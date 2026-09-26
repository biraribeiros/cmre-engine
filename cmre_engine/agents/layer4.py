"""
CMRE Engine — Camada 4: Síntese e Execução
Agente 26: CCICalculator    — calcula o Índice de Coerência Cross-Modal
Agente 27: ConflictResolver — resolve conflitos detectados pelos validadores
Agente 28: PromptSynthesizer — constrói o prompt final otimizado
Agente 29: NegativePromptFinal — consolida o prompt negativo
Agente 30: Executor          — envia para o backend selecionado

O Executor (Agente 30) consulta o banco de referências (Lado A) antes de
gerar, usando as referências como âncora de calibração do prompt.
"""
import statistics
from typing import Optional
from ..models import TechnicalBlocks, ValidationResult, CCIReport, ReferenceEntry


# Pesos por par de validação (quanto cada domínio impacta o CCI final)
PAIR_WEIGHTS = {
    "Luz × Sombra":         0.22,
    "Clima × Corpo":        0.12,
    "Câmera × Física":      0.15,
    "Anatomia × Física":    0.20,
    "Materiais × Cor":      0.13,
    "Entropia × Contexto":  0.10,
    "Escala × Proporção":   0.08,
}


class CCICalculator:
    """
    Agente 26 — CCICalculator
    CCI = Σ (peso_par × score_par) / Σ pesos
    Escala 0.0–1.0. Aprovação ≥ 0.75.
    """

    def calculate(self, validations: list[ValidationResult]) -> float:
        if not validations:
            return 0.5

        total_weight = 0.0
        weighted_sum = 0.0

        for v in validations:
            weight = PAIR_WEIGHTS.get(v.pair, 0.1)
            weighted_sum += weight * v.score
            total_weight += weight

        cci = weighted_sum / total_weight if total_weight > 0 else 0.5
        return round(min(1.0, max(0.0, cci)), 3)


class ConflictResolver:
    """
    Agente 27 — ConflictResolver
    Gera ações de resolução para cada conflito detectado.
    Retorna lista de strings descrevendo as correções aplicadas.
    """

    def resolve(self, blocks: TechnicalBlocks, validations: list[ValidationResult]) -> tuple[TechnicalBlocks, list[str]]:
        resolved = []

        for v in validations:
            if v.passed:
                continue

            # Aplicar sugestões automáticas simples
            for suggestion in v.suggestions:
                # Temperatura de luz × cor
                if "Temperatura" in suggestion and "alinhe" in suggestion.lower():
                    if "fria" in blocks.luz.lower():
                        blocks.cor = blocks.cor + ", skin tone protection ativo"
                    resolved.append(f"[{v.pair}] Proteção de skin tone adicionada ao grading")

                # Vestuário × clima
                if "casaco" in suggestion.lower() and "neve" in blocks.ambiente.lower():
                    blocks.sujeito = blocks.sujeito + ", vestindo casaco pesado de inverno, luvas, bota neve"
                    resolved.append(f"[{v.pair}] Vestuário de inverno adicionado ao sujeito")

                # Motion blur × shutter
                if "motion blur" in suggestion.lower():
                    blocks.exposicao = blocks.exposicao.replace("1/2000", "1/60").replace("1/4000", "1/60")
                    resolved.append(f"[{v.pair}] Shutter ajustado para permitir motion blur")

                # Metal sem reflexo
                if "reflexos especulares" in suggestion.lower():
                    blocks.materiais = blocks.materiais + ", reflexos especulares do ambiente"
                    resolved.append(f"[{v.pair}] Reflexos especulares adicionados aos materiais")

        return blocks, resolved


class PromptSynthesizer:
    """
    Agente 28 — PromptSynthesizer
    Constrói o prompt final em inglês, estruturado e otimizado
    para modelos de geração de imagem (Gemini Flash Image, Fooocus, DALL-E).
    """

    # Ordem de importância dos blocos no prompt
    BLOCK_ORDER = [
        ("sujeito", "SUBJECT"),
        ("enquadramento", "FRAMING"),
        ("luz", "LIGHTING"),
        ("cor", "COLOR"),
        ("sensor_meio", "CAMERA"),
        ("optica", "OPTICS"),
        ("exposicao", "EXPOSURE"),
        ("materiais", "MATERIALS"),
        ("ambiente", "ENVIRONMENT"),
        ("profundidade", "DEPTH"),
        ("textura_captura", "FILM TEXTURE"),
        ("imperfeicoes", "OPTICAL IMPERFECTIONS"),
        ("entropia", "SCENE COMPLEXITY"),
        ("movimento_fisica", "PHYSICS"),
        ("saida", "OUTPUT"),
    ]

    def synthesize(self, blocks: TechnicalBlocks, cci: float) -> str:
        parts = []

        # Header de qualidade
        parts.append(
            "Ultra-realistic photograph, photorealistic, "
            "shot on professional camera, physically accurate lighting, "
            "physically plausible scene"
        )

        # Blocos em ordem de importância
        for field_name, label in self.BLOCK_ORDER:
            value = getattr(blocks, field_name, "").strip()
            if value and value != "não especificado":
                parts.append(f"{value}")

        # Footer de qualidade baseado no CCI
        if cci >= 0.90:
            parts.append("masterpiece photograph, award-winning image, technically flawless")
        elif cci >= 0.75:
            parts.append("high-quality photograph, technically consistent, professional grade")
        else:
            parts.append("photograph, realistic, technically coherent")

        return ", ".join(p for p in parts if p)


class NegativePromptFinal:
    """
    Agente 29 — NegativePromptFinal
    Consolida o prompt negativo das exclusões CMRE com negativos universais
    de qualidade para o modelo de geração selecionado.
    """

    # Negativos universais para qualquer modelo
    UNIVERSAL = [
        "worst quality", "low quality", "normal quality", "lowres",
        "bad anatomy", "bad hands", "error", "missing fingers",
        "extra digit", "fewer digits", "cropped", "jpeg artifacts",
        "signature", "watermark", "username", "blurry",
        "artist name", "text", "logo", "3d render", "cgi",
        "cartoon", "anime", "illustration", "painting",
        "drawing", "sketch", "unrealistic", "overexposed",
        "underexposed", "nsfw",
    ]

    def build(self, blocks_exclusoes: str) -> str:
        custom = [e.strip() for e in blocks_exclusoes.split(",") if e.strip()]
        all_negatives = self.UNIVERSAL + custom
        # Deduplica mantendo ordem
        seen = set()
        unique = []
        for n in all_negatives:
            if n.lower() not in seen:
                seen.add(n.lower())
                unique.append(n)
        return ", ".join(unique[:40])


class ReferenceEnricher:
    """
    Agente 30a — ReferenceEnricher (Lado B — consulta ao banco de referências)

    Antes de gerar, consulta o banco de fotos reais analisadas (Lado A) e
    enriquece o prompt com características técnicas de referências com CCI alto.

    Se nenhuma referência for encontrada, retorna o prompt inalterado.
    """

    def enrich(
        self,
        prompt: str,
        scene_genre: str,
        db,
        top_k: int = 3,
        min_cci: float = 0.70,
    ) -> tuple[str, list[ReferenceEntry]]:
        """
        Busca referências do mesmo gênero e injeta detalhes técnicos no prompt.

        Returns:
            (prompt_enriquecido, lista_de_referencias_usadas)
        """
        if db is None:
            return prompt, []

        try:
            refs = db.find_similar(scene_genre, min_cci=min_cci, limit=top_k)
        except Exception:
            return prompt, []

        if not refs:
            return prompt, []

        # Extrair características técnicas das melhores referências
        ref_details = []
        for ref in refs:
            detail_parts = []
            if ref.blocks.luz:
                detail_parts.append(ref.blocks.luz)
            if ref.blocks.optica:
                detail_parts.append(ref.blocks.optica)
            if ref.blocks.textura_captura:
                detail_parts.append(ref.blocks.textura_captura)
            if detail_parts:
                ref_details.append(f"[ref CCI={ref.cci_score:.2f}] {', '.join(detail_parts)}")

        if not ref_details:
            return prompt, refs

        # Injeta a ancora de referência no prompt, antes do footer de qualidade
        reference_anchor = (
            f"calibrated to real photographic reference "
            f"({'; '.join(ref_details[:2])})"
        )
        enriched = prompt + ", " + reference_anchor

        return enriched, refs


class Executor:
    """
    Agente 30 — Executor
    Conecta ao backend configurado e executa a geração de imagem.
    Consulta o banco de referências (Lado A) antes de gerar para calibrar o prompt.
    Retorna o caminho do arquivo gerado.
    """

    def __init__(self):
        self.enricher = ReferenceEnricher()

    def execute(
        self,
        prompt: str,
        negative: str,
        backend,
        briefing: str,
        cci: float,
        validations: list[ValidationResult],
        blocks: TechnicalBlocks,
        scene_genre: str = "",
        db=None,
    ) -> CCIReport:

        print(f"\n🎨 Executando geração | CCI: {cci:.2f}")

        # ─── Enriquecimento com banco de referências (Lado B) ─────────────────
        refs_used = []
        if db and scene_genre:
            from ..config import REFERENCE_MIN_CCI, REFERENCE_TOP_K
            prompt_enriched, refs_used = self.enricher.enrich(
                prompt, scene_genre, db,
                top_k=REFERENCE_TOP_K,
                min_cci=REFERENCE_MIN_CCI,
            )
            if refs_used:
                print(f"📚 {len(refs_used)} referência(s) de '{scene_genre}' "
                      f"usada(s) como âncora (CCI máx: {refs_used[0].cci_score:.2f})")
                prompt = prompt_enriched
        # ─────────────────────────────────────────────────────────────────────

        print(f"📝 Prompt ({len(prompt)} chars)")
        print(f"🚫 Negative ({len(negative)} chars)")

        # Tenta gerar a imagem
        image_path = None
        backend_name = type(backend).__name__.replace("Backend", "").lower()

        try:
            image_path = backend.generate(prompt, negative)
            print(f"✅ Imagem gerada: {image_path}")
        except Exception as e:
            print(f"❌ Erro no backend {backend_name}: {e}")

        # Registra referências usadas nos metadados do relatório
        ref_meta = [
            {"id": r.id, "image_path": r.image_path, "cci": r.cci_score}
            for r in refs_used
        ] if refs_used else []

        return CCIReport(
            cci_score=cci,
            prompt_final=prompt,
            negative_prompt=negative,
            validations=validations,
            backend_used=backend_name,
            image_path=image_path,
            briefing_original=briefing,
            blocks=blocks,
        )
