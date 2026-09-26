"""
CMRE Engine — Banco de referências SQLite.
Armazena análises de fotos reais (Lado A) para consulta antes da geração (Lado B).

Schema:
  reference_photos
    id              INTEGER PRIMARY KEY AUTOINCREMENT
    image_path      TEXT NOT NULL
    image_hash      TEXT NOT NULL UNIQUE   -- SHA256 do arquivo
    scene_genre     TEXT NOT NULL          -- retrato, paisagem, produto, etc.
    blocks_json     TEXT NOT NULL          -- JSON com os 16 blocos técnicos
    cci_score       REAL NOT NULL          -- 0.0–1.0
    validator_json  TEXT NOT NULL          -- JSON {"Luz × Sombra": 0.9, ...}
    created_at      TEXT NOT NULL          -- ISO 8601 UTC
    metadata_json   TEXT DEFAULT '{}'      -- dados extras (EXIF, notas)
"""
import sqlite3
import json
import hashlib
import dataclasses
import os
from pathlib import Path
from typing import Optional

from ..models import TechnicalBlocks, ReferenceEntry


class ReferenceDatabase:
    """
    Gerencia o banco SQLite de fotos reais analisadas.

    Uso típico:
        db = ReferenceDatabase("outputs/reference.db")
        db.save(entry)
        similares = db.find_similar("retrato", limit=3)
        melhor = db.best_for_genre("retrato")
    """

    def __init__(self, db_path: str = "outputs/reference.db"):
        self.db_path = db_path
        # Garante que o diretório existe
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ─── Schema ───────────────────────────────────────────────────────────────

    def _init_schema(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reference_photos (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path     TEXT    NOT NULL,
                    image_hash     TEXT    NOT NULL UNIQUE,
                    scene_genre    TEXT    NOT NULL,
                    blocks_json    TEXT    NOT NULL,
                    cci_score      REAL    NOT NULL,
                    validator_json TEXT    NOT NULL,
                    created_at     TEXT    NOT NULL,
                    metadata_json  TEXT    DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_genre
                ON reference_photos (scene_genre)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cci
                ON reference_photos (cci_score DESC)
            """)
            conn.commit()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    def save(self, entry: ReferenceEntry) -> int:
        """
        Insere ou atualiza uma referência no banco.
        Retorna o id do registro inserido/atualizado.
        """
        blocks_json = json.dumps(dataclasses.asdict(entry.blocks))
        validator_json = json.dumps(entry.validator_scores)
        metadata_json = json.dumps(entry.metadata)

        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO reference_photos
                    (image_path, image_hash, scene_genre, blocks_json,
                     cci_score, validator_json, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(image_hash) DO UPDATE SET
                    scene_genre    = excluded.scene_genre,
                    blocks_json    = excluded.blocks_json,
                    cci_score      = excluded.cci_score,
                    validator_json = excluded.validator_json,
                    metadata_json  = excluded.metadata_json
            """, (
                entry.image_path,
                entry.image_hash,
                entry.scene_genre,
                blocks_json,
                entry.cci_score,
                validator_json,
                entry.created_at,
                metadata_json,
            ))
            conn.commit()
            return cursor.lastrowid or self._id_by_hash(conn, entry.image_hash)

    def _id_by_hash(self, conn, image_hash: str) -> int:
        row = conn.execute(
            "SELECT id FROM reference_photos WHERE image_hash = ?", (image_hash,)
        ).fetchone()
        return row["id"] if row else -1

    def get_by_hash(self, image_hash: str) -> Optional[ReferenceEntry]:
        """Recupera uma entrada pelo SHA256 da imagem."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM reference_photos WHERE image_hash = ?", (image_hash,)
            ).fetchone()
        return self._row_to_entry(row) if row else None

    def delete(self, image_hash: str) -> bool:
        """Remove uma entrada pelo hash. Retorna True se deletado."""
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM reference_photos WHERE image_hash = ?", (image_hash,)
            )
            conn.commit()
        return cur.rowcount > 0

    # ─── Consultas ────────────────────────────────────────────────────────────

    def find_similar(
        self,
        scene_genre: str,
        min_cci: float = 0.0,
        limit: int = 5,
    ) -> list[ReferenceEntry]:
        """
        Retorna as N referências mais coerentes do mesmo gênero de cena.
        Ordenadas por CCI decrescente (melhor primeiro).
        """
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM reference_photos
                WHERE scene_genre = ?
                  AND cci_score   >= ?
                ORDER BY cci_score DESC
                LIMIT ?
            """, (scene_genre, min_cci, limit)).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def best_for_genre(self, scene_genre: str) -> Optional[ReferenceEntry]:
        """Retorna a referência de maior CCI para o gênero de cena."""
        results = self.find_similar(scene_genre, limit=1)
        return results[0] if results else None

    def all_genres(self) -> list[str]:
        """Lista todos os gêneros de cena únicos no banco."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT scene_genre FROM reference_photos ORDER BY scene_genre"
            ).fetchall()
        return [r["scene_genre"] for r in rows]

    def stats(self) -> dict:
        """Estatísticas gerais do banco de referências."""
        with self._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as n FROM reference_photos"
            ).fetchone()["n"]
            avg_cci = conn.execute(
                "SELECT AVG(cci_score) as a FROM reference_photos"
            ).fetchone()["a"] or 0.0
            by_genre = conn.execute("""
                SELECT scene_genre, COUNT(*) as n, AVG(cci_score) as avg_cci
                FROM reference_photos
                GROUP BY scene_genre
                ORDER BY n DESC
            """).fetchall()
        return {
            "total": total,
            "avg_cci": round(avg_cci, 3),
            "by_genre": [
                {
                    "genre": r["scene_genre"],
                    "count": r["n"],
                    "avg_cci": round(r["avg_cci"], 3),
                }
                for r in by_genre
            ],
        }

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def hash_image(image_path: str) -> str:
        """Calcula SHA256 do arquivo de imagem."""
        sha = hashlib.sha256()
        with open(image_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def _row_to_entry(self, row: sqlite3.Row) -> ReferenceEntry:
        blocks_dict = json.loads(row["blocks_json"])
        blocks = TechnicalBlocks(**blocks_dict)
        return ReferenceEntry(
            id=row["id"],
            image_path=row["image_path"],
            image_hash=row["image_hash"],
            scene_genre=row["scene_genre"],
            blocks=blocks,
            cci_score=row["cci_score"],
            validator_scores=json.loads(row["validator_json"]),
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"]),
        )
