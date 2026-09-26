"""
CMRE Learning — Sistema de Aprendizado Contínuo

Módulos:
  daily_harvest     — coleta diária de fotos por API (Pexels/Unsplash)
  feedback          — coleta de avaliações do usuário (1–5 por dimensão)
  weight_calibrator — recalibração dos pesos do CCI a partir do feedback
  neural_cci        — rede neural MLP para prever CCI e score do usuário
"""

from .daily_harvest import DailyHarvest
from .feedback import FeedbackDB, FeedbackCollector, FeedbackEntry
from .weight_calibrator import WeightCalibrator, load_weights, save_weights
from .neural_cci import NeuralCCIPredictor, NeuralTrainer

__all__ = [
    "DailyHarvest",
    "FeedbackDB",
    "FeedbackCollector",
    "FeedbackEntry",
    "WeightCalibrator",
    "load_weights",
    "save_weights",
    "NeuralCCIPredictor",
    "NeuralTrainer",
]
