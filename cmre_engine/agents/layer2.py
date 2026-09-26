"""
CMRE Engine — Camada 2: 16 Especialistas em Blocos Técnicos
Agentes 03–18 — cada um preenche um bloco da Ficha Técnica CMRE.
"""
from ..models import TechnicalBlocks


class TechnicalBlockAgents:
    """
    Coordena os 16 agentes especialistas em blocos técnicos.
    Cada agente recebe o briefing + dados da L1 e retorna
    especificação técnica para seu bloco.
    """

    def process(self, briefing: str, intent_data: dict, classification: dict) -> TechnicalBlocks:
        blocks = TechnicalBlocks()
        active = set(classification.get("active_blocks", []))
        domain = classification.get("primary_domain", "geral")
        kw = " ".join(intent_data.get("keywords", []))

        if "saida" in active:
            blocks.saida = Agente03_Saida().process(briefing, domain)
        if "enquadramento" in active:
            blocks.enquadramento = Agente04_Enquadramento().process(briefing, kw)
        if "sensor_meio" in active:
            blocks.sensor_meio = Agente05_SensorMeio().process(briefing, domain)
        if "optica" in active:
            blocks.optica = Agente06_Optica().process(briefing, domain)
        if "exposicao" in active:
            blocks.exposicao = Agente07_Exposicao().process(briefing, domain)
        if "luz" in active:
            blocks.luz = Agente08_Luz().process(briefing, kw)
        if "cor" in active:
            blocks.cor = Agente09_Cor().process(briefing, domain)
        if "sujeito" in active:
            blocks.sujeito = Agente10_Sujeito().process(briefing)
        if "materiais" in active:
            blocks.materiais = Agente11_Materiais().process(briefing, kw)
        if "ambiente" in active:
            blocks.ambiente = Agente12_Ambiente().process(briefing)
        if "profundidade" in active:
            blocks.profundidade = Agente13_Profundidade().process(briefing, domain)
        if "textura_captura" in active:
            blocks.textura_captura = Agente14_TexturaCaptura().process(briefing, domain)
        if "imperfeicoes" in active:
            blocks.imperfeicoes = Agente15_Imperfeicoes().process(briefing, domain)
        if "entropia" in active:
            blocks.entropia = Agente16_Entropia().process(briefing, domain)
        if "movimento_fisica" in active:
            blocks.movimento_fisica = Agente17_MovimentoFisica().process(briefing)
        if "exclusoes" in active:
            blocks.exclusoes = Agente18_Exclusoes().process(briefing, kw)

        return blocks


# ─── Agentes 03–18 ────────────────────────────────────────────────────────────

class Agente03_Saida:
    """Agente 03 — Saída: resolução, codec, formato de entrega."""
    DEFAULTS = {
        "retrato": "4K UHD, aspect ratio 4:5 portrait, JPEG alta qualidade",
        "paisagem": "4K UHD, aspect ratio 16:9, JPEG alta qualidade",
        "produto": "Square 1:1 ou 4:5, PNG sem fundo ou JPEG branco, alta resolução",
        "cinema": "Cinemascope 2.39:1, 4K DCI, JPEG ou RAW simulado",
        "geral": "4K UHD, aspect ratio 16:9, JPEG ultra qualidade",
    }
    def process(self, briefing: str, domain: str) -> str:
        return self.DEFAULTS.get(domain, self.DEFAULTS["geral"])


class Agente04_Enquadramento:
    """Agente 04 — Enquadramento: plano, ângulo, composição."""
    ANGLE_KEYWORDS = {
        "aerial": "plano aéreo, drone shot, bird's eye view",
        "low angle": "contra-plongée, câmera baixa apontando para cima",
        "close": "primeiro plano fechado, close-up, detalhe extremo",
        "wide": "plano geral, grande angular, paisagem ampla",
    }
    def process(self, briefing: str, keywords: str) -> str:
        text = (briefing + " " + keywords).lower()
        for marker, value in self.ANGLE_KEYWORDS.items():
            if marker in text:
                return value
        # Padrão: plano médio regra dos terços
        return "plano médio, composição regra dos terços, horizonte equilibrado"


class Agente05_SensorMeio:
    """Agente 05 — Sensor/Meio: câmera/sensor ou meio físico."""
    DOMAIN_MAP = {
        "cinema": "Sony VENICE 2, sensor full-frame 8.6K, simulação de película",
        "documental": "Sony A7 IV, sensor full-frame, ISo auto, grain natural",
        "retrato": "Nikon Z9, full-frame 45MP, alta definição de pele",
        "produto": "Phase One IQ4, médio formato, 150MP, cores perfeitas",
        "paisagem": "Sony A7R V, full-frame 61MP, grande latitude dinâmica",
        "acao": "Sony A1, full-frame 50MP, 30fps, congelamento de movimento",
        "macro": "Canon EOS R5 + macro lens, full-frame, foco manual preciso",
    }
    def process(self, briefing: str, domain: str) -> str:
        return self.DOMAIN_MAP.get(domain, "Câmera full-frame profissional, sensor de alta resolução")


class Agente06_Optica:
    """Agente 06 — Óptica: lente, distância focal, abertura."""
    DOMAIN_MAP = {
        "retrato": "85mm f/1.4, abertura máxima para bokeh suave, sem distorção facial",
        "cinema": "Zeiss Master Prime 35mm T1.3, óptica cinematográfica",
        "paisagem": "Grande angular 14-24mm f/2.8, máxima cobertura, sem vinheta",
        "produto": "Macro 100mm f/2.8, perspectiva plana, distorção zero",
        "acao": "Teleobjetiva 400mm f/2.8, isolamento do sujeito em movimento",
        "macro": "Macro 100mm f/2.8 + extensores, ampliação 1:1 ou maior",
        "arquitetura": "Tilt-shift 24mm PC-E, correção de perspectiva vertical",
    }
    def process(self, briefing: str, domain: str) -> str:
        return self.DOMAIN_MAP.get(domain, "50mm f/1.8, perspectiva natural, óptica neutra")


class Agente07_Exposicao:
    """Agente 07 — Exposição: ISO, shutter speed, abertura."""
    DOMAIN_MAP = {
        "acao": "ISO 1600, 1/2000s, f/4 — congelamento de movimento rápido",
        "paisagem": "ISO 100, 1/125s, f/11 — máxima nitidez, grande profundidade",
        "retrato": "ISO 400, 1/200s, f/2.8 — exposição equilibrada, bokeh",
        "produto": "ISO 50, 1/60s, f/16 — exposição perfeita em estúdio",
        "noite": "ISO 3200, 1/30s, f/2.8 — cena noturna urbana, grain permitido",
    }
    def process(self, briefing: str, domain: str) -> str:
        text = briefing.lower()
        if "noite" in text or "noturno" in text or "night" in text:
            return self.DOMAIN_MAP["noite"]
        return self.DOMAIN_MAP.get(domain, "ISO 400, exposição equilibrada, sem overexposure")


class Agente08_Luz:
    """Agente 08 — Luz: tipo, direção, temperatura de cor."""
    LIGHT_KEYWORDS = {
        "golden hour": "luz dourada, magic hour, sol baixo 5000K, sombras longas suaves",
        "blue hour": "crepúsculo, luz azul-roxo 8000K, contraste baixo, atmosfera mágica",
        "studio": "luz de estúdio, softbox lateral, 5500K, sombras controladas",
        "natural": "luz natural difusa, janela lateral, 6500K, sombras suaves",
        "harsh": "luz dura direta, meio-dia, sombras definidas, alto contraste",
        "dramatic": "chiaroscuro, luz lateral extrema, 90% sombra, 3200K",
        "neon": "iluminação neon colorida, reflexos em superfícies úmidas, noite urbana",
    }
    def process(self, briefing: str, keywords: str) -> str:
        text = (briefing + " " + keywords).lower()
        for marker, value in self.LIGHT_KEYWORDS.items():
            if marker in text:
                return value
        return "luz natural, diffused, 5500K, sombras suaves, sem overexposure"


class Agente09_Cor:
    """Agente 09 — Cor: paleta, grading, LUT."""
    DOMAIN_MAP = {
        "cinema": "LUT cinematográfico desaturado, shadows levantados, teal-orange look",
        "retrato": "skin tones quentes naturais, shadows neutros, sem virar verde",
        "produto": "cores fiéis ao produto, perfil ICC sRGB, sem dominante de cor",
        "paisagem": "cores naturais vibrantes, céu azul sem poster, vegetação verde real",
        "documental": "paleta desaturada discreta, tons terra, sem grading artificial",
        "drama": "contraste alto, paleta fria, shadows azul-esverdeados, clima de tensão",
    }
    def process(self, briefing: str, domain: str) -> str:
        return self.DOMAIN_MAP.get(domain, "paleta natural equilibrada, sem dominante de cor, sRGB")


class Agente10_Sujeito:
    """Agente 10 — Sujeito: descrição detalhada do elemento principal."""
    def process(self, briefing: str) -> str:
        # Extrai o sujeito do briefing (simplificado: primeiras palavras relevantes)
        text = briefing.strip()
        if len(text) > 200:
            return text[:200] + "..."
        return text if text else "sujeito não especificado"


class Agente11_Materiais:
    """Agente 11 — Materiais: texturas, superfícies, propriedades físicas."""
    MATERIAL_KEYWORDS = {
        "metal": "metal polido, reflexos especulares precisos, microtexturas de usinagem",
        "pele": "pele humana com poros visíveis, subsurface scattering, oleosidade natural",
        "tecido": "fibras de tecido visíveis, deformação natural por gravidade, textura real",
        "madeira": "veios de madeira com profundidade, nós, variação de grão, verniz real",
        "vidro": "vidro com refrações, reflexos distorcidos, espessura física visível",
        "água": "água com ondas pequenas, reflexo do céu, transparência graduada",
        "pedra": "granito/mármore com cristais visíveis, superfície rugosa, microrelevo",
        "plastico": "plástico com especular suave, ABS fosco ou transparente injetado",
    }
    def process(self, briefing: str, keywords: str) -> str:
        text = (briefing + " " + keywords).lower()
        detected = []
        for material, desc in self.MATERIAL_KEYWORDS.items():
            if material in text:
                detected.append(desc)
        if detected:
            return "; ".join(detected[:3])
        return "materiais com propriedades físicas realistas, superfícies com microtexturas"


class Agente12_Ambiente:
    """Agente 12 — Ambiente: cenário, locação, contexto espacial."""
    LOCATION_KEYWORDS = {
        "urbano": "rua urbana com asfalto molhado, edifícios ao fundo desfocados",
        "floresta": "floresta densa, light rays entre árvores, solo com folhas",
        "praia": "praia com areia fina, espuma de onda, horizonte aquático",
        "deserto": "deserto com dunas, calor visível, grãos de areia voando",
        "interior": "interior doméstico, luz de janela, detalhes de ambiente real",
        "estudio": "fundo negro infinito de estúdio fotográfico ou backdrop branco",
        "montanha": "montanha com névoa, perspectiva aérea, altitude perceptível",
    }
    def process(self, briefing: str) -> str:
        text = briefing.lower()
        for loc, desc in self.LOCATION_KEYWORDS.items():
            if loc in text:
                return desc
        return "ambiente contextualmente coerente com o sujeito, profundidade de campo real"


class Agente13_Profundidade:
    """Agente 13 — Profundidade de campo: DoF, bokeh, foco seletivo."""
    DOMAIN_MAP = {
        "retrato": "bokeh cremoso f/1.4–2.0, fundo completamente desfocado, sujeito tack-sharp",
        "produto": "foco total f/11–16, tudo nítido, DoF máxima em estúdio",
        "paisagem": "hiperfocal, f/11, tudo nítido de primeiro plano ao horizonte",
        "macro": "DoF extremamente rasa, só um elemento foco, bokeh geométrico",
        "cinema": "DoF controlada, foco rack entre planos, movimento suave de foco",
    }
    def process(self, briefing: str, domain: str) -> str:
        return self.DOMAIN_MAP.get(domain, "profundidade de campo natural, foco no sujeito principal")


class Agente14_TexturaCaptura:
    """Agente 14 — Textura de captura: grain, noise, imperfeições de sensor."""
    DOMAIN_MAP = {
        "cinema": "grain de película 35mm, estrutura orgânica, não digital",
        "documental": "noise digital ISO 1600 natural, sem redução de ruído artificial",
        "produto": "imagem limpa, zero grain, redução de ruído máxima, nitidez cirúrgica",
        "retrato": "grain sutil ISO 400, textura de pele preservada, sem oversmoothing",
        "vintage": "grain pesado de película 800 ISO, vazamentos de luz ocasionais",
    }
    def process(self, briefing: str, domain: str) -> str:
        text = briefing.lower()
        if "vintage" in text or "analógico" in text or "film" in text:
            return self.DOMAIN_MAP["vintage"]
        return self.DOMAIN_MAP.get(domain, "textura de captura sutil e natural, grain orgânico")


class Agente15_Imperfeicoes:
    """Agente 15 — Imperfeições: aberrações cromáticas, vinheta, distorções."""
    DOMAIN_MAP = {
        "cinema": "vinheta sutil, aberração cromática mínima nas bordas, flare ocasional",
        "documental": "leve distorção de barrel, aberração cromática visível, sem correção",
        "produto": "zero imperfeições, correção total de distorção, perfil de câmera aplicado",
        "vintage": "aberração cromática intensa, vinheta forte, borrão de movimento nas bordas",
        "retrato": "vinheta sutil direcionando olhar, correção de distorção facial",
    }
    def process(self, briefing: str, domain: str) -> str:
        return self.DOMAIN_MAP.get(domain, "imperfeições óticas sutis e realistas, vinheta discreta")


class Agente16_Entropia:
    """Agente 16 — Entropia: ordem vs. caos visual, clutter."""
    def process(self, briefing: str, domain: str) -> str:
        text = briefing.lower()
        if "minimalista" in text or "clean" in text or "produto" in domain:
            return "cena minimalista, fundo limpo, elementos mínimos, entropia baixa"
        if "urbano" in text or "rua" in text or "mercado" in text:
            return "cena densa com elementos sobrepostos, entropia alta, realismo urbano"
        return "equilíbrio entre ordem e detalhe, elementos suficientes para contexto sem poluição"


class Agente17_MovimentoFisica:
    """Agente 17 — Movimento e Física: motion blur, gravidade, dinâmica."""
    def process(self, briefing: str) -> str:
        text = briefing.lower()
        if "correndo" in text or "velocidade" in text or "sport" in text:
            return "motion blur direcional no sujeito, fundo estático nítido, 1/500s efeito"
        if "água" in text or "water" in text:
            return "água com física real — gotas com tensão superficial, ondas coerentes"
        if "vento" in text or "wind" in text:
            return "vento nos cabelos e tecidos com deformação física coerente"
        if "explosão" in text or "fumaça" in text:
            return "partículas com física de fluido, pressão de onda, subsimulação real"
        return "física estática, sem motion blur desnecessário, elementos sólidos e coerentes"


class Agente18_Exclusoes:
    """Agente 18 — Exclusões: o que NÃO deve aparecer (negative prompt)."""
    # Exclusões universais de qualidade
    UNIVERSAL_NEGATIVES = [
        "watermark", "text overlay", "signature", "logo",
        "blur artificial", "overexposed highlights",
        "plastic skin", "uncanny valley face", "extra fingers",
        "deformed hands", "floating objects", "inconsistent lighting",
        "cartoon style", "anime", "illustration", "painting look",
        "low quality", "jpeg artifacts", "pixelated", "blurry",
    ]

    def process(self, briefing: str, keywords: str) -> str:
        exclusions = list(self.UNIVERSAL_NEGATIVES)

        text = (briefing + " " + keywords).lower()

        # Exclusões contextuais
        if "retrato" in text or "pessoa" in text:
            exclusions += ["extra limbs", "bad anatomy", "disfigured face", "cross-eyed"]
        if "produto" in text:
            exclusions += ["shadow on product", "color cast", "dirty surface"]
        if "natureza" in text or "paisagem" in text:
            exclusions += ["power lines", "trash", "people in background unintentionally"]
        if "arquitetura" in text:
            exclusions += ["perspective distortion", "converging verticals"]

        return ", ".join(exclusions[:25])
