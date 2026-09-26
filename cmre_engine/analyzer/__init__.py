"""
CMRE Engine — Módulo de análise de fotos reais (Lado A).
Usa visão computacional (Gemini multimodal) para extrair os 16 blocos técnicos
de qualquer fotografia real, calcular o CCI e armazenar como referência.
"""
from .photo_analyzer import PhotoAnalyzer

__all__ = ["PhotoAnalyzer"]
