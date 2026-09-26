"""
CMRE Engine — Camada 3: 7 Validadores Cross-Domain
Agentes 19–25 — detectam conflitos entre pares de domínios visuais.

Cada validador verifica coerência entre dois domínios e retorna:
- score (0.0–1.0)
- conflicts (lista de problemas encontrados)
- suggestions (como resolver)
"""
from ..models import TechnicalBlocks, ValidationResult


class CrossDomainValidators:
    """Coordena os 7 validadores cross-domain."""

    def validate_all(self, blocks: TechnicalBlocks) -> list[ValidationResult]:
        validators = [
            Agente19_LuzSombra(),
            Agente20_ClimaCorpo(),
            Agente21_CameraFisica(),
            Agente22_AnatomiaFisica(),
            Agente23_MateriaisCor(),
            Agente24_EntropiaContexto(),
            Agente25_EscalaProporção(),
        ]
        results = []
        for v in validators:
            result = v.validate(blocks)
            results.append(result)
        return results


class Agente19_LuzSombra:
    """
    Agente 19 — Validador Luz × Sombra
    Verifica se a direção da luz é consistente com as sombras esperadas.
    Ex: 'luz dourada ao entardecer' + 'sombras azuis frias' = conflito.
    """
    pair = "Luz × Sombra"

    def validate(self, blocks: TechnicalBlocks) -> ValidationResult:
        conflicts = []
        suggestions = []
        score = 1.0

        luz = blocks.luz.lower()
        cor = blocks.cor.lower()

        # Detectar inconsistência de temperatura de cor
        if ("5500k" in luz or "fria" in luz or "6500k" in luz) and \
           ("quente" in cor or "teal-orange" in cor or "3200k" in luz):
            conflicts.append("Temperatura de luz fria incompatível com grading quente")
            suggestions.append("Alinhe a temperatura: use 5500K neutro ou escolha um grading")
            score -= 0.3

        # Luz de estúdio + ambiente externo
        if "estúdio" in luz and ("floresta" in blocks.ambiente.lower() or
                                  "praia" in blocks.ambiente.lower()):
            conflicts.append("Luz de estúdio controlada em ambiente externo")
            suggestions.append("Use luz natural difusa ou um reflector como key light")
            score -= 0.2

        # Neon + luz natural = raro mas possível (ex.: cyberpunk)
        if "neon" in luz and "natural" in luz:
            conflicts.append("Mistura de luz neon artificial com 'natural' é ambígua")
            suggestions.append("Especifique: neon predominante ou apenas detalhe ambiente?")
            score -= 0.1

        return ValidationResult(
            pair=self.pair,
            score=max(0.0, score),
            conflicts=conflicts,
            suggestions=suggestions,
            passed=score >= 0.7,
        )


class Agente20_ClimaCorpo:
    """
    Agente 20 — Validador Clima × Corpo
    Verifica se o vestuário/aparência humana é coerente com o clima da cena.
    Ex: 'neve pesada' + 'pessoa de camiseta' = conflito.
    """
    pair = "Clima × Corpo"

    def validate(self, blocks: TechnicalBlocks) -> ValidationResult:
        conflicts = []
        suggestions = []
        score = 1.0

        sujeito = blocks.sujeito.lower()
        ambiente = blocks.ambiente.lower()

        # Clima frio + roupa de verão
        cold_markers = ["neve", "gelo", "frio", "inverno", "blizzard", "arctic"]
        hot_clothes = ["camiseta", "biquíni", "shorts", "summer dress", "sandália"]
        if any(c in ambiente for c in cold_markers) and \
           any(h in sujeito for h in hot_clothes):
            conflicts.append("Vestuário de verão em ambiente de frio extremo")
            suggestions.append("Adicione casaco pesado, luvas, bota neve ao sujeito")
            score -= 0.4

        # Clima quente + agasalho pesado
        hot_markers = ["deserto", "praia tropical", "verão", "calor"]
        winter_clothes = ["casaco de inverno", "sobretudo", "parka", "luvas de inverno"]
        if any(h in ambiente for h in hot_markers) and \
           any(w in sujeito for w in winter_clothes):
            conflicts.append("Agasalho de inverno em ambiente tropical")
            suggestions.append("Adapte o vestuário ao clima quente da cena")
            score -= 0.4

        return ValidationResult(
            pair=self.pair,
            score=max(0.0, score),
            conflicts=conflicts,
            suggestions=suggestions,
            passed=score >= 0.7,
        )


class Agente21_CameraFisica:
    """
    Agente 21 — Validador Câmera × Física
    Verifica se o equipamento descrito é capaz de capturar a física descrita.
    Ex: câmera estática + velocidade de obturador impossível para movimento.
    """
    pair = "Câmera × Física"

    def validate(self, blocks: TechnicalBlocks) -> ValidationResult:
        conflicts = []
        suggestions = []
        score = 1.0

        sensor = blocks.sensor_meio.lower()
        exposicao = blocks.exposicao.lower()
        movimento = blocks.movimento_fisica.lower()

        # Motion blur intencional + shutter ultra-rápido = impossível
        if "motion blur" in movimento and ("1/2000" in exposicao or "1/4000" in exposicao):
            conflicts.append("Motion blur impossível com obturador ultra-rápido (1/2000s+)")
            suggestions.append("Use 1/30s–1/60s para motion blur natural")
            score -= 0.3

        # Câmera estática de estúdio descrita para ação esportiva
        if "tripé" in sensor and "ação" in movimento and "velocidade" in movimento:
            conflicts.append("Câmera em tripé para capturar ação dinâmica")
            suggestions.append("Descreva câmera de mão ou gimbal para movimento")
            score -= 0.2

        return ValidationResult(
            pair=self.pair,
            score=max(0.0, score),
            conflicts=conflicts,
            suggestions=suggestions,
            passed=score >= 0.7,
        )


class Agente22_AnatomiaFisica:
    """
    Agente 22 — Validador Anatomia × Física
    Detecta poses humanas fisicamente impossíveis ou anatomicamente incoerentes.
    """
    pair = "Anatomia × Física"

    def validate(self, blocks: TechnicalBlocks) -> ValidationResult:
        conflicts = []
        suggestions = []
        score = 1.0

        sujeito = blocks.sujeito.lower()

        # Sinais de risco de má anatomia
        risky_terms = [
            "pulando muito alto", "voando sem apoio", "braço esticado 180 graus"
        ]
        for term in risky_terms:
            if term in sujeito:
                conflicts.append(f"Pose de risco anatômico: '{term}'")
                suggestions.append("Reforce no prompt: 'anatomia humana perfeita, pose fisicamente plausível'")
                score -= 0.2

        # Múltiplas pessoas sem referência clara
        if ("grupo" in sujeito or "multidão" in sujeito) and "crowd" not in sujeito:
            suggestions.append("Para grupos, adicione: 'cada pessoa com anatomia individual perfeita'")
            score -= 0.05  # Só um lembrete, não um conflito grave

        return ValidationResult(
            pair=self.pair,
            score=max(0.0, score),
            conflicts=conflicts,
            suggestions=suggestions,
            passed=score >= 0.7,
        )


class Agente23_MateriaisCor:
    """
    Agente 23 — Validador Materiais × Cor
    Verifica se as propriedades de cor são fisicamente coerentes com os materiais.
    Ex: metal espelhado sem reflexos coerentes, pele sem subsurface scattering.
    """
    pair = "Materiais × Cor"

    def validate(self, blocks: TechnicalBlocks) -> ValidationResult:
        conflicts = []
        suggestions = []
        score = 1.0

        materiais = blocks.materiais.lower()
        cor = blocks.cor.lower()
        luz = blocks.luz.lower()

        # Metal polido sem reflexos especulares na descrição de cor
        if "metal polido" in materiais and "especular" not in materiais and \
           "reflexo" not in materiais:
            suggestions.append("Metal polido precisa de reflexos especulares do ambiente")
            score -= 0.1

        # Pele com grading muito verde/teal
        if "pele" in materiais and "teal" in cor:
            conflicts.append("Grading teal pode tornar a pele verde/doentia")
            suggestions.append("Proteja os tons de pele (skin tones protection) no grading")
            score -= 0.25

        # Vidro/transparente sem refração descrita
        if "vidro" in materiais and "refração" not in materiais:
            suggestions.append("Adicione 'refrações realistas' à descrição do vidro")
            score -= 0.05

        return ValidationResult(
            pair=self.pair,
            score=max(0.0, score),
            conflicts=conflicts,
            suggestions=suggestions,
            passed=score >= 0.7,
        )


class Agente24_EntropiaContexto:
    """
    Agente 24 — Validador Entropia × Contexto
    Verifica se o nível de detalhe/caos da cena é coerente com o contexto narrativo.
    """
    pair = "Entropia × Contexto"

    def validate(self, blocks: TechnicalBlocks) -> ValidationResult:
        conflicts = []
        suggestions = []
        score = 1.0

        entropia = blocks.entropia.lower()
        ambiente = blocks.ambiente.lower()
        saida = blocks.saida.lower()

        # Produto em fundo sujo/caótico
        if "produto" in ambiente and ("alta entropia" in entropia or "densa" in entropia):
            conflicts.append("Cena de produto com fundo caótico reduz foco no item")
            suggestions.append("Use fundo limpo ou entropia baixa para produto")
            score -= 0.3

        # Retrato editorial em cenário minimalista marcado como 'caótico'
        if "minimalista" in entropia and "urbano" in ambiente:
            suggestions.append("Ambiente urbano tende a alta entropia — verifique se 'minimalista' é intencional")
            score -= 0.05

        return ValidationResult(
            pair=self.pair,
            score=max(0.0, score),
            conflicts=conflicts,
            suggestions=suggestions,
            passed=score >= 0.7,
        )


class Agente25_EscalaProporção:
    """
    Agente 25 — Validador Escala × Proporção
    Detecta inconsistências de tamanho relativo entre elementos da cena.
    """
    pair = "Escala × Proporção"

    def validate(self, blocks: TechnicalBlocks) -> ValidationResult:
        conflicts = []
        suggestions = []
        score = 1.0

        sujeito = blocks.sujeito.lower()
        ambiente = blocks.ambiente.lower()
        enquadramento = blocks.enquadramento.lower()

        # Plano macro de objeto grande sem justificativa
        if ("close-up extremo" in enquadramento or "macro" in enquadramento) and \
           ("carro" in sujeito or "construção" in sujeito or "edifício" in sujeito):
            suggestions.append("Macro de objeto grande: esclareça se é detalhe específico (parafuso, textura)")
            score -= 0.1

        # Pessoa descrita como "minúscula" em interior pequeno
        if "minúscula" in sujeito and "interior" in ambiente and "vasto" not in ambiente:
            conflicts.append("Pessoa 'minúscula' em interior comum: escala inconsistente")
            suggestions.append("Adicione: 'escala humana realista' ou amplie o ambiente")
            score -= 0.2

        return ValidationResult(
            pair=self.pair,
            score=max(0.0, score),
            conflicts=conflicts,
            suggestions=suggestions,
            passed=score >= 0.7,
        )
