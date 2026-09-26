"""
CMRE Engine — Modelos de dados compartilhados entre todas as camadas.
"""
from dataclasses import dataclass, field
from typing import Optional
import datetime


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


# ─── Modelos do Lado A — Análise de Fotos Reais ──────────────────────────────

@dataclass
class PhotoAnalysisReport:
    """
    Relatório gerado pelo Lado A (análise de foto real).
    Espelha o CCIReport, mas a origem é uma imagem real, não um briefing.
    """
    image_path: str                           # Caminho da foto analisada
    cci_score: float                          # CCI calculado sobre os blocos extraídos
    blocks: TechnicalBlocks = field(default_factory=TechnicalBlocks)
    validations: list[ValidationResult] = field(default_factory=list)
    scene_genre: str = ""                     # Classificação: retrato, paisagem, produto...
    metadata: dict = field(default_factory=dict)  # Dados extras (câmera EXIF, etc.)
    image_hash: str = ""                      # SHA256 do arquivo de imagem

    def summary(self) -> str:
        status = "✅ REFERÊNCIA APROVADA" if self.cci_score >= 0.75 else "⚠️ REFERÊNCIA FRACA"
        return (
            f"{status} | CCI Real: {self.cci_score:.2f} | "
            f"Gênero: {self.scene_genre or 'indefinido'} | "
            f"Foto: {self.image_path}"
        )


@dataclass
class ReferenceEntry:
    """
    Registro armazenado no banco de referências (SQLite).
    Cada entrada representa uma foto real analisada pelos 30 agentes.
    """
    image_path: str
    image_hash: str
    scene_genre: str
    blocks: TechnicalBlocks
    cci_score: float
    validator_scores: dict                    # {"Luz × Sombra": 0.9, ...}
    created_at: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat()
    )
    metadata: dict = field(default_factory=dict)
    id: Optional[int] = None                 # Atribuído pelo banco ao inserir
