"""
CMRE Engine — Agente 00: Orquestrador Principal
Coordena todas as 5 camadas do motor de realismo visual.
"""
from .models import CCIReport
from .agents.layer1 import IntentParser, SceneClassifier
from .agents.layer2 import TechnicalBlockAgents
from .agents.layer3 import CrossDomainValidators
from .agents.layer4 import (
    CCICalculator, ConflictResolver, PromptSynthesizer,
    NegativePromptFinal, Executor
)
from .config import BACKEND, VERBOSE


class CMREOrchestrator:
    """
    Agente 00 — Orquestrador CMRE
    Motor de 30 agentes para geração de imagem ultra-realista.

    Arquitetura:
    L0: Orquestrador (este arquivo)
    L1: IntentParser + SceneClassifier        (Agentes 01–02)
    L2: 16 Especialistas em Blocos Técnicos  (Agentes 03–18)
    L3: 7 Validadores Cross-Domain           (Agentes 19–25)
    L4: CCICalc + Resolver + Synth + Exec    (Agentes 26–30)
    """

    def __init__(self):
        # L1
        self.intent_parser = IntentParser()
        self.scene_classifier = SceneClassifier()

        # L2
        self.technical_blocks = TechnicalBlockAgents()

        # L3
        self.validators = CrossDomainValidators()

        # L4
        self.cci_calculator = CCICalculator()
        self.conflict_resolver = ConflictResolver()
        self.prompt_synthesizer = PromptSynthesizer()
        self.negative_builder = NegativePromptFinal()
        self.executor = Executor()

        # Backend de geração (configurado em config.py)
        self.backend = BACKEND

    def run(self, briefing: str) -> CCIReport:
        """
        Processa um briefing em linguagem natural e gera uma imagem ultra-realista.

        Args:
            briefing: Descrição da imagem em linguagem natural (PT/EN)

        Returns:
            CCIReport com CCI score, prompt final, negative prompt e caminho da imagem
        """
        self._log(f"\n{'='*60}")
        self._log(f"🧠 CMRE Engine — Briefing recebido ({len(briefing)} chars)")
        self._log(f"{'='*60}")

        # ─── CAMADA 1: Análise de Briefing ────────────────────────────
        self._log("\n[L1] Analisando briefing...")
        intent_data = self.intent_parser.parse(briefing)
        classification = self.scene_classifier.classify(intent_data)

        self._log(f"     Intent: {intent_data['intent']}")
        self._log(f"     Domínio: {classification['primary_domain']}")
        self._log(f"     Blocos ativos: {len(classification['active_blocks'])}/16")

        # ─── CAMADA 2: Especialistas Técnicos ─────────────────────────
        self._log("\n[L2] Processando 16 blocos técnicos...")
        blocks = self.technical_blocks.process(briefing, intent_data, classification)
        self._log("     ✅ Ficha técnica CMRE preenchida")

        # ─── CAMADA 3: Validadores Cross-Domain ───────────────────────
        self._log("\n[L3] Executando 7 validadores cross-domain...")
        validations = self.validators.validate_all(blocks)

        failed = [v for v in validations if not v.passed]
        self._log(f"     Conflitos detectados: {len(failed)}")
        for v in failed:
            self._log(f"     ⚠️  {v.pair}: {', '.join(v.conflicts)}")

        # ─── CAMADA 4: Síntese e Execução ─────────────────────────────
        self._log("\n[L4] Calculando CCI e sintetizando prompt...")

        # 4.1: Calcular CCI antes da resolução
        cci_bruto = self.cci_calculator.calculate(validations)

        # 4.2: Resolver conflitos automaticamente
        blocks, resolved = self.conflict_resolver.resolve(blocks, validations)
        if resolved:
            self._log(f"     🔧 Conflitos resolvidos: {len(resolved)}")
            for r in resolved:
                self._log(f"        {r}")

        # 4.3: Recalcular CCI pós-resolução
        if resolved:
            validations_final = self.validators.validate_all(blocks)
            cci_final = self.cci_calculator.calculate(validations_final)
        else:
            validations_final = validations
            cci_final = cci_bruto

        self._log(f"     CCI: {cci_bruto:.3f} → {cci_final:.3f}")

        # 4.4: Construir prompts
        prompt_final = self.prompt_synthesizer.synthesize(blocks, cci_final)
        negative_final = self.negative_builder.build(blocks.exclusoes)

        # 4.5: Executar geração
        report = self.executor.execute(
            prompt=prompt_final,
            negative=negative_final,
            backend=self.backend,
            briefing=briefing,
            cci=cci_final,
            validations=validations_final,
            blocks=blocks,
        )

        self._log(f"\n{'='*60}")
        self._log(f"🏁 {report.summary()}")
        self._log(f"{'='*60}\n")

        return report

    def _log(self, msg: str):
        if VERBOSE:
            print(msg)
