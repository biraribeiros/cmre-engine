"""
CMRE Engine — Backend Gemini
Usa google-genai SDK para gerar imagens via Gemini 2.5 Flash Image.
Gratuito: 500 imagens/dia via Google AI Studio.
"""
import os
import time
from pathlib import Path

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiBackend:
    """
    Backend Gemini — Agente de execução via API gratuita Google AI Studio.

    Setup:
    1. Acesse https://aistudio.google.com/apikey
    2. Crie uma API Key gratuita (sem cartão de crédito)
    3. Adicione ao .env: GEMINI_API_KEY=sua_chave_aqui
    """

    MODEL = "gemini-2.5-flash-preview-image-generation"

    def __init__(self, output_dir: str = "outputs"):
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai não instalado. Execute: pip install google-genai"
            )

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY não encontrada.\n"
                "1. Acesse https://aistudio.google.com/apikey\n"
                "2. Adicione ao .env: GEMINI_API_KEY=sua_chave"
            )

        self.client = genai.Client(api_key=api_key)
        self.output_dir = Path(output_dir) / "gemini"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, negative: str = "") -> str:
        """
        Gera uma imagem e salva em outputs/gemini/.

        Args:
            prompt: Prompt positivo (construído pelo PromptSynthesizer)
            negative: Prompt negativo (do NegativePromptFinal)

        Returns:
            Caminho absoluto da imagem gerada (str)
        """
        # Gemini não tem campo de negative separado — incluímos no prompt
        full_prompt = prompt
        if negative:
            full_prompt += f"\n\nAbsolutely avoid: {negative}"

        response = self.client.models.generate_images(
            model=self.MODEL,
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9",   # Padrão; o Agente 03 pode sobrescrever
            ),
        )

        if not response.generated_images:
            raise RuntimeError("Gemini não retornou nenhuma imagem")

        # Salvar imagem com timestamp
        timestamp = int(time.time())
        filename = self.output_dir / f"cmre_{timestamp}.jpg"

        image_data = response.generated_images[0].image.image_bytes
        with open(filename, "wb") as f:
            f.write(image_data)

        return str(filename.resolve())
