"""
CMRE Engine — Configuração e seleção de backend.

Para trocar de backend, altere BACKEND_NAME:
  "gemini"  → Google Gemini API (recomendado, gratuito)
  "fooocus" → Fooocus local (offline, DirectML)
  "dalle"   → OpenAI DALL-E 3 (pago)
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Configuração Global ──────────────────────────────────────────────────────

# Backend ativo: "gemini" | "fooocus" | "dalle"
BACKEND_NAME = os.getenv("CMRE_BACKEND", "gemini")

# Modo verbose: exibe logs detalhados de cada camada
VERBOSE = os.getenv("CMRE_VERBOSE", "true").lower() == "true"

# Diretório de saída das imagens geradas
OUTPUT_DIR = os.getenv("CMRE_OUTPUT_DIR", "outputs")

# ─── Configuração do Lado A (Análise de Fotos Reais) ─────────────────────────

# Modelo de visão para extrair blocos técnicos de fotos reais
# Precisa suportar multimodal (imagem + texto). Default: Gemini 2.0 Flash Exp
VISION_MODEL = os.getenv("CMRE_VISION_MODEL", "gemini-2.0-flash-exp")

# Caminho do banco SQLite de referências (criado automaticamente)
REFERENCE_DB_PATH = os.getenv("CMRE_REFERENCE_DB", "outputs/reference.db")

# CCI mínimo para uma referência ser usada como âncora na geração (Lado B)
REFERENCE_MIN_CCI = float(os.getenv("CMRE_REFERENCE_MIN_CCI", "0.70"))

# Número de referências similares consultadas antes de gerar (Lado B)
REFERENCE_TOP_K = int(os.getenv("CMRE_REFERENCE_TOP_K", "3"))

# ─── Inicialização do Backend ─────────────────────────────────────────────────

def _load_backend():
    if BACKEND_NAME == "gemini":
        from .backends.gemini_backend import GeminiBackend
        return GeminiBackend(output_dir=OUTPUT_DIR)

    elif BACKEND_NAME == "fooocus":
        from .backends.fooocus_backend import FooocusBackend
        host = os.getenv("FOOOCUS_HOST", "http://localhost:7865")
        return FooocusBackend(host=host, output_dir=OUTPUT_DIR)

    elif BACKEND_NAME == "dalle":
        from .backends.dalle_backend import DalleBackend
        return DalleBackend(output_dir=OUTPUT_DIR)

    else:
        raise ValueError(
            f"Backend '{BACKEND_NAME}' não reconhecido. "
            "Use: gemini | fooocus | dalle"
        )


# Backend singleton — carregado uma vez no import
try:
    BACKEND = _load_backend()
except Exception as e:
    print(f"⚠️  Backend '{BACKEND_NAME}' não pôde ser carregado: {e}")
    print("   Configure a variável CMRE_BACKEND e as credenciais no .env")
    BACKEND = None
