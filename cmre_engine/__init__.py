"""
CMRE Engine — Cross-Modal Realism Engine
Motor de 30 agentes para geração de imagem ultra-realista.

Uso rápido:
    from cmre_engine import CMREOrchestrator
    engine = CMREOrchestrator()
    report = engine.run("Mulher fotografando em floresta tropical ao entardecer")
    print(report.summary())
"""
from .orchestrator import CMREOrchestrator
from .models import CCIReport, TechnicalBlocks, ValidationResult

__version__ = "1.0.0"
__author__ = "Via Multimidia — Bira Ribeiro"
__all__ = ["CMREOrchestrator", "CCIReport", "TechnicalBlocks", "ValidationResult"]
