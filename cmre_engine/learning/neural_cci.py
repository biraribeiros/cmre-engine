"""
CMRE Learning — Neural CCI Predictor (MLP)

Rede neural leve (~500 parâmetros) que aprende a prever:
  - CCI score esperado dado o vetor de blocos técnicos
  - Score do usuário esperado (realismo, técnica, etc.)

Treina em VETORES DE RELAÇÃO (features extraídas) — nunca em fotos.
Não há dados visuais aqui: apenas valores numéricos derivados dos 30 agentes.

Arquitetura:
  Entrada: 23 features (16 blocos técnicos + 7 scores L3)
  Camada 1: 32 neurônios ReLU
  Camada 2: 16 neurônios ReLU
  Saída: 2 neurônios (cci_pred, user_score_pred)

Requer: scikit-learn (preferencial) ou numpy puro como fallback.
"""
from __future__ import annotations

import json
import os
import logging
import pickle
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

MODEL_PATH   = "outputs/neural_cci.pkl"
SCALER_PATH  = "outputs/neural_cci_scaler.pkl"
HISTORY_PATH = "outputs/neural_cci_history.json"

# Dimensão de entrada: 16 blocos + 7 L3 scores
INPUT_DIM = 23


# ─── Extrator de features ─────────────────────────────────────────────────────

BLOCK_KEYS = [
    "saida", "enquadramento", "sensor_meio", "optica", "exposicao",
    "luz", "cor", "sujeito", "materiais", "ambiente", "profundidade",
    "textura_captura", "imperfeicoes", "entropia", "movimento_fisica",
    "exclusoes",
]

L3_KEYS = [
    "luz_sombra", "anatomia_fisica", "camera_fisica", "materiais_cor",
    "clima_corpo", "entropia_contexto", "escala_proporcao",
]


def _blocks_to_vector(blocks: dict, validators: dict) -> list[float]:
    """
    Converte os dicionários de blocos e validadores num vetor numérico.
    Cada bloco é representado por sua riqueza semântica (len/100).
    """
    vec: list[float] = []

    # 16 features dos blocos (comprimento do texto normalizado → 0-1)
    for key in BLOCK_KEYS:
        val = blocks.get(key, "")
        if isinstance(val, str):
            feat = min(len(val) / 200.0, 1.0)
        elif isinstance(val, (int, float)):
            feat = float(val)
        else:
            feat = 0.0
        vec.append(feat)

    # 7 features dos validadores L3 (score 0.0–1.0)
    for key in L3_KEYS:
        val = validators.get(key, 0)
        if isinstance(val, dict):
            val = val.get("score", 0)
        vec.append(float(val))

    return vec


def _row_to_xy(row: dict) -> tuple[list[float], list[float]] | None:
    """
    Converte um registro de training_rows em (X, Y).
    X: vetor de 23 features
    Y: [cci_score, user_score]  ambos em 0–1
    """
    blocks = row.get("blocks", {})
    validators = row.get("validators", {})
    cci = row.get("cci_score")
    usr = row.get("score_global")

    if cci is None or usr is None:
        return None

    x = _blocks_to_vector(blocks, validators)
    if len(x) != INPUT_DIM:
        logger.debug(f"Vector dim mismatch: {len(x)} != {INPUT_DIM}")
        return None

    y = [float(cci), float(usr)]
    return x, y


# ─── Modelo ──────────────────────────────────────────────────────────────────

class NeuralCCIPredictor:
    """
    Wrapper em torno de sklearn.MLPRegressor (ou fallback linear puro).

    Uso:
        predictor = NeuralCCIPredictor()
        predictor.train(rows)
        cci_pred, user_pred = predictor.predict(blocks, validators)
        predictor.save()
    """

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        scaler_path: str = SCALER_PATH,
    ) -> None:
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model: Any = None
        self.scaler: Any = None
        self.is_fitted = False
        self.history: list[dict] = []
        self._load_history()

    # ── Treinamento ──────────────────────────────────────────────────────────

    def train(self, rows: list[dict]) -> dict:
        """
        Treina o modelo nos registros de feedback.
        Retorna métricas de treinamento.
        """
        # Prepara dataset
        X, Y = [], []
        for row in rows:
            result = _row_to_xy(row)
            if result is not None:
                x, y = result
                X.append(x)
                Y.append(y)

        if len(X) < 5:
            return {"status": "insufficient_data", "samples": len(X)}

        metrics = {}

        try:
            from sklearn.neural_network import MLPRegressor
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import train_test_split
            import numpy as np

            Xa = np.array(X, dtype=float)
            Ya = np.array(Y, dtype=float)

            # Normalização
            scaler = StandardScaler()
            Xs = scaler.fit_transform(Xa)
            self.scaler = scaler

            # Divisão treino/validação
            if len(X) >= 10:
                X_tr, X_val, Y_tr, Y_val = train_test_split(
                    Xs, Ya, test_size=0.2, random_state=42
                )
            else:
                X_tr, Y_tr = Xs, Ya
                X_val, Y_val = Xs, Ya

            # Modelo MLP ~500 parâmetros
            # (23 × 32) + 32 + (32 × 16) + 16 + (16 × 2) + 2 ≈ 1_218 params
            # Reduzindo para hidden=(24, 12) → ~23*24 + 24 + 24*12 + 12 + 12*2 + 2 = 896
            mlp = MLPRegressor(
                hidden_layer_sizes=(24, 12),
                activation="relu",
                solver="adam",
                alpha=1e-3,
                learning_rate_init=1e-3,
                max_iter=500,
                early_stopping=True,
                validation_fraction=0.2 if len(X_tr) >= 10 else 0.0,
                n_iter_no_change=20,
                random_state=42,
                verbose=False,
            )
            mlp.fit(X_tr, Y_tr)
            self.model = mlp
            self.is_fitted = True

            # Métricas
            Y_pred = mlp.predict(X_val)
            mse_cci  = float(np.mean((Y_pred[:, 0] - Y_val[:, 0]) ** 2))
            mse_user = float(np.mean((Y_pred[:, 1] - Y_val[:, 1]) ** 2))
            metrics = {
                "status": "ok",
                "samples": len(X),
                "train_samples": len(X_tr),
                "val_samples": len(X_val),
                "mse_cci": round(mse_cci, 6),
                "mse_user": round(mse_user, 6),
                "rmse_cci": round(mse_cci ** 0.5, 4),
                "rmse_user": round(mse_user ** 0.5, 4),
                "iterations": mlp.n_iter_,
                "backend": "sklearn",
            }

        except ImportError:
            # Fallback: regressão linear simples via numpy
            metrics = self._train_linear_fallback(X, Y)

        self._record_history(metrics)
        return metrics

    def _train_linear_fallback(self, X: list, Y: list) -> dict:
        """Fallback quando sklearn não está disponível."""
        try:
            import numpy as np
            Xa = np.array(X, dtype=float)
            Ya = np.array(Y, dtype=float)

            # Regressão linear (pseudo-inversa)
            # Adiciona coluna de bias
            Xb = np.hstack([Xa, np.ones((len(Xa), 1))])
            W, _, _, _ = np.linalg.lstsq(Xb, Ya, rcond=None)
            self.model = {"W": W.tolist(), "type": "linear"}
            self.is_fitted = True

            Y_pred = Xb @ W
            mse = float(np.mean((Y_pred - Ya) ** 2))
            return {
                "status": "ok_linear",
                "samples": len(X),
                "mse": round(mse, 6),
                "backend": "numpy_linear",
            }
        except ImportError:
            # Sem numpy: guarda média
            cci_mean = sum(y[0] for y in Y) / len(Y)
            usr_mean = sum(y[1] for y in Y) / len(Y)
            self.model = {"type": "mean", "cci": cci_mean, "user": usr_mean}
            self.is_fitted = True
            return {"status": "ok_mean", "samples": len(X), "backend": "mean"}

    # ── Predição ─────────────────────────────────────────────────────────────

    def predict(
        self,
        blocks: dict,
        validators: dict,
    ) -> tuple[float, float]:
        """
        Prediz (cci_score, user_score) para um conjunto de blocos e validadores.
        Retorna (0.5, 0.5) como fallback se modelo não estiver treinado.
        """
        if not self.is_fitted or self.model is None:
            return 0.5, 0.5

        x = _blocks_to_vector(blocks, validators)

        try:
            # sklearn MLP
            if hasattr(self.model, "predict"):
                import numpy as np
                Xa = np.array([x], dtype=float)
                if self.scaler is not None:
                    Xa = self.scaler.transform(Xa)
                pred = self.model.predict(Xa)[0]
                cci  = float(max(0.0, min(1.0, pred[0])))
                user = float(max(0.0, min(1.0, pred[1])))
                return cci, user

            # Fallback linear
            if isinstance(self.model, dict) and self.model.get("type") == "linear":
                import numpy as np
                W = np.array(self.model["W"])
                xb = np.array(x + [1.0])
                pred = xb @ W
                return (
                    float(max(0.0, min(1.0, pred[0]))),
                    float(max(0.0, min(1.0, pred[1]))),
                )

            # Mean fallback
            if isinstance(self.model, dict) and self.model.get("type") == "mean":
                return self.model["cci"], self.model["user"]

        except Exception as e:
            logger.warning(f"Predição falhou: {e}")

        return 0.5, 0.5

    # ── Persistência ─────────────────────────────────────────────────────────

    def save(self) -> None:
        """Salva modelo e scaler em disco."""
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump(self.model, f)
        if self.scaler is not None:
            with open(self.scaler_path, "wb") as f:
                pickle.dump(self.scaler, f)
        self._save_history()

    def load(self) -> bool:
        """Carrega modelo salvo. Retorna True se bem-sucedido."""
        try:
            if Path(self.model_path).exists():
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                if Path(self.scaler_path).exists():
                    with open(self.scaler_path, "rb") as f:
                        self.scaler = pickle.load(f)
                self.is_fitted = True
                return True
        except Exception as e:
            logger.warning(f"Erro ao carregar modelo: {e}")
        return False

    def _load_history(self) -> None:
        if Path(HISTORY_PATH).exists():
            try:
                with open(HISTORY_PATH) as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def _save_history(self) -> None:
        Path(HISTORY_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, "w") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def _record_history(self, metrics: dict) -> None:
        from datetime import datetime
        entry = {"timestamp": datetime.utcnow().isoformat(), **metrics}
        self.history.append(entry)
        self._save_history()

    def status(self) -> dict:
        last = self.history[-1] if self.history else None
        return {
            "is_fitted": self.is_fitted,
            "model_exists": Path(self.model_path).exists(),
            "training_runs": len(self.history),
            "last_training": last,
        }


# ─── Pipeline de treinamento integrado ───────────────────────────────────────

class NeuralTrainer:
    """
    Orquestra o ciclo completo de treinamento neural:
    FeedbackDB → NeuralCCIPredictor → WeightCalibrator
    """

    def __init__(self) -> None:
        self.predictor = NeuralCCIPredictor()
        self.predictor.load()  # carrega modelo existente se disponível

    def run(self, also_calibrate_weights: bool = True) -> dict:
        """Treina a rede neural + recalibra pesos CCI."""
        from cmre_engine.learning.feedback import FeedbackDB
        from cmre_engine.learning.weight_calibrator import WeightCalibrator

        print("\n🧠 CMRE Neural Training")
        print("═" * 50)

        # 1. Coleta dados de treinamento
        db = FeedbackDB()
        rows = db.all_training_rows()
        print(f"  📊 Registros de feedback disponíveis: {len(rows)}")

        if not rows:
            print("  ⚠️  Nenhum dado de treinamento ainda")
            print("     Use o comando 'feedback' para coletar avaliações")
            return {"status": "no_data"}

        # 2. Treina rede neural
        print(f"\n  🔧 Treinando rede neural ({INPUT_DIM}→24→12→2)...")
        metrics = self.predictor.train(rows)
        self.predictor.save()

        if metrics["status"].startswith("ok"):
            backend = metrics.get("backend", "?")
            if "rmse_cci" in metrics:
                print(f"  ✅ Treino concluído [{backend}]")
                print(f"     RMSE CCI:  {metrics['rmse_cci']:.4f}")
                print(f"     RMSE User: {metrics['rmse_user']:.4f}")
            else:
                print(f"  ✅ Treino concluído [{backend}]")
        else:
            print(f"  ⚠️  {metrics}")

        # 3. Recalibra pesos CCI
        cal_result = {"status": "skipped"}
        if also_calibrate_weights:
            print("\n  ⚖️  Recalibrando pesos CCI...")
            cal = WeightCalibrator()
            cal_result = cal.calibrate(dry_run=False)
            if cal_result["status"] == "ok":
                deltas = cal_result.get("delta", {})
                changed = {k: v for k, v in deltas.items() if abs(v) > 1e-5}
                if changed:
                    print("  Pesos ajustados:")
                    for pair, delta in sorted(changed.items(), key=lambda x: -abs(x[1])):
                        sign = "▲" if delta > 0 else "▼"
                        print(f"     {pair:<25} {sign} {abs(delta):.4f}")
                else:
                    print("  ✅ Pesos estáveis (nenhuma mudança significativa)")
            else:
                print(f"  ℹ️  {cal_result.get('status')}: {cal_result.get('samples',0)} amostras")

        return {
            "neural": metrics,
            "calibration": cal_result,
        }


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "train":
        trainer = NeuralTrainer()
        result = trainer.run()
        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

    elif cmd == "status":
        p = NeuralCCIPredictor()
        p.load()
        s = p.status()
        print(json.dumps(s, indent=2, ensure_ascii=False))

    elif cmd == "predict":
        # Teste com blocos simulados
        p = NeuralCCIPredictor()
        if p.load():
            test_blocks = {k: "sample text content" for k in BLOCK_KEYS}
            test_validators = {k: 0.8 for k in L3_KEYS}
            cci_p, usr_p = p.predict(test_blocks, test_validators)
            print(f"Predição — CCI: {cci_p:.3f} | User: {usr_p:.3f}")
        else:
            print("Modelo não treinado. Execute 'train' primeiro.")
    else:
        print("Uso: python -m cmre_engine.learning.neural_cci [train|status|predict]")
