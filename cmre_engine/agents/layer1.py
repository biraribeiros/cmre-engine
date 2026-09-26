"""
CMRE Engine — Camada 1: Análise de Briefing
Agente 01: IntentParser — extrai intenção e palavras-chave do briefing
Agente 02: SceneClassifier — classifica cena em domínios visuais ativos
"""


class IntentParser:
    """
    Agente 01 — IntentParser
    Recebe o briefing em linguagem natural e extrai:
    - intent: o que o usuário quer ver (substantivo + ação)
    - keywords: lista de termos-chave
    - style_hints: dicas de estilo percebidas
    - complexity: 'simples' | 'media' | 'complexa'
    """

    STYLE_KEYWORDS = {
        "cinema": ["cinematográfico", "cinema", "filme", "movie", "cinematic"],
        "documental": ["documental", "documentary", "jornalístico", "reportagem"],
        "comercial": ["produto", "embalagem", "pack shot", "e-commerce", "comercial"],
        "retrato": ["retrato", "portrait", "rosto", "pessoa", "modelo"],
        "paisagem": ["paisagem", "landscape", "natureza", "outdoor", "exterior"],
        "arquitetura": ["arquitetura", "prédio", "interiores", "interior design"],
        "macro": ["macro", "detalhe", "close-up", "textura"],
        "acao": ["ação", "movimento", "esporte", "sport", "dinâmico"],
    }

    def parse(self, briefing: str) -> dict:
        text = briefing.lower()
        words = text.split()

        # Detectar estilo predominante
        style_hints = []
        for style, markers in self.STYLE_KEYWORDS.items():
            if any(m in text for m in markers):
                style_hints.append(style)

        # Complexidade por número de elementos descritos
        complexity = "simples"
        if len(words) > 30:
            complexity = "media"
        if len(words) > 60 or len(style_hints) > 2:
            complexity = "complexa"

        # Palavras-chave (remover stopwords básicas)
        stopwords = {
            "uma", "um", "de", "do", "da", "com", "em", "para",
            "que", "e", "o", "a", "os", "as", "se", "no", "na",
            "ao", "pelo", "pela", "the", "a", "an", "of", "with",
        }
        keywords = [w for w in words if len(w) > 3 and w not in stopwords][:20]

        # Intent: primeiras 3 palavras significativas
        intent = " ".join(keywords[:3]) if keywords else briefing[:50]

        return {
            "intent": intent,
            "keywords": keywords,
            "style_hints": style_hints if style_hints else ["realismo"],
            "complexity": complexity,
            "briefing_length": len(words),
        }


class SceneClassifier:
    """
    Agente 02 — SceneClassifier
    Mapeia o briefing para os domínios CMRE ativos:
    quais dos 16 blocos técnicos são relevantes para esta cena.
    """

    # Mapeamento: domínio → blocos CMRE prioritários
    DOMAIN_BLOCKS = {
        "retrato": ["sujeito", "luz", "optica", "cor", "profundidade", "imperfeicoes"],
        "paisagem": ["ambiente", "luz", "cor", "entropia", "sensor_meio", "exposicao"],
        "produto": ["materiais", "luz", "cor", "enquadramento", "profundidade", "saida"],
        "acao": ["movimento_fisica", "exposicao", "enquadramento", "sensor_meio", "luz"],
        "arquitetura": ["ambiente", "enquadramento", "luz", "materiais", "optica"],
        "macro": ["optica", "profundidade", "textura_captura", "materiais", "luz"],
        "cinema": ["enquadramento", "luz", "cor", "sensor_meio", "movimento_fisica"],
        "documental": ["sensor_meio", "luz", "textura_captura", "imperfeicoes", "entropia"],
    }

    # Blocos sempre incluídos em qualquer cena
    ALWAYS_ACTIVE = ["saida", "sujeito", "exclusoes"]

    def classify(self, intent_data: dict) -> dict:
        style_hints = intent_data.get("style_hints", ["realismo"])

        active_blocks = set(self.ALWAYS_ACTIVE)
        domain_scores = {}

        for style in style_hints:
            if style in self.DOMAIN_BLOCKS:
                blocks = self.DOMAIN_BLOCKS[style]
                for b in blocks:
                    active_blocks.add(b)
                domain_scores[style] = 1.0

        # Se nenhum domínio reconhecido → ativa todos os blocos
        if not domain_scores:
            active_blocks = {
                "saida", "enquadramento", "sensor_meio", "optica",
                "exposicao", "luz", "cor", "sujeito", "materiais",
                "ambiente", "profundidade", "textura_captura",
                "imperfeicoes", "entropia", "movimento_fisica", "exclusoes"
            }
            domain_scores["geral"] = 0.8

        return {
            "active_blocks": sorted(list(active_blocks)),
            "domain_scores": domain_scores,
            "primary_domain": style_hints[0] if style_hints else "geral",
        }
