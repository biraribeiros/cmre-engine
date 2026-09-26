"""
CMRE Engine — Backend DALL-E 3 (OpenAI)
Usa openai SDK para gerar imagens via DALL-E 3.
Pago — ~$0.04 por imagem 1024×1024.
"""
import os
import time
from pathlib import Path

try:
    import openai
    import requests
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class DalleBackend:
    """
    Backend DALL-E 3 — alta qualidade, pago.
    Configure OPENAI_API_KEY no .env.
    """

    MODEL = "dall-e-3"
    SIZE = "1792x1024"   # Widescreen — melhor para conteúdo editorial

    def __init__(self, output_dir: str = "outputs"):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai não instalado. Execute: pip install openai")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não encontrada no .env")

        self.client = openai.OpenAI(api_key=api_key)
        self.output_dir = Path(output_dir) / "dalle"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, negative: str = "") -> str:
        """
        DALL-E não suporta negative prompts nativamente.
        O negative é incorporado ao prompt como instrução.
        """
        # DALL-E tem limite de 4000 chars — trunca se necessário
        full_prompt = prompt
        if negative:
            avoid_note = f" Avoid: {negative[:300]}"
            if len(full_prompt) + len(avoid_note) <= 4000:
                full_prompt += avoid_note

        if len(full_prompt) > 4000:
            full_prompt = full_prompt[:3997] + "..."

        response = self.client.images.generate(
            model=self.MODEL,
            prompt=full_prompt,
            size=self.SIZE,
            quality="hd",
            n=1,
        )

        image_url = response.data[0].url
        if not image_url:
            raise RuntimeError("DALL-E não retornou URL de imagem")

        # Baixar imagem da URL temporária
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()

        timestamp = int(time.time())
        filename = self.output_dir / f"cmre_{timestamp}.jpg"
        with open(filename, "wb") as f:
            f.write(img_response.content)

        return str(filename.resolve())
