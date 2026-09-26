"""
CMRE Learning — User Feedback & Rating System

Os usuários avaliam a imagem gerada em 5 dimensões (1–5).
Os ratings alimentam o treinamento da rede neural e recalibram
os pesos do CCI.

Dimensões de avaliação:
  • realismo      — quão fotorrealista parece
  • tecnica       — qualidade técnica (foco, exposição, cor)
  • composicao    — composição e enquadramento
  • coerencia     — coerência entre briefing e imagem
  • impacto       — impacto visual geral / "wow factor"
"""
from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

FEEDBACK_DB_PATH = "outputs/feedback.db"

DIMENSIONS = ["realismo", "tecnica", "composicao", "coerencia", "impacto"]


class FeedbackDB:
    """SQLite para armazenar avaliações dos usuários."""

    def __init__(self, db_path: str = FEEDBACK_DB_PATH) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS image_feedback (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id      TEXT,
                    briefing        TEXT,
                    prompt_used     TEXT,
                    backend         TEXT,
                    cci_score       REAL,
                    image_path      TEXT,

                    -- Avaliações (1–5)
                    score_realismo      INTEGER,
                    score_tecnica       INTEGER,
                    score_composicao    INTEGER,
                    score_coerencia     INTEGER,
                    score_impacto       INTEGER,
                    score_global        REAL,   -- média ponderada

                    -- Extras opcionais
                    comment         TEXT,
                    blocks_json     TEXT,   -- vetor de blocos técnicos (para treinar NN)
                    validators_json TEXT,   -- scores L3

                    created_at      TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_fb_session
                ON image_feedback(session_id)
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_fb_cci
                ON image_feedback(cci_score)
            """)

    def save(self, entry: "FeedbackEntry") -> int:
        """Salva um registro de feedback. Retorna o ID inserido."""
        with self._conn() as c:
            c.execute("""
                INSERT INTO image_feedback (
                    session_id, briefing, prompt_used, backend, cci_score,
                    image_path, score_realismo, score_tecnica, score_composicao,
                    score_coerencia, score_impacto, score_global,
                    comment, blocks_json, validators_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.session_id, entry.briefing, entry.prompt_used,
                entry.backend, entry.cci_score, entry.image_path,
                entry.scores.get("realismo"),
                entry.scores.get("tecnica"),
                entry.scores.get("composicao"),
                entry.scores.get("coerencia"),
                entry.scores.get("impacto"),
                entry.global_score,
                entry.comment,
                json.dumps(entry.blocks, ensure_ascii=False) if entry.blocks else None,
                json.dumps(entry.validators, ensure_ascii=False) if entry.validators else None,
                entry.created_at or datetime.utcnow().isoformat(),
            ))
            return c.lastrowid  # type: ignore[return-value]

    def all_training_rows(self) -> list[dict]:
        """Retorna todos os registros com scores válidos para treinamento da NN."""
        with self._conn() as c:
            rows = c.execute("""
                SELECT
                    cci_score, score_global,
                    blocks_json, validators_json
                FROM image_feedback
                WHERE score_global IS NOT NULL
                  AND blocks_json IS NOT NULL
                ORDER BY id
            """).fetchall()
        result = []
        for cci, sg, blk, val in rows:
            try:
                result.append({
                    "cci_score": cci,
                    "score_global": sg,
                    "blocks": json.loads(blk),
                    "validators": json.loads(val) if val else {},
                })
            except Exception:
                pass
        return result

    def aggregated_by_cci_band(self) -> list[dict]:
        """Agrega feedback por faixa de CCI — usado pelo weight calibrator."""
        with self._conn() as c:
            rows = c.execute("""
                SELECT
                    ROUND(cci_score * 10) / 10 AS cci_band,
                    COUNT(*) AS cnt,
                    AVG(score_global)  AS avg_user,
                    AVG(score_realismo)    AS avg_realismo,
                    AVG(score_tecnica)     AS avg_tecnica,
                    AVG(score_composicao)  AS avg_composicao,
                    AVG(score_coerencia)   AS avg_coerencia,
                    AVG(score_impacto)     AS avg_impacto
                FROM image_feedback
                WHERE score_global IS NOT NULL
                GROUP BY cci_band
                ORDER BY cci_band
            """).fetchall()
        cols = ["cci_band", "cnt", "avg_user",
                "avg_realismo", "avg_tecnica", "avg_composicao",
                "avg_coerencia", "avg_impacto"]
        return [dict(zip(cols, r)) for r in rows]

    def stats(self) -> dict:
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM image_feedback").fetchone()[0]
            avg_global = c.execute(
                "SELECT AVG(score_global) FROM image_feedback WHERE score_global IS NOT NULL"
            ).fetchone()[0]
            avg_cci = c.execute(
                "SELECT AVG(cci_score) FROM image_feedback WHERE cci_score IS NOT NULL"
            ).fetchone()[0]
        return {
            "total_feedbacks": total,
            "avg_user_score": round(avg_global or 0, 2),
            "avg_cci": round(avg_cci or 0, 3),
        }


# ─── Dataclass de entrada ─────────────────────────────────────────────────────

class FeedbackEntry:
    """Representa uma avaliação do usuário sobre uma imagem gerada."""

    def __init__(
        self,
        *,
        session_id: str | None = None,
        briefing: str = "",
        prompt_used: str = "",
        backend: str = "",
        cci_score: float | None = None,
        image_path: str | None = None,
        scores: dict | None = None,
        comment: str | None = None,
        blocks: dict | None = None,
        validators: dict | None = None,
    ) -> None:
        self.session_id = session_id
        self.briefing = briefing
        self.prompt_used = prompt_used
        self.backend = backend
        self.cci_score = cci_score
        self.image_path = image_path
        self.scores: dict[str, int] = scores or {}
        self.comment = comment
        self.blocks = blocks
        self.validators = validators
        self.created_at = datetime.utcnow().isoformat()

    @property
    def global_score(self) -> float | None:
        """Média ponderada das dimensões (1–5 → 0–1)."""
        weights = {
            "realismo":   0.30,
            "tecnica":    0.25,
            "composicao": 0.20,
            "coerencia":  0.15,
            "impacto":    0.10,
        }
        total, wsum = 0.0, 0.0
        for dim, w in weights.items():
            v = self.scores.get(dim)
            if v is not None:
                total += v * w
                wsum += w
        if wsum == 0:
            return None
        # Converte escala 1–5 para 0.0–1.0
        return round((total / wsum - 1) / 4, 4)

    def validate(self) -> list[str]:
        """Valida o entry. Retorna lista de erros (vazia se OK)."""
        errors = []
        for dim in DIMENSIONS:
            v = self.scores.get(dim)
            if v is not None and not (1 <= v <= 5):
                errors.append(f"Score '{dim}' deve ser 1–5 (recebido: {v})")
        return errors


# ─── Coletor interativo (CLI) ─────────────────────────────────────────────────

class FeedbackCollector:
    """Coleta feedback interativamente no terminal."""

    def __init__(self, db_path: str = FEEDBACK_DB_PATH) -> None:
        self.db = FeedbackDB(db_path)

    def collect(
        self,
        briefing: str = "",
        prompt_used: str = "",
        backend: str = "",
        cci_score: float | None = None,
        image_path: str | None = None,
        blocks: dict | None = None,
        validators: dict | None = None,
        session_id: str | None = None,
    ) -> FeedbackEntry | None:
        """
        Coleta avaliação interativamente e salva no banco.
        Retorna None se o usuário cancelar.
        """
        print("\n" + "═" * 55)
        print("  📊 AVALIAÇÃO DA IMAGEM GERADA")
        print("═" * 55)
        if image_path:
            print(f"  Imagem: {image_path}")
        if cci_score is not None:
            print(f"  CCI Score: {cci_score:.3f}")
        print()
        print("  Avalie cada dimensão de 1 a 5:")
        print("  1=Ruim  2=Regular  3=Bom  4=Muito bom  5=Excelente")
        print()

        dim_labels = {
            "realismo":   "Realismo       (parece uma foto real?)",
            "tecnica":    "Técnica        (foco, luz, exposição, cor)",
            "composicao": "Composição     (enquadramento e layout)",
            "coerencia":  "Coerência      (corresponde ao briefing?)",
            "impacto":    "Impacto visual ('wow factor')",
        }

        scores: dict[str, int] = {}
        for dim in DIMENSIONS:
            while True:
                raw = input(f"  {dim_labels[dim]}: ").strip()
                if raw == "" or raw.lower() in ("q", "s", "skip"):
                    print("  [avaliação cancelada]")
                    return None
                try:
                    v = int(raw)
                    if 1 <= v <= 5:
                        scores[dim] = v
                        break
                    print("  ⚠  Digite um número entre 1 e 5")
                except ValueError:
                    print("  ⚠  Número inválido")

        comment = input("\n  Comentário (opcional, Enter para pular): ").strip() or None

        entry = FeedbackEntry(
            session_id=session_id,
            briefing=briefing,
            prompt_used=prompt_used,
            backend=backend,
            cci_score=cci_score,
            image_path=image_path,
            scores=scores,
            comment=comment,
            blocks=blocks,
            validators=validators,
        )
        fid = self.db.save(entry)
        score_disp = f"{entry.global_score:.2f}" if entry.global_score else "N/A"
        print(f"\n  ✅ Feedback #{fid} salvo — Score global: {score_disp}")
        return entry


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"

    if cmd == "stats":
        db = FeedbackDB()
        s = db.stats()
        print(json.dumps(s, indent=2, ensure_ascii=False))

    elif cmd == "collect":
        collector = FeedbackCollector()
        collector.collect(briefing="Teste manual", backend="manual")

    elif cmd == "training-data":
        db = FeedbackDB()
        rows = db.all_training_rows()
        print(f"Registros para treinamento: {len(rows)}")
        if rows:
            print(json.dumps(rows[:3], indent=2, ensure_ascii=False))
    else:
        print("Uso: python -m cmre_engine.learning.feedback [stats|collect|training-data]")
