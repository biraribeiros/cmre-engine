"""
CMRE Learning — Daily Harvest Pipeline

Busca 4 fotos por gênero de cena diariamente usando APIs gratuitas
(Pexels / Unsplash) e alimenta automaticamente o banco de referências.

Uso:
    python -m cmre_engine.learning.daily_harvest run
    python -m cmre_engine.learning.daily_harvest status
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import logging
import sqlite3
import urllib.request
import urllib.parse
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Gêneros de cena monitorados ─────────────────────────────────────────────

SCENE_GENRES = [
    "retrato", "produto", "paisagem", "urbano", "moda",
    "esporte", "alimento", "animal", "arquitetura", "geral",
]

GENRE_QUERIES = {
    "retrato":      "portrait photography natural light",
    "produto":      "product photography studio",
    "paisagem":     "landscape photography nature",
    "urbano":       "urban street photography city",
    "moda":         "fashion editorial photography",
    "esporte":      "sports action photography",
    "alimento":     "food photography restaurant",
    "animal":       "wildlife animal photography",
    "arquitetura":  "architecture building photography",
    "geral":        "professional photography realistic",
}

PHOTOS_PER_GENRE = int(os.getenv("CMRE_HARVEST_PHOTOS", "4"))
HARVEST_CACHE_DB = os.getenv("CMRE_HARVEST_DB", "outputs/harvest.db")
PHOTO_CACHE_DIR  = os.getenv("CMRE_HARVEST_CACHE", "outputs/harvest_cache")

# ─── APIs ─────────────────────────────────────────────────────────────────────

PEXELS_API_KEY   = os.getenv("PEXELS_API_KEY", "")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")


class HarvestDB:
    """SQLite para rastrear o que já foi coletado (evita duplicatas)."""

    def __init__(self, db_path: str = HARVEST_CACHE_DB) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS harvested_photos (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_id    TEXT NOT NULL UNIQUE,
                    source      TEXT NOT NULL,
                    genre       TEXT NOT NULL,
                    url         TEXT NOT NULL,
                    local_path  TEXT,
                    analyzed    INTEGER DEFAULT 0,
                    cci_score   REAL,
                    error       TEXT,
                    harvested_at TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS harvest_runs (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date     TEXT NOT NULL UNIQUE,
                    genres_done  INTEGER DEFAULT 0,
                    photos_found INTEGER DEFAULT 0,
                    photos_ok    INTEGER DEFAULT 0,
                    started_at   TEXT NOT NULL,
                    finished_at  TEXT
                )
            """)

    def already_harvested(self, photo_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT id FROM harvested_photos WHERE photo_id = ?",
                (photo_id,)
            ).fetchone()
        return row is not None

    def record_photo(self, photo_id: str, source: str, genre: str,
                     url: str, local_path: str | None = None) -> None:
        with self._conn() as c:
            c.execute("""
                INSERT OR IGNORE INTO harvested_photos
                    (photo_id, source, genre, url, local_path, harvested_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (photo_id, source, genre, url, local_path,
                  datetime.utcnow().isoformat()))

    def mark_analyzed(self, photo_id: str, cci: float | None,
                      error: str | None = None) -> None:
        with self._conn() as c:
            c.execute("""
                UPDATE harvested_photos
                SET analyzed = 1, cci_score = ?, error = ?
                WHERE photo_id = ?
            """, (cci, error, photo_id))

    def start_run(self, run_date: str) -> int:
        with self._conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO harvest_runs
                    (run_date, started_at)
                VALUES (?, ?)
            """, (run_date, datetime.utcnow().isoformat()))
            return c.lastrowid  # type: ignore[return-value]

    def finish_run(self, run_date: str, genres_done: int,
                   photos_found: int, photos_ok: int) -> None:
        with self._conn() as c:
            c.execute("""
                UPDATE harvest_runs
                SET genres_done = ?, photos_found = ?, photos_ok = ?,
                    finished_at = ?
                WHERE run_date = ?
            """, (genres_done, photos_found, photos_ok,
                  datetime.utcnow().isoformat(), run_date))

    def stats(self) -> dict:
        with self._conn() as c:
            total = c.execute(
                "SELECT COUNT(*) FROM harvested_photos"
            ).fetchone()[0]
            analyzed = c.execute(
                "SELECT COUNT(*) FROM harvested_photos WHERE analyzed = 1"
            ).fetchone()[0]
            runs = c.execute(
                "SELECT COUNT(*) FROM harvest_runs"
            ).fetchone()[0]
            last = c.execute(
                "SELECT run_date, photos_ok FROM harvest_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return {
            "total_photos": total,
            "analyzed": analyzed,
            "pending_analysis": total - analyzed,
            "runs_total": runs,
            "last_run": last[0] if last else None,
            "last_run_ok": last[1] if last else 0,
        }

    def pending_analysis(self) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("""
                SELECT photo_id, genre, local_path
                FROM harvested_photos
                WHERE analyzed = 0 AND local_path IS NOT NULL AND error IS NULL
            """).fetchall()
        return [{"photo_id": r[0], "genre": r[1], "path": r[2]} for r in rows]


# ─── Fetchers ─────────────────────────────────────────────────────────────────

def _pexels_search(query: str, per_page: int) -> list[dict]:
    """Busca fotos no Pexels. Retorna lista de {id, url, thumb}."""
    if not PEXELS_API_KEY:
        return []
    q = urllib.parse.urlencode({"query": query, "per_page": per_page, "size": "large"})
    url = f"https://api.pexels.com/v1/search?{q}"
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        photos = []
        for p in data.get("photos", []):
            photos.append({
                "id": f"pexels_{p['id']}",
                "url": p["src"]["large2x"],
                "source": "pexels",
            })
        return photos
    except Exception as e:
        logger.warning(f"Pexels error for '{query}': {e}")
        return []


def _unsplash_search(query: str, per_page: int) -> list[dict]:
    """Busca fotos no Unsplash. Retorna lista de {id, url}."""
    if not UNSPLASH_API_KEY:
        return []
    q = urllib.parse.urlencode({"query": query, "per_page": per_page})
    url = f"https://api.unsplash.com/search/photos?{q}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Client-ID {UNSPLASH_API_KEY}"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        photos = []
        for p in data.get("results", []):
            photos.append({
                "id": f"unsplash_{p['id']}",
                "url": p["urls"]["full"],
                "source": "unsplash",
            })
        return photos
    except Exception as e:
        logger.warning(f"Unsplash error for '{query}': {e}")
        return []


def _download_photo(photo: dict, dest_dir: str) -> str | None:
    """Baixa a foto e retorna o caminho local."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    ext = "jpg"
    fname = dest / f"{photo['id']}.{ext}"
    if fname.exists():
        return str(fname)
    try:
        urllib.request.urlretrieve(photo["url"], str(fname))
        return str(fname)
    except Exception as e:
        logger.warning(f"Download failed for {photo['id']}: {e}")
        return None


# ─── Pipeline principal ───────────────────────────────────────────────────────

class DailyHarvest:
    """Executa a coleta diária de fotos e alimenta o banco de referências."""

    def __init__(self) -> None:
        self.hdb = HarvestDB()
        self.cache_dir = PHOTO_CACHE_DIR

    def run(self, genres: list[str] | None = None,
            analyze: bool = True) -> dict:
        """
        Executa o harvest para os gêneros especificados (ou todos).
        Se analyze=True, analisa cada foto nova com o PhotoAnalyzer.
        """
        today = str(date.today())
        genres = genres or SCENE_GENRES
        self.hdb.start_run(today)

        total_found = 0
        total_ok = 0
        results = {}

        print(f"\n🌾 CMRE Daily Harvest — {today}")
        print(f"   Gêneros: {len(genres)} | Fotos/gênero: {PHOTOS_PER_GENRE}")
        print(f"   APIs: {'Pexels ✓' if PEXELS_API_KEY else 'Pexels ✗'} | "
              f"{'Unsplash ✓' if UNSPLASH_API_KEY else 'Unsplash ✗'}")
        print()

        for genre in genres:
            query = GENRE_QUERIES.get(genre, genre)
            print(f"  📷 [{genre}] buscando '{query}'...", end=" ")

            # Busca em ambas as APIs
            photos = _pexels_search(query, PHOTOS_PER_GENRE)
            if len(photos) < PHOTOS_PER_GENRE:
                photos += _unsplash_search(query, PHOTOS_PER_GENRE - len(photos))
            photos = photos[:PHOTOS_PER_GENRE]

            new_photos = [p for p in photos if not self.hdb.already_harvested(p["id"])]
            print(f"{len(photos)} encontradas, {len(new_photos)} novas")

            total_found += len(new_photos)
            genre_ok = 0

            for photo in new_photos:
                # Download
                local_path = _download_photo(photo, self.cache_dir)
                self.hdb.record_photo(
                    photo["id"], photo["source"], genre,
                    photo["url"], local_path
                )

                if local_path and analyze:
                    cci = self._analyze_photo(photo["id"], genre, local_path)
                    if cci is not None:
                        genre_ok += 1
                elif local_path:
                    genre_ok += 1

                time.sleep(0.5)  # respeita rate limit

            total_ok += genre_ok
            results[genre] = {"found": len(new_photos), "ok": genre_ok}

        self.hdb.finish_run(today, len(genres), total_found, total_ok)

        print(f"\n✅ Harvest concluído: {total_found} novas fotos, "
              f"{total_ok} analisadas com sucesso")
        return {
            "date": today,
            "total_found": total_found,
            "total_ok": total_ok,
            "by_genre": results,
        }

    def analyze_pending(self) -> int:
        """Analisa fotos já baixadas mas ainda não analisadas."""
        pending = self.hdb.pending_analysis()
        print(f"🔍 Analisando {len(pending)} fotos pendentes...")
        ok = 0
        for item in pending:
            cci = self._analyze_photo(item["photo_id"], item["genre"], item["path"])
            if cci is not None:
                ok += 1
        return ok

    def _analyze_photo(self, photo_id: str, genre: str, path: str) -> float | None:
        """Analisa uma foto com o PhotoAnalyzer e salva no banco de referências."""
        try:
            from cmre_engine.analyzer import PhotoAnalyzer
            from cmre_engine.reference import ReferenceDatabase
            from cmre_engine.config import REFERENCE_DB_PATH

            analyzer = PhotoAnalyzer()
            db = ReferenceDatabase(REFERENCE_DB_PATH)
            report = analyzer.analyze(path, scene_genre=genre, db=db)

            self.hdb.mark_analyzed(photo_id, report.cci_score)
            return report.cci_score

        except Exception as e:
            logger.warning(f"Análise falhou para {photo_id}: {e}")
            self.hdb.mark_analyzed(photo_id, None, str(e))
            return None

    def status(self) -> dict:
        """Retorna estatísticas do harvest."""
        return self.hdb.stats()


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.WARNING)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    harvest = DailyHarvest()

    if cmd == "run":
        genres = sys.argv[2:] if len(sys.argv) > 2 else None
        result = harvest.run(genres=genres, analyze=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "analyze-pending":
        ok = harvest.analyze_pending()
        print(f"✅ {ok} fotos analisadas")

    elif cmd == "status":
        s = harvest.status()
        print(json.dumps(s, indent=2, ensure_ascii=False))

    else:
        print(f"Uso: python -m cmre_engine.learning.daily_harvest [run|analyze-pending|status]")
