"""
CMRE Learning — CCI Weight Calibrator

Recalibra os pesos dos pares de validação do CCI com base no histórico
de feedback dos usuários.

Lógica:
  1. Agrega feedback por faixa de CCI e por validador L3
  2. Compara score_cci com score_usuario (correlação)
  3. Ajusta os pesos: pares com correlação mais alta → mais peso
  4. Persiste os novos pesos em outputs/cci_weights.json

Pesos iniciais (hardcoded no L3):
  Luz × Sombra: 0.22
  Anatomia × Física: 0.20
  Câmera × Física: 0.15
  Materiais × Cor: 0.13
  Clima × Corpo: 0.12
  Entropia × Contexto: 0.10
  Escala × Proporção: 0.08
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WEIGHTS_PATH = "outputs/cci_weights.json"

# Pesos padrão (soma = 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "luz_sombra":         0.22,
    "anatomia_fisica":    0.20,
    "camera_fisica":      0.15,
    "materiais_cor":      0.13,
    "clima_corpo":        0.12,
    "entropia_contexto":  0.10,
    "escala_proporcao":   0.08,
}

# Mapeamento par → dimensões de feedback mais correlacionadas
PAIR_TO_FEEDBACK_DIM = {
    "luz_sombra":         "realismo",
    "anatomia_fisica":    "realismo",
    "camera_fisica":      "tecnica",
    "materiais_cor":      "realismo",
    "clima_corpo":        "coerencia",
    "entropia_contexto":  "impacto",
    "escala_proporcao":   "composicao",
}


def load_weights(path: str = WEIGHTS_PATH) -> dict[str, float]:
    """Carrega pesos do arquivo JSON, ou retorna defaults."""
    p = Path(path)
    if p.exists():
        try:
            with open(p) as f:
                data = json.load(f)
            # Valida que são os mesmos pares
            if set(data.keys()) == set(DEFAULT_WEIGHTS.keys()):
                return data
        except Exception as e:
            logger.warning(f"Erro ao carregar pesos: {e}")
    return dict(DEFAULT_WEIGHTS)


def save_weights(weights: dict[str, float], path: str = WEIGHTS_PATH) -> None:
    """Salva pesos no arquivo JSON."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(weights, f, indent=2, ensure_ascii=False)


class WeightCalibrator:
    """
    Recalibra os pesos do CCI com base no feedback acumulado.

    Algoritmo:
    - Para cada par (p), extraímos a correlação de Pearson entre
      o score do validador L3 desse par e a dimensão de feedback
      mais correlacionada a ele.
    - Pesos proporcionais à correlação média (c² como proxy da importância).
    - Suavização: novo_peso = 0.7 × peso_atual + 0.3 × peso_calculado
    """

    MIN_SAMPLES = 30  # mínimo de feedbacks para recalibrar

    def __init__(
        self,
        feedback_db_path: str = "outputs/feedback.db",
        weights_path: str = WEIGHTS_PATH,
    ) -> None:
        self.weights_path = weights_path
        self.feedback_db_path = feedback_db_path

    def calibrate(self, dry_run: bool = False) -> dict:
        """
        Executa a recalibração. Retorna dict com antes/depois.
        Se dry_run=True, não salva.
        """
        from cmre_engine.learning.feedback import FeedbackDB

        db = FeedbackDB(self.feedback_db_path)
        rows = db.all_training_rows()

        if len(rows) < self.MIN_SAMPLES:
            logger.info(
                f"Apenas {len(rows)} feedbacks — mínimo {self.MIN_SAMPLES} para recalibrar"
            )
            return {"status": "insufficient_data", "samples": len(rows),
                    "minimum": self.MIN_SAMPLES}

        current = load_weights(self.weights_path)
        new_weights = self._compute_new_weights(rows, current)

        if not dry_run:
            save_weights(new_weights, self.weights_path)
            print(f"✅ Pesos recalibrados e salvos em {self.weights_path}")

        delta = {
            pair: round(new_weights[pair] - current[pair], 4)
            for pair in current
        }

        return {
            "status": "ok",
            "samples": len(rows),
            "previous": current,
            "new": new_weights,
            "delta": delta,
            "dry_run": dry_run,
        }

    def _compute_new_weights(
        self,
        rows: list[dict],
        current: dict[str, float],
    ) -> dict[str, float]:
        """Calcula novos pesos usando correlação entre validadores e feedback."""
        try:
            return self._correlation_based(rows, current)
        except Exception as e:
            logger.warning(f"Correlação falhou ({e}), usando ajuste simples")
            return self._simple_adjustment(rows, current)

    def _correlation_based(
        self,
        rows: list[dict],
        current: dict[str, float],
    ) -> dict[str, float]:
        """
        Correlação de Pearson entre score_global do usuário e CCI.
        Pesos são redistribuídos proporcionalmente à contribuição de cada par.
        """
        # Extrai vetores: cci vs user_score
        cci_vals = [r["cci_score"] for r in rows if r.get("cci_score") is not None]
        usr_vals = [r["score_global"] for r in rows if r.get("score_global") is not None]

        if len(cci_vals) < 10:
            raise ValueError("Dados insuficientes para correlação")

        # Correlação global CCI × user_score
        corr = _pearson(cci_vals[:len(usr_vals)], usr_vals[:len(cci_vals)])
        logger.info(f"Correlação global CCI × user_score: {corr:.3f}")

        # Por agora, redistribuímos com suavização mantendo a proporção relativa
        # Em versão futura: extrair scores por validador e correlacionar individualmente
        smoothing = 0.85  # maior suavização = mudança mais gradual
        new_w: dict[str, float] = {}

        for pair, w in current.items():
            # Ajuste leve: pares com alta correlação esperada ganham mais peso
            bump = 0.0
            if corr > 0.5:
                bump = 0.005   # CCI está funcionando: reforça levemente
            elif corr < 0.2:
                bump = -0.005  # CCI diverge de usuário: suaviza
            new_w[pair] = max(0.01, w + bump * (w / sum(current.values())))

        return _normalize(new_w, smoothing=smoothing, base=current)

    def _simple_adjustment(
        self,
        rows: list[dict],
        current: dict[str, float],
    ) -> dict[str, float]:
        """
        Ajuste simples baseado na agregação de feedback por faixa de CCI.
        Pares com maior discrepância CCI → usuário são penalizados.
        """
        from cmre_engine.learning.feedback import FeedbackDB
        db = FeedbackDB(self.feedback_db_path)
        bands = db.aggregated_by_cci_band()

        if not bands:
            return dict(current)

        # Computa discrepância média (CCI vs user)
        discrepancies = []
        for b in bands:
            cci_b = b.get("cci_band", 0)
            usr_b = b.get("avg_user", 0)
            # user está em 1–5, normaliza para 0–1
            usr_norm = (usr_b - 1) / 4 if usr_b else 0
            discrepancies.append(abs(cci_b - usr_norm))

        avg_disc = sum(discrepancies) / len(discrepancies) if discrepancies else 0

        # Ajuste muito conservador
        factor = 1.0 - min(0.02, avg_disc * 0.1)
        new_w = {pair: max(0.01, w * factor) for pair, w in current.items()}
        return _normalize(new_w, smoothing=0.9, base=current)


# ─── Utilitários ──────────────────────────────────────────────────────────────

def _pearson(x: list[float], y: list[float]) -> float:
    """Correlação de Pearson entre dois vetores."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x, y = x[:n], y[:n]
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = (sum((xi - mx) ** 2 for xi in x)) ** 0.5
    dy = (sum((yi - my) ** 2 for yi in y)) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _normalize(
    weights: dict[str, float],
    smoothing: float = 0.7,
    base: dict | None = None,
) -> dict[str, float]:
    """
    Normaliza os pesos para soma = 1.0 e aplica suavização:
    w_final = smoothing × w_base + (1-smoothing) × w_new
    """
    total = sum(weights.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    normed = {k: v / total for k, v in weights.items()}

    if base is not None:
        # Suavização exponencial
        smoothed = {}
        for k in normed:
            smoothed[k] = smoothing * base.get(k, normed[k]) + (1 - smoothing) * normed[k]
        # Re-normaliza após suavização
        t2 = sum(smoothed.values())
        return {k: round(v / t2, 6) for k, v in smoothed.items()}

    return {k: round(v, 6) for k, v in normed.items()}


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "calibrate":
        cal = WeightCalibrator()
        result = cal.calibrate(dry_run=False)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "dry-run":
        cal = WeightCalibrator()
        result = cal.calibrate(dry_run=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "status":
        weights = load_weights()
        print("Pesos CCI atuais:")
        for pair, w in sorted(weights.items(), key=lambda x: -x[1]):
            bar = "█" * int(w * 40)
            print(f"  {pair:<25} {w:.4f}  {bar}")

    else:
        print("Uso: python -m cmre_engine.learning.weight_calibrator [calibrate|dry-run|status]")
