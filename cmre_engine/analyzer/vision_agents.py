"""
CMRE Engine — Agentes de Visão (Lado A)
Espelham os agentes L2, mas em vez de *escrever* blocos a partir de um briefing,
*leem* blocos a partir de uma imagem real usando Gemini multimodal.

Cada agente recebe a imagem codificada em base64 + instrução de extração,
e retorna o valor preenchido para seu bloco técnico.

Todos os 16 agentes compartilham a mesma interface:
    extract(image_b64: str, mime_type: str) -> str
"""
import os
import json
import re


def _gemini_vision_call(image_b64: str, mime_type: str, prompt: str) -> str:
    """
    Chama Gemini com a imagem e retorna a resposta em texto.
    Usa a mesma chave de API configurada no backend Gemini existente.
    """
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não configurada")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            os.getenv("CMRE_VISION_MODEL", "gemini-2.0-flash-exp")
        )

        import base64
        image_bytes = base64.b64decode(image_b64)

        import PIL.Image
        import io
        img = PIL.Image.open(io.BytesIO(image_bytes))

        response = model.generate_content(
            [prompt, img],
            generation_config={"temperature": 0.2, "max_output_tokens": 256},
        )
        return response.text.strip()

    except Exception as e:
        return f"[erro: {e}]"


# ─── Bloco 1: Saída ───────────────────────────────────────────────────────────

class VisionAgent01_Saida:
    """Extrai resolução, aspect ratio e formato inferidos da imagem."""

    def extract(self, image_b64: str, mime_type: str, image_width: int = 0, image_height: int = 0) -> str:
        if image_width and image_height:
            ratio = image_width / image_height
            if abs(ratio - 16/9) < 0.05:
                aspect = "16:9"
            elif abs(ratio - 4/3) < 0.05:
                aspect = "4:3"
            elif abs(ratio - 1) < 0.05:
                aspect = "1:1"
            elif abs(ratio - 3/2) < 0.05:
                aspect = "3:2"
            else:
                aspect = f"{image_width}:{image_height}"
            return f"{image_width}x{image_height}px, aspect {aspect}, JPEG/PNG fotográfico"
        return "resolução não determinada"


# ─── Bloco 2: Enquadramento ───────────────────────────────────────────────────

class VisionAgent02_Enquadramento:
    """Identifica plano, ângulo e composição da foto."""

    PROMPT = """Analise esta fotografia e descreva de forma técnica e concisa:
- Plano da câmera (close-up extremo, close-up, plano médio, plano americano, plano geral, plano detalhe)
- Ângulo da câmera (eye level, high angle, low angle, bird's eye, dutch angle)
- Composição (regra dos terços, simetria, diagonal, quadro dentro do quadro, etc.)

Responda em UMA linha descritiva, sem bullet points. Exemplo:
"Plano médio, eye level, composição em regra dos terços, sujeito à direita"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 3: Sensor/Meio ─────────────────────────────────────────────────────

class VisionAgent03_SensorMeio:
    """Identifica ou infere a câmera/sensor que capturou a foto."""

    PROMPT = """Analise esta fotografia e infira o tipo de câmera/sensor mais provável:
- Câmera profissional full-frame (35mm), APS-C, médio formato, smartphone, etc.
- Se houver grain visível, descreva como analógico vs. digital
- Mencione se parece ser fotografia de estúdio ou externa

Responda em UMA linha. Exemplo:
"Câmera DSLR full-frame, sensor digital, 45MP estimado, captura em estúdio"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 4: Óptica ──────────────────────────────────────────────────────────

class VisionAgent04_Optica:
    """Infere a lente/focal usada a partir do campo de visão e distorção."""

    PROMPT = """Analise esta fotografia e infira a lente utilizada:
- Distância focal estimada (16mm grande-angular, 35mm, 50mm, 85mm, 135mm, 200mm+)
- Abertura estimada pelo bokeh ou profundidade de campo (f/1.4, f/2.8, f/8, etc.)
- Tipo de lente (prime, zoom, macro, olho de peixe, tele)
- Distorção visível (barril, almofada, nenhuma)

Responda em UMA linha. Exemplo:
"85mm prime, f/1.8 estimado por bokeh pronunciado, distorção mínima"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 5: Exposição ───────────────────────────────────────────────────────

class VisionAgent05_Exposicao:
    """Infere ISO, shutter e abertura a partir de ruído, motion blur e DoF."""

    PROMPT = """Analise esta fotografia e infira os parâmetros de exposição:
- ISO estimado (baixo ISO = imagem limpa, alto ISO = grain digital)
- Shutter speed inferida (rápido = movimento congelado, lento = motion blur)
- Abertura inferida (rasa = bokeh, fechada = tudo em foco)
- Qualidade de exposição (subexposta, bem exposta, superexposta, HDR)

Responda em UMA linha técnica. Exemplo:
"ISO 400, 1/250s (movimento congelado), f/4.0, exposição bem balanceada"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 6: Luz ─────────────────────────────────────────────────────────────

class VisionAgent06_Luz:
    """Analisa iluminação: tipo, direção, temperatura e qualidade."""

    PROMPT = """Analise a iluminação desta fotografia com precisão técnica:
- Tipo de luz (natural, estúdio, neon, mista, ambiente)
- Direção principal (frontal, lateral esquerda/direita, contraluz, rembrandt, loop)
- Temperatura de cor estimada em Kelvin (3200K quente, 5500K neutro, 6500K frio)
- Qualidade (dura/direta, suave/difusa, rebatida, fill light visível)
- Luzes secundárias ou rim light

Responda em UMA linha técnica. Exemplo:
"Luz natural difusa, lateral direita, 5500K, suave, rim light azul-frio à esquerda"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 7: Cor ─────────────────────────────────────────────────────────────

class VisionAgent07_Cor:
    """Analisa paleta de cor, grading e dominante cromática."""

    PROMPT = """Analise a cor e o grading desta fotografia:
- Paleta dominante (tons quentes, frios, neutros, complementares, análogos)
- Saturação geral (dessaturado, neutro, vibrante, hipersaturado)
- Estilo de grading visível (teal & orange, matte, vintage, clean, cinemático)
- Dominante cromática nas sombras e nos altos-luzes
- Temperatura geral percebida

Responda em UMA linha técnica. Exemplo:
"Paleta quente âmbar, saturação moderada, grading teal-orange suave, sombras azuladas"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 8: Sujeito ─────────────────────────────────────────────────────────

class VisionAgent08_Sujeito:
    """Descreve o sujeito principal com precisão fotográfica."""

    PROMPT = """Descreva o sujeito principal desta fotografia de forma técnica e objetiva:
- O que é o sujeito (pessoa, grupo, objeto, animal, paisagem, produto)
- Características visíveis (gênero aparente, faixa etária, roupas, postura, expressão)
- Posição no quadro e relação com o fundo
- Ação ou estado (estático, em movimento, olhando para câmera, de costas)

Mantenha descrição neutra e técnica, sem julgamentos.
Responda em UMA linha. Exemplo:
"Mulher adulta, cabelo escuro, vestido vermelho, postura relaxada, olhando câmera, centralizada"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 9: Materiais ───────────────────────────────────────────────────────

class VisionAgent09_Materiais:
    """Identifica materiais, texturas e propriedades de superfície."""

    PROMPT = """Identifique os principais materiais e texturas visíveis nesta fotografia:
- Tipo de superfície do sujeito (pele, tecido, metal, madeira, vidro, couro, etc.)
- Propriedades ópticas (mate, brilhante, translúcido, reflexivo, rugoso, suave)
- Subsurface scattering visível em pele ou materiais translúcidos
- Reflexos ambientais em superfícies polidas

Responda em UMA linha técnica. Exemplo:
"Pele com subsurface scattering natural, tecido de seda reflexivo, fundo de madeira rústica mate"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 10: Ambiente ───────────────────────────────────────────────────────

class VisionAgent10_Ambiente:
    """Descreve o cenário e contexto espacial da cena."""

    PROMPT = """Analise o cenário/ambiente desta fotografia:
- Tipo de ambiente (interior, exterior, estúdio, urbano, natural, industrial)
- Localização inferida (escritório, café, rua, floresta, praia, estúdio, etc.)
- Época do dia (manhã, tarde, entardecer, noite)
- Condições climáticas se exterior (sol, nublado, chuva, neve, neblina)
- Distância e relação com o fundo

Responda em UMA linha técnica. Exemplo:
"Interior de café, iluminação ambiente quente, tarde, fundo desfocado com elementos de madeira"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 11: Profundidade de Campo ─────────────────────────────────────────

class VisionAgent11_Profundidade:
    """Analisa profundidade de campo, bokeh e plano de foco."""

    PROMPT = """Analise a profundidade de campo e foco desta fotografia:
- Profundidade de campo (rasa, moderada, profunda)
- Qualidade do bokeh se presente (circular, cremoso, nervoso, hexagonal)
- Ponto focal principal (o quê está em foco)
- Separação sujeito/fundo (forte, moderada, ausente)
- Uso de foco seletivo intencional

Responda em UMA linha técnica. Exemplo:
"DoF rasa, bokeh cremoso circular, foco nos olhos, forte separação fundo desfocado"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 12: Textura de Captura ────────────────────────────────────────────

class VisionAgent12_TexturaCaptura:
    """Analisa grain, noise e imperfeições de sensor."""

    PROMPT = """Analise a textura de captura desta fotografia:
- Grain visível (ausente, sutil, moderado, forte)
- Tipo de ruído se presente (luminância, crominância, ambos)
- Parece analógico (filme 35mm) ou digital?
- Nível de sharpening aplicado (nenhum, suave, excessivo)
- Aliasing ou moiré visíveis?

Responda em UMA linha técnica. Exemplo:
"Grain digital sutil de luminância, aparência digital moderna, sharpening suave bem aplicado"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 13: Imperfeições Ópticas ──────────────────────────────────────────

class VisionAgent13_Imperfeicoes:
    """Detecta aberrações cromáticas, vignette e distorções."""

    PROMPT = """Identifique imperfeições ópticas reais nesta fotografia:
- Aberração cromática (franja roxa/verde nas bordas de alto contraste?)
- Vignette (escurecimento nos cantos, natural ou artificial?)
- Distorção (barril, almofada, perspectiva)
- Flare ou ghosting de lente
- Lens breathing ou focus shift visíveis

Responda em UMA linha técnica. Exemplo:
"Vignette natural sutil, leve aberração cromática nas bordas, sem distorção visível"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 14: Entropia ───────────────────────────────────────────────────────

class VisionAgent14_Entropia:
    """Avalia o nível de ordem vs. caos visual (clutter/entropia)."""

    PROMPT = """Avalie o nível de complexidade visual (entropia) desta fotografia:
- Quantidade de elementos visuais (minimalista, moderado, denso, caótico)
- Organização do cenário (limpo e ordenado, casual, desordenado, caótico)
- Fundo (neutro/limpo, texturizado, complexo, poluído)
- Ruído informacional (quantos elementos competem pela atenção)

Responda em UMA linha com nível de entropia e descrição. Exemplo:
"Baixa entropia, fundo neutro limpo, sujeito isolado, composição minimalista intencional"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 15: Movimento/Física ───────────────────────────────────────────────

class VisionAgent15_MovimentoFisica:
    """Detecta motion blur, dinâmica e física da cena."""

    PROMPT = """Analise movimento e física desta fotografia:
- Motion blur presente? (sujeito, fundo, nenhum)
- Movimento congelado (shutter rápido) ou registrado (lento)?
- Física plausível dos elementos (gravidade, postura, fluidos, cabelo, roupas)
- Captura de momento decisivo ou pose estática
- Panning intencional do fotógrafo?

Responda em UMA linha técnica. Exemplo:
"Sem motion blur, movimento congelado, física plausível, pose estática natural"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Bloco 16: Exclusões/Negativos ───────────────────────────────────────────

class VisionAgent16_Exclusoes:
    """
    Infere o que está AUSENTE na foto, gerando um negative prompt útil.
    Baseado no que a foto *evitou* com sucesso.
    """

    PROMPT = """Analise o que foi EVITADO com sucesso nesta fotografia de alta qualidade.
Liste elementos indesejáveis que NÃO estão presentes:
- Problemas de qualidade ausentes (não há grain excessivo, não há borrado desnecessário)
- Elementos visuais poluentes ausentes (sem texto, sem marcas d'água)
- Problemas técnicos ausentes (sem superexposição, sem anatomia incorreta, etc.)
- Outros elementos que degradariam a foto se estivessem presentes

Responda como lista de negativos separados por vírgula. Exemplo:
"grain excessivo, overexposure, watermark, bad anatomy, distortion, noise"
"""

    def extract(self, image_b64: str, mime_type: str, **_) -> str:
        return _gemini_vision_call(image_b64, mime_type, self.PROMPT)


# ─── Coordenador ──────────────────────────────────────────────────────────────

class VisionBlockExtractor:
    """
    Coordena os 16 agentes de visão para extrair todos os blocos
    técnicos de uma fotografia real em uma única passagem.

    Para economizar chamadas de API, agrupa blocos em chamadas combinadas.
    """

    def __init__(self):
        self.agents = {
            "saida":            VisionAgent01_Saida(),
            "enquadramento":    VisionAgent02_Enquadramento(),
            "sensor_meio":      VisionAgent03_SensorMeio(),
            "optica":           VisionAgent04_Optica(),
            "exposicao":        VisionAgent05_Exposicao(),
            "luz":              VisionAgent06_Luz(),
            "cor":              VisionAgent07_Cor(),
            "sujeito":          VisionAgent08_Sujeito(),
            "materiais":        VisionAgent09_Materiais(),
            "ambiente":         VisionAgent10_Ambiente(),
            "profundidade":     VisionAgent11_Profundidade(),
            "textura_captura":  VisionAgent12_TexturaCaptura(),
            "imperfeicoes":     VisionAgent13_Imperfeicoes(),
            "entropia":         VisionAgent14_Entropia(),
            "movimento_fisica": VisionAgent15_MovimentoFisica(),
            "exclusoes":        VisionAgent16_Exclusoes(),
        }

    def extract_all_blocks(
        self,
        image_b64: str,
        mime_type: str,
        image_width: int = 0,
        image_height: int = 0,
        verbose: bool = False,
    ) -> dict:
        """
        Extrai todos os 16 blocos técnicos da imagem.
        Retorna dicionário {nome_bloco: valor_string}.
        """
        # Usamos uma única chamada multi-bloco para economizar API calls
        result = self._extract_multi_block(image_b64, mime_type)

        # Bloco 1 (saida) é calculado localmente via dimensões
        result["saida"] = self.agents["saida"].extract(
            image_b64, mime_type,
            image_width=image_width, image_height=image_height
        )

        if verbose:
            for k, v in result.items():
                print(f"     [{k}] {v[:80]}...")

        return result

    def _extract_multi_block(self, image_b64: str, mime_type: str) -> dict:
        """
        Chama Gemini uma única vez pedindo todos os 15 blocos de análise.
        Retorna dicionário com os blocos preenchidos.
        """
        prompt = """Você é um sistema de análise fotográfica técnica (CMRE Engine).
Analise esta fotografia e extraia os valores para cada bloco técnico abaixo.
Seja CONCISO (máx. 1 linha por bloco) e TÉCNICO.

Responda APENAS no formato JSON abaixo, sem texto adicional:

{
  "enquadramento": "plano, ângulo, composição em uma linha",
  "sensor_meio": "câmera/sensor inferido em uma linha",
  "optica": "focal, abertura, tipo de lente em uma linha",
  "exposicao": "ISO, shutter, abertura, qualidade em uma linha",
  "luz": "tipo, direção, temperatura Kelvin, qualidade em uma linha",
  "cor": "paleta, saturação, grading, dominante em uma linha",
  "sujeito": "descrição objetiva do sujeito em uma linha",
  "materiais": "materiais, texturas, propriedades em uma linha",
  "ambiente": "cenário, localização, horário, clima em uma linha",
  "profundidade": "DoF, bokeh, ponto focal em uma linha",
  "textura_captura": "grain, noise, sharpening em uma linha",
  "imperfeicoes": "aberrações, vignette, distorções em uma linha",
  "entropia": "nível de complexidade visual em uma linha",
  "movimento_fisica": "motion blur, física, dinâmica em uma linha",
  "exclusoes": "lista de negativos separados por vírgula"
}"""

        raw = _gemini_vision_call(image_b64, mime_type, prompt)

        # Tenta parsear o JSON da resposta
        try:
            # Remove possíveis blocos de código markdown
            clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
            data = json.loads(clean)
            return {k: str(v) for k, v in data.items()}
        except (json.JSONDecodeError, ValueError):
            # Fallback: retorna dicionário com o raw para cada bloco
            return {key: raw[:120] for key in [
                "enquadramento", "sensor_meio", "optica", "exposicao",
                "luz", "cor", "sujeito", "materiais", "ambiente",
                "profundidade", "textura_captura", "imperfeicoes",
                "entropia", "movimento_fisica", "exclusoes",
            ]}
