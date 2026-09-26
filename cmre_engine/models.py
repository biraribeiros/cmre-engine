"""
CMRE Engine — Modelos de dados compartilhados entre todas as camadas.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TechnicalBlocks:
    """Os 16 blocos técnicos da ficha CMRE."""
    saida: str = ""            # Bloco 1: Resolução, codec, formato de entrega
    enquadramento: str = ""    # Bloco 2: Plano, ângulo, composição
    sensor_meio: str = ""      # Bloco 3: Câmera/sensor ou meio físico
    optica: str = ""           # Bloco 4: Lente, distância focal, abertura
    exposicao: str = ""        # Bloco 5: ISO, shutter, abertura
    luz: str = ""              # Bloco 6: Tipo, direção, temperatura de luz
    cor: str = ""              # Bloco 7: Paleta, LUT, grading
    sujeito: str = ""          # Bloco 8: Descrição do sujeito principal
    materiais: str = ""        # Bloco 9: Texturas, superfícies, reflectância
    ambiente: str = ""         # Bloco 10: Cenário, locação, contexto espacial
    profundidade: str = ""     # Bloco 11: DoF, bokeh, foco seletivo
    textura_captura: str = ""  # Bloco 12: Grain, noise, imperfeições de sensor
    imperfeicoes: str = ""     # Bloco 13: Aberrações, vignette, distorções
    entropia: str = ""         # Bloco 14: Ordem vs. caos visual, clutter
    movimento_fisica: str = "" # Bloco 15: Motion blur, physics, dinâmica
    exclusoes: str = ""        # Bloco 16: O que NÃO deve aparecer (negative)


@dataclass
class ValidationResult:
    """Resultado de um validador cross-domain."""
    pair: str               # Ex.: "Luz × Sombra"
    score: float            # 0.0 a 1.0
    conflicts: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class CCIReport:
    """Relatório final do CCI (Cross-modal Coherence Index)."""
    cci_score: float                      # 0.0 a 1.0
    prompt_final: str
    negative_prompt: str
    validations: list[ValidationResult] = field(default_factory=list)
    conflicts_resolved: list[str] = field(default_factory=list)
    backend_used: str = "gemini"
    image_path: Optional[str] = None
    briefing_original: str = ""
    blocks: Optional[TechnicalBlocks] = None

    def summary(self) -> str:
        status = "✅ APROVADO" if self.cci_score >= 0.75 else "⚠️ REVISAR"
        return (
            f"{status} | CCI: {self.cci_score:.2f} | "
            f"Backend: {self.backend_used} | "
            f"Imagem: {self.image_path or 'não gerada'}"
        )
