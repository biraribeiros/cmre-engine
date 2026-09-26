"""
CMRE Engine — FastAPI Server

Endpoints:
  POST /process   — recebe briefing → retorna prompt final + CCI
  POST /generate  — recebe prompt + backend → gera imagem
  POST /feedback  — salva avaliação do usuário
  GET  /status    — estado do sistema
  GET  /stats     — estatísticas do banco de referências

Iniciar:
  uvicorn cmre_engine.api.server:app --reload --port 8000
"""
from __future__ import annotations

import os
import json
import uuid
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

# FastAPI
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CMRE Engine API",
    description="30-agent pipeline para geração de imagens ultra-realistas",
    version="2.0.0",
)

# CORS — permite o frontend local acessar a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve o frontend estático
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    briefing: str = Field(..., min_length=5, description="Descrição da imagem desejada")
    scene_genre: str = Field("geral", description="Gênero de cena (retrato, produto, etc.)")
    session_id: Optional[str] = None


class ProcessResponse(BaseModel):
    session_id: str
    prompt: str
    negative_prompt: str
    cci_score: float
    cci_approved: bool
    scene_genre: str
    processing_time_s: float
    blocks: dict
    validators: dict


class GenerateRequest(BaseModel):
    session_id: Optional[str] = None
    prompt: str
    negative_prompt: str = ""
    backend: str = Field("gemini", description="Backend: gemini | fooocus | dalle")
    width: int = 1024
    height: int = 1024


class GenerateResponse(BaseModel):
    session_id: str
    image_path: str
    image_url: Optional[str] = None
    backend: str
    generation_time_s: float


class FeedbackRequest(BaseModel):
    session_id: Optional[str] = None
    briefing: str = ""
    prompt_used: str = ""
    backend: str = ""
    cci_score: Optional[float] = None
    image_path: Optional[str] = None
    scores: dict = Field(default_factory=dict,
                         description="realismo, tecnica, composicao, coerencia, impacto (1–5)")
    comment: Optional[str] = None
    blocks: Optional[dict] = None
    validators: Optional[dict] = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    global_score: Optional[float]
    message: str


# ─── Cache de sessão em memória ───────────────────────────────────────────────

_session_cache: dict[str, dict] = {}

def _save_session(session_id: str, data: dict) -> None:
    _session_cache[session_id] = {**data, "updated_at": datetime.utcnow().isoformat()}
    # Limpa sessões antigas (>100)
    if len(_session_cache) > 100:
        oldest = sorted(_session_cache, key=lambda k: _session_cache[k].get("updated_at", ""))[0]
        _session_cache.pop(oldest, None)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "CMRE Engine API v2.0",
        "endpoints": ["/process", "/generate", "/feedback", "/status", "/stats"],
        "ui": "/ui/" if FRONTEND_DIR.exists() else None,
    }


@app.get("/status")
async def status():
    """Estado do sistema: backend ativo, banco de referências, modelo neural."""
    from cmre_engine.config import BACKEND_NAME, BACKEND
    from cmre_engine.config import REFERENCE_DB_PATH

    ref_stats: dict = {}
    try:
        from cmre_engine.reference import ReferenceDatabase
        db = ReferenceDatabase(REFERENCE_DB_PATH)
        ref_stats = db.stats()
    except Exception as e:
        ref_stats = {"error": str(e)}

    neural_status: dict = {}
    try:
        from cmre_engine.learning.neural_cci import NeuralCCIPredictor
        pred = NeuralCCIPredictor()
        pred.load()
        neural_status = pred.status()
    except Exception as e:
        neural_status = {"error": str(e)}

    harvest_stats: dict = {}
    try:
        from cmre_engine.learning.daily_harvest import HarvestDB
        hdb = HarvestDB()
        harvest_stats = hdb.stats()
    except Exception as e:
        harvest_stats = {"error": str(e)}

    feedback_stats: dict = {}
    try:
        from cmre_engine.learning.feedback import FeedbackDB
        fdb = FeedbackDB()
        feedback_stats = fdb.stats()
    except Exception as e:
        feedback_stats = {"error": str(e)}

    return {
        "backend_active": BACKEND_NAME,
        "backend_loaded": BACKEND is not None,
        "reference_db": ref_stats,
        "neural_model": neural_status,
        "harvest": harvest_stats,
        "feedback": feedback_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/stats")
async def stats():
    """Estatísticas do banco de referências e feedback."""
    from cmre_engine.config import REFERENCE_DB_PATH
    from cmre_engine.reference import ReferenceDatabase

    db = ReferenceDatabase(REFERENCE_DB_PATH)
    return db.stats()


@app.post("/process", response_model=ProcessResponse)
async def process_briefing(req: ProcessRequest):
    """
    Passa o briefing pelos 30 agentes CMRE e retorna o prompt final + CCI.
    Não gera imagem — apenas o prompt pronto para enviar ao backend escolhido.
    """
    from cmre_engine.orchestrator import Orchestrator
    from cmre_engine.config import REFERENCE_DB_PATH
    from cmre_engine.reference import ReferenceDatabase

    session_id = req.session_id or str(uuid.uuid4())[:8]
    t0 = time.time()

    # Carrega banco de referências
    try:
        db = ReferenceDatabase(REFERENCE_DB_PATH)
    except Exception:
        db = None

    # Processa via orquestrador
    try:
        orch = Orchestrator(verbose=False)
        result = orch.run(
            req.briefing,
            scene_genre=req.scene_genre,
            db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no pipeline: {e}")

    elapsed = round(time.time() - t0, 2)

    # Extrai campos do resultado
    prompt         = result.get("prompt", "")
    negative       = result.get("negative_prompt", "")
    cci_score      = result.get("cci_score", 0.0)
    cci_approved   = result.get("cci_approved", False)
    blocks         = result.get("blocks", {})
    validators     = result.get("validators", {})

    # Salva na sessão
    _save_session(session_id, {
        "briefing": req.briefing,
        "scene_genre": req.scene_genre,
        "prompt": prompt,
        "negative_prompt": negative,
        "cci_score": cci_score,
        "blocks": blocks,
        "validators": validators,
    })

    return ProcessResponse(
        session_id=session_id,
        prompt=prompt,
        negative_prompt=negative,
        cci_score=cci_score,
        cci_approved=cci_approved,
        scene_genre=req.scene_genre,
        processing_time_s=elapsed,
        blocks=blocks,
        validators=validators,
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate_image(req: GenerateRequest):
    """
    Gera a imagem a partir de um prompt já processado.
    O usuário escolhe o backend (gemini | fooocus | dalle).
    """
    import importlib

    session_id = req.session_id or str(uuid.uuid4())[:8]
    t0 = time.time()

    # Carrega o backend solicitado
    try:
        if req.backend == "gemini":
            from cmre_engine.backends.gemini_backend import GeminiBackend
            backend = GeminiBackend()
        elif req.backend == "fooocus":
            from cmre_engine.backends.fooocus_backend import FooocusBackend
            backend = FooocusBackend()
        elif req.backend == "dalle":
            from cmre_engine.backends.dalle_backend import DalleBackend
            backend = DalleBackend()
        else:
            raise HTTPException(status_code=400,
                                detail=f"Backend '{req.backend}' não suportado")
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Backend indisponível: {e}")

    # Gera a imagem
    try:
        image_path = backend.generate(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na geração: {e}")

    elapsed = round(time.time() - t0, 2)

    # URL local da imagem (se existir)
    image_url: str | None = None
    if image_path and Path(image_path).exists():
        image_url = f"/outputs/{Path(image_path).name}"

    # Atualiza sessão
    sess = _session_cache.get(session_id, {})
    sess.update({"image_path": image_path, "backend": req.backend})
    _save_session(session_id, sess)

    return GenerateResponse(
        session_id=session_id,
        image_path=image_path or "",
        image_url=image_url,
        backend=req.backend,
        generation_time_s=elapsed,
    )


@app.post("/feedback", response_model=FeedbackResponse)
async def save_feedback(req: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    Salva a avaliação do usuário para a imagem gerada.
    Dispara re-treinamento neural em background quando há dados suficientes.
    """
    from cmre_engine.learning.feedback import FeedbackDB, FeedbackEntry

    # Recupera dados da sessão se disponível
    session = _session_cache.get(req.session_id or "", {})
    entry = FeedbackEntry(
        session_id=req.session_id,
        briefing=req.briefing or session.get("briefing", ""),
        prompt_used=req.prompt_used or session.get("prompt", ""),
        backend=req.backend or session.get("backend", ""),
        cci_score=req.cci_score if req.cci_score is not None else session.get("cci_score"),
        image_path=req.image_path or session.get("image_path"),
        scores=req.scores,
        comment=req.comment,
        blocks=req.blocks or session.get("blocks"),
        validators=req.validators or session.get("validators"),
    )

    errors = entry.validate()
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    db = FeedbackDB()
    fid = db.save(entry)

    # Re-treina em background se múltiplos de 20 feedbacks
    total = db.stats()["total_feedbacks"]
    if total > 0 and total % 20 == 0:
        background_tasks.add_task(_background_retrain)

    return FeedbackResponse(
        feedback_id=fid,
        global_score=entry.global_score,
        message=f"Obrigado! Score global: {entry.global_score:.2f}" if entry.global_score else "Feedback salvo",
    )


async def _background_retrain() -> None:
    """Re-treina a rede neural em background."""
    try:
        from cmre_engine.learning.neural_cci import NeuralTrainer
        trainer = NeuralTrainer()
        trainer.run(also_calibrate_weights=True)
    except Exception as e:
        logger.warning(f"Background retrain falhou: {e}")


# ─── Serve outputs ────────────────────────────────────────────────────────────

@app.get("/outputs/{filename}")
async def serve_output(filename: str):
    """Serve imagens geradas."""
    output_path = Path("outputs") / filename
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(str(output_path))


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
