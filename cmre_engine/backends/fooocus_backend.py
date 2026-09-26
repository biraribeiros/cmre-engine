"""
CMRE Engine — Backend Fooocus
Conecta ao servidor Fooocus local via API HTTP.
Fooocus roda localmente com 4GB VRAM usando DirectML (AMD/Intel).

Setup:
1. Baixe Fooocus: https://github.com/lllyasviel/Fooocus
2. Execute: python entry_with_update.py --directml
3. Acesse: http://localhost:7865
"""
import os
import time
import base64
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class FooocusBackend:
    """
    Backend Fooocus — geração local sem CUDA, com DirectML.
    Requer Fooocus rodando em http://localhost:7865 (padrão).
    """

    def __init__(self, host: str = "http://localhost:7865", output_dir: str = "outputs"):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests não instalado. Execute: pip install requests")

        self.host = host.rstrip("/")
        self.api_url = f"{self.host}/v1/generation/text-to-image"
        self.output_dir = Path(output_dir) / "fooocus"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, negative: str = "") -> str:
        """
        Envia prompt para Fooocus local e salva a imagem retornada.

        Args:
            prompt: Prompt positivo CMRE
            negative: Prompt negativo consolidado

        Returns:
            Caminho da imagem salva
        """
        payload = {
            "prompt": prompt,
            "negative_prompt": negative,
            "performance_selection": "Speed",   # Quality | Speed | Extreme Speed
            "aspect_ratios_selection": "1152×896",
            "image_number": 1,
            "image_seed": -1,   # -1 = aleatório
            "sharpness": 2.0,
            "guidance_scale": 4.0,
            "base_model_name": "juggernautXL_v8Rundiffusion.safetensors",
            "async_process": False,
        }

        try:
            resp = requests.post(self.api_url, json=payload, timeout=300)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Fooocus não está rodando em {self.host}\n"
                "Inicie: python entry_with_update.py --directml"
            )
        except requests.exceptions.Timeout:
            raise RuntimeError("Fooocus demorou mais de 5 minutos — timeout")

        data = resp.json()

        # Fooocus retorna lista de imagens em base64
        if not data or not isinstance(data, list):
            raise RuntimeError(f"Resposta inesperada do Fooocus: {data}")

        image_b64 = data[0].get("base64", "")
        if not image_b64:
            raise RuntimeError("Fooocus não retornou dados de imagem")

        timestamp = int(time.time())
        filename = self.output_dir / f"cmre_{timestamp}.jpg"

        image_bytes = base64.b64decode(image_b64)
        with open(filename, "wb") as f:
            f.write(image_bytes)

        return str(filename.resolve())
