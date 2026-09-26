"""
CMRE Engine — PhotoAnalyzer (Lado A)
Orquestra a análise completa de uma fotografia real:

  Foto real → Visão (16 blocos) → L3 Validadores → CCI → Banco de referências

Equivalente do CMREOrchestrator para o Lado A, mas em vez de gerar
imagens, lê e cataloga fotografias reais existentes.
"""
import base64
import os
from pathlib import Path

from ..models import TechnicalBlocks, PhotoAnalysisReport, ReferenceEntry
from ..agents.layer3 import CrossDomainValidators
from ..agents.layer4 import CCICalculator
from ..reference.database import ReferenceDatabase
from ..config import VERBOSE
from .vision_agents import VisionBlockExtractor


# Mapeia gênero de cena a partir das palavras-chave detectadas no sujeito/ambiente
_GENRE_KEYWORDS = {
    "retrato":  ["pessoa", "mulher", "homem", "criança", "rosto", "retrato", "portrait",
                 "adult", "woman", "man", "child", "face", "sujeito humano"],
    "produto":  ["produto", "product", "garrafa", "embalagem", "objeto isolado",
                 "still life", "bottle", "package", "item"],
    "paisagem": ["paisagem", "landscape", "floresta", "montanha", "praia", "céu",
                 "campo", "natureza", "exterior", "outdoor"],
    "urbano":   ["cidade", "rua", "urbano", "prédio", "edifício", "urban", "street",
                 "building", "city", "arquitetura"],
    "moda":     ["moda", "fashion", "editorial", "modelo", "roupa", "vestuário"],
    "esporte":  ["esporte", "sport", "atleta", "ação", "movimento", "corrida"],
    "alimento": ["alimento", "comida", "food", "prato", "bebida", "culinário"],
    "animal":   ["animal", "cachorro", "gato", "pássaro", "fauna", "wildlife"],
    "arquitetura": ["arquitetura", "interiores", "interior design", "cômodo",
                    "sala", "quarto", "escritório"],
}


def _classify_genre(blocks: TechnicalBlocks) -> str:
    """Infere o gênero da cena a partir dos blocos extraídos."""
    text = (blocks.sujeito + " " + blocks.ambiente + " " + blocks.enquadramento).lower()
    scores = {genre: 0 for genre in _GENRE_KEYWORDS}
    for genre, keywords in _GENRE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[genre] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "geral"


class PhotoAnalyzer:
    """
    Agente de análise de fotos reais (Lado A).

    Uso:
        analyzer = PhotoAnalyzer()
        report = analyzer.analyze("minha_foto.jpg")
        print(report.summary())
        # CCI Real: 0.87 | Gênero: retrato | Foto: minha_foto.jpg
    """

    def __init__(self, db: ReferenceDatabase | None = None):
        self.vision_extractor = VisionBlockExtractor()
        self.validators = CrossDomainValidators()
        self.cci_calculator = CCICalculator()
        self.db = db  # Opcional: se fornecido, salva automaticamente

    def analyze(
        self,
        image_path: str,
        save_to_db: bool = True,
        metadata: dict | None = None,
    ) -> PhotoAnalysisReport:
        """
        Analisa uma fotografia real e retorna um PhotoAnalysisReport.

        Args:
            image_path: Caminho para a imagem (JPG, PNG, WebP)
            save_to_db: Se True e db foi fornecido no construtor, salva no banco
            metadata: Dados extras opcionais (câmera, fotógrafo, notas)

        Returns:
            PhotoAnalysisReport com blocos extraídos, CCI e gênero
        """
        self._log(f"\n{'='*60}")
        self._log(f"🔍 CMRE Analyzer — Analisando foto: {image_path}")
        self._log(f"{'='*60}")

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

        # ─── 1. Carregar imagem ───────────────────────────────────────────────
        self._log("\n[A1] Carregando imagem...")
        image_b64, mime_type, width, height = self._load_image(path)
        image_hash = ReferenceDatabase.hash_image(image_path)
        self._log(f"     {width}x{height}px | {mime_type} | hash: {image_hash[:16]}...")

        # ─── 2. Verificar cache no banco ──────────────────────────────────────
        if self.db:
            cached = self.db.get_by_hash(image_hash)
            if cached:
                self._log(f"     ♻️  Cache hit! CCI={cached.cci_score:.2f} ({cached.scene_genre})")
                return PhotoAnalysisReport(
                    image_path=image_path,
                    cci_score=cached.cci_score,
                    blocks=cached.blocks,
                    validations=[],
                    scene_genre=cached.scene_genre,
                    metadata=cached.metadata,
                    image_hash=image_hash,
                )

        # ─── 3. Extrair 16 blocos com agentes de visão ───────────────────────
        self._log("\n[A2] Extraindo 16 blocos técnicos via visão multimodal...")
        raw_blocks = self.vision_extractor.extract_all_blocks(
            image_b64, mime_type,
            image_width=width, image_height=height,
            verbose=VERBOSE,
        )
        blocks = TechnicalBlocks(**{k: v for k, v in raw_blocks.items()
                                    if k in TechnicalBlocks.__dataclass_fields__})
        self._log("     ✅ Ficha técnica extraída da foto real")

        # ─── 4. Classificar gênero ────────────────────────────────────────────
        scene_genre = _classify_genre(blocks)
        self._log(f"\n[A3] Gênero de cena: {scene_genre}")

        # ─── 5. Validadores L3 ────────────────────────────────────────────────
        self._log("\n[A4] Executando 7 validadores cross-domain na foto real...")
        validations = self.validators.validate_all(blocks)
        failed = [v for v in validations if not v.passed]
        self._log(f"     Inconsistências detectadas: {len(failed)}")
        for v in failed:
            self._log(f"     ⚠️  {v.pair}: score={v.score:.2f}")

        # ─── 6. Calcular CCI da foto real ─────────────────────────────────────
        cci_real = self.cci_calculator.calculate(validations)
        self._log(f"\n[A5] CCI real: {cci_real:.3f}")

        # ─── 7. Montar relatório ──────────────────────────────────────────────
        report = PhotoAnalysisReport(
            image_path=image_path,
            cci_score=cci_real,
            blocks=blocks,
            validations=validations,
            scene_genre=scene_genre,
            metadata=metadata or {},
            image_hash=image_hash,
        )

        # ─── 8. Salvar no banco ───────────────────────────────────────────────
        if save_to_db and self.db:
            validator_scores = {v.pair: v.score for v in validations}
            entry = ReferenceEntry(
                image_path=image_path,
                image_hash=image_hash,
                scene_genre=scene_genre,
                blocks=blocks,
                cci_score=cci_real,
                validator_scores=validator_scores,
                metadata=metadata or {},
            )
            entry_id = self.db.save(entry)
            self._log(f"\n[A6] 💾 Referência salva no banco (id={entry_id})")

        self._log(f"\n{'='*60}")
        self._log(f"🏁 {report.summary()}")
        self._log(f"{'='*60}\n")

        return report

    def analyze_batch(
        self,
        image_paths: list[str],
        save_to_db: bool = True,
    ) -> list[PhotoAnalysisReport]:
        """
        Analisa múltiplas fotos em sequência.
        Útil para popular o banco de referências em lote.
        """
        reports = []
        for i, path in enumerate(image_paths, 1):
            self._log(f"\n📷 [{i}/{len(image_paths)}] {path}")
            try:
                report = self.analyze(path, save_to_db=save_to_db)
                reports.append(report)
            except Exception as e:
                self._log(f"❌ Erro em {path}: {e}")
        return reports

    def _load_image(self, path: Path) -> tuple[str, str, int, int]:
        """
        Carrega uma imagem e retorna (base64, mime_type, width, height).
        """
        suffix = path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(suffix, "image/jpeg")

        with open(path, "rb") as f:
            raw_bytes = f.read()

        image_b64 = base64.b64encode(raw_bytes).decode("utf-8")

        # Tentar obter dimensões sem dependência externa
        width, height = 0, 0
        try:
            import PIL.Image
            import io
            with PIL.Image.open(io.BytesIO(raw_bytes)) as img:
                width, height = img.size
        except ImportError:
            pass  # PIL não disponível, dimensões ficam 0

        return image_b64, mime_type, width, height

    def _log(self, msg: str):
        if VERBOSE:
            print(msg)
