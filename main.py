"""
CMRE Engine — Ponto de entrada principal.

Comandos disponíveis:
  python main.py                        → menu interativo (geração)
  python main.py "briefing..."          → gera imagem do briefing (Lado B)
  python main.py analyze foto.jpg       → analisa foto real (Lado A)
  python main.py analyze foto1.jpg foto2.jpg ...  → lote de fotos
  python main.py stats                  → estatísticas do banco de referências
  python main.py compare foto.jpg "briefing"      → compara foto vs geração

  ── Sistema de Aprendizado Contínuo ──
  python main.py harvest                → coleta diária de fotos (Pexels/Unsplash)
  python main.py harvest <genre> ...    → coleta apenas os gêneros especificados
  python main.py harvest-status         → status das coletas anteriores
  python main.py feedback               → avaliação interativa da última imagem
  python main.py train                  → treina/atualiza rede neural + pesos CCI
  python main.py train-status           → status do modelo neural
  python main.py weights                → exibe pesos CCI atuais

  ── API / Frontend ──
  python main.py serve                  → inicia o servidor FastAPI (porta 8000)
"""
import sys
import os
from cmre_engine import CMREOrchestrator


EXEMPLOS = [
    "Fotógrafa profissional no meio de uma floresta tropical densa ao entardecer, "
    "com raios de sol dourado atravessando as folhas, câmera na mão, "
    "expressão concentrada, roupa de campo, mochila de equipamentos",

    "Produto: garrafa de whisky premium em estúdio escuro com iluminação lateral dramática, "
    "gelo derretendo ao lado, condensação na superfície do vidro, fundo preto infinito, "
    "reflexos perfeitos no tampo metálico",

    "Close-up extremo de olho humano realista, íris azul-esverdeada com detalhes de fibras, "
    "reflexo de janela no vítreo, cílios individuais nítidos, fundo desfocado suave",
]


# ─── Comando: analyze ─────────────────────────────────────────────────────────

def cmd_analyze(image_paths: list[str]):
    """Lado A — analisa fotos reais e salva no banco de referências."""
    from cmre_engine.analyzer import PhotoAnalyzer
    from cmre_engine.reference import ReferenceDatabase
    from cmre_engine.config import REFERENCE_DB_PATH

    db = ReferenceDatabase(REFERENCE_DB_PATH)
    analyzer = PhotoAnalyzer(db=db)

    print("=" * 60)
    print("  CMRE ANALYZER — Lado A: Análise de Fotos Reais")
    print("=" * 60)

    if not image_paths:
        print("❌ Forneça ao menos um caminho de imagem.")
        print("   Ex: python main.py analyze foto.jpg")
        sys.exit(1)

    for path in image_paths:
        if not os.path.exists(path):
            print(f"❌ Arquivo não encontrado: {path}")
            continue
        try:
            report = analyzer.analyze(path, save_to_db=True)
            print(f"\n{'='*60}")
            print(f"  {report.summary()}")
            print(f"  Gênero detectado: {report.scene_genre}")
            print(f"  Validações L3:")
            for v in report.validations:
                icon = "✅" if v.passed else "⚠️"
                print(f"    {icon} {v.pair}: {v.score:.2f}")
            print(f"{'='*60}")
        except Exception as e:
            print(f"❌ Erro ao analisar {path}: {e}")

    # Mostrar stats após análise
    stats = db.stats()
    print(f"\n📚 Banco atualizado: {stats['total']} referências | "
          f"CCI médio: {stats['avg_cci']:.2f}")


# ─── Comando: stats ────────────────────────────────────────────────────────────

def cmd_stats():
    """Exibe estatísticas do banco de referências."""
    from cmre_engine.reference import ReferenceDatabase
    from cmre_engine.config import REFERENCE_DB_PATH

    print("=" * 60)
    print("  CMRE — Banco de Referências (Lado A)")
    print("=" * 60)

    if not os.path.exists(REFERENCE_DB_PATH):
        print("⚠️  Banco vazio. Use 'python main.py analyze foto.jpg' para popular.")
        return

    db = ReferenceDatabase(REFERENCE_DB_PATH)
    stats = db.stats()

    print(f"\n  Total de referências: {stats['total']}")
    print(f"  CCI médio global:     {stats['avg_cci']:.3f}")
    print(f"\n  Por gênero de cena:")
    for g in stats["by_genre"]:
        bar = "█" * int(g["avg_cci"] * 20)
        print(f"    {g['genre']:<15} {g['count']:>3} fotos | "
              f"CCI médio: {g['avg_cci']:.2f} {bar}")
    print()


# ─── Comando: compare ─────────────────────────────────────────────────────────

def cmd_compare(image_path: str, briefing: str):
    """
    Compara uma foto real (Lado A) com o que seria gerado para um briefing (Lado B).
    Útil para calibrar a qualidade do motor CMRE.
    """
    from cmre_engine.analyzer import PhotoAnalyzer
    from cmre_engine.reference import ReferenceDatabase
    from cmre_engine.config import REFERENCE_DB_PATH

    print("=" * 60)
    print("  CMRE COMPARE — Foto Real vs. Geração")
    print("=" * 60)

    # Análise da foto real
    print(f"\n📷 Analisando foto: {image_path}")
    db = ReferenceDatabase(REFERENCE_DB_PATH)
    analyzer = PhotoAnalyzer(db=db)
    real_report = analyzer.analyze(image_path, save_to_db=True)

    # Geração com o briefing
    print(f"\n🧠 Processando briefing: {briefing[:80]}...")
    engine = CMREOrchestrator()
    gen_report = engine.run(briefing)

    # Comparação
    print("\n" + "=" * 60)
    print("  COMPARAÇÃO DE COERÊNCIA")
    print("=" * 60)
    print(f"\n  {'Dimensão':<25} {'Foto Real':>10}  {'Gerado':>10}  {'Δ':>8}")
    print(f"  {'-'*55}")
    print(f"  {'CCI Global':<25} {real_report.cci_score:>10.3f}  "
          f"{gen_report.cci_score:>10.3f}  "
          f"{gen_report.cci_score - real_report.cci_score:>+8.3f}")

    real_scores = {v.pair: v.score for v in real_report.validations}
    gen_scores  = {v.pair: v.score for v in gen_report.validations}

    for pair in real_scores:
        r = real_scores.get(pair, 0)
        g = gen_scores.get(pair, 0)
        print(f"  {pair:<25} {r:>10.3f}  {g:>10.3f}  {g-r:>+8.3f}")

    print(f"\n  Gênero foto real:   {real_report.scene_genre}")
    print(f"  Imagem gerada:      {gen_report.image_path or 'não gerada'}")
    print()


# ─── Comando: generate (padrão) ───────────────────────────────────────────────

def cmd_generate(briefing: str):
    """Lado B — gera imagem a partir de um briefing (fluxo padrão + referências)."""
    engine = CMREOrchestrator()

    print(f"\n📋 Briefing: {briefing[:100]}{'...' if len(briefing) > 100 else ''}")

    report = engine.run(briefing)

    print("\n" + "=" * 60)
    print("  RESULTADO FINAL")
    print("=" * 60)
    print(f"  CCI Score: {report.cci_score:.3f} {'✅' if report.cci_score >= 0.75 else '⚠️'}")
    print(f"  Backend:   {report.backend_used}")
    print(f"  Imagem:    {report.image_path or 'não gerada'}")
    print(f"\n  Prompt ({len(report.prompt_final)} chars):")
    print(f"  {report.prompt_final[:200]}...")
    print(f"\n  Negative ({len(report.negative_prompt)} chars):")
    print(f"  {report.negative_prompt[:150]}...")

    if report.validations:
        print(f"\n  Validações cross-domain:")
        for v in report.validations:
            status = "✅" if v.passed else "⚠️"
            print(f"  {status} {v.pair}: {v.score:.2f}")

    if report.conflicts_resolved:
        print(f"\n  Conflitos auto-resolvidos: {len(report.conflicts_resolved)}")
        for c in report.conflicts_resolved:
            print(f"     {c}")

    print("\n" + "=" * 60)


# ─── Menu interativo ──────────────────────────────────────────────────────────

def cmd_menu():
    """Menu interativo de geração de imagem."""
    print("=" * 60)
    print("  CMRE ENGINE — Cross-Modal Realism Engine v2.0")
    print("  Motor de 30 Agentes para Geração de Imagem Ultra-Realista")
    print("  Dual-Flow: Análise (Lado A) + Geração Calibrada (Lado B)")
    print("=" * 60)

    print("\nExemplos disponíveis:")
    for i, ex in enumerate(EXEMPLOS, 1):
        print(f"  [{i}] {ex[:70]}...")
    print("  [0] Digite seu próprio briefing")

    escolha = input("\nEscolha (0-3): ").strip()

    if escolha in ("1", "2", "3"):
        briefing = EXEMPLOS[int(escolha) - 1]
    elif escolha == "0":
        briefing = input("\nDescreva a imagem: ").strip()
        if not briefing:
            print("Briefing vazio. Usando exemplo 1.")
            briefing = EXEMPLOS[0]
    else:
        print("Opção inválida. Usando exemplo 1.")
        briefing = EXEMPLOS[0]

    cmd_generate(briefing)


# ─── Comando: harvest ─────────────────────────────────────────────────────────

def cmd_harvest(genres: list[str]):
    """Sistema de aprendizado — coleta diária de fotos por gênero."""
    from cmre_engine.learning.daily_harvest import DailyHarvest

    harvest = DailyHarvest()
    result = harvest.run(genres=genres or None, analyze=True)
    print("\n  Resumo por gênero:")
    for genre, info in result["by_genre"].items():
        print(f"    {genre:<15} {info['found']:>3} novas | {info['ok']:>3} analisadas")


def cmd_harvest_status():
    """Exibe status das coletas anteriores."""
    from cmre_engine.learning.daily_harvest import DailyHarvest
    import json

    harvest = DailyHarvest()
    s = harvest.status()
    print("=" * 60)
    print("  CMRE Harvest — Status")
    print("=" * 60)
    print(f"\n  Total de fotos coletadas: {s['total_photos']}")
    print(f"  Fotos analisadas:         {s['analyzed']}")
    print(f"  Pendentes de análise:     {s['pending_analysis']}")
    print(f"  Total de coletas:         {s['runs_total']}")
    print(f"  Última coleta:            {s['last_run'] or 'nunca'}")
    print(f"  OK na última coleta:      {s['last_run_ok']}")
    print()


# ─── Comando: feedback ────────────────────────────────────────────────────────

def cmd_feedback():
    """Coleta avaliação interativa do usuário sobre a última imagem."""
    from cmre_engine.learning.feedback import FeedbackCollector
    collector = FeedbackCollector()
    print("=" * 60)
    print("  CMRE Feedback — Avaliação de Imagem")
    print("=" * 60)
    collector.collect(
        briefing=input("\nBriefing usado (Enter para pular): ").strip(),
        backend=input("Backend usado (gemini/fooocus/dalle): ").strip() or "gemini",
    )


def cmd_feedback_stats():
    """Exibe estatísticas de feedback acumulado."""
    from cmre_engine.learning.feedback import FeedbackDB

    db = FeedbackDB()
    s = db.stats()
    print("=" * 60)
    print("  CMRE Feedback — Estatísticas")
    print("=" * 60)
    print(f"\n  Total de avaliações:  {s['total_feedbacks']}")
    print(f"  Score médio usuário:  {s['avg_user_score']:.2f} / 1.00")
    print(f"  CCI médio avaliado:   {s['avg_cci']:.3f}")
    print()


# ─── Comando: train ───────────────────────────────────────────────────────────

def cmd_train():
    """Treina a rede neural CCI e recalibra os pesos."""
    from cmre_engine.learning.neural_cci import NeuralTrainer

    print("=" * 60)
    print("  CMRE Neural Training")
    print("=" * 60)
    trainer = NeuralTrainer()
    result = trainer.run(also_calibrate_weights=True)

    if result.get("status") == "no_data":
        print("\n  💡 Dica: colete feedback com 'python main.py feedback'")
        print("       e depois execute 'python main.py train' novamente")
    print()


def cmd_train_status():
    """Exibe status do modelo neural."""
    from cmre_engine.learning.neural_cci import NeuralCCIPredictor
    import json

    p = NeuralCCIPredictor()
    p.load()
    s = p.status()
    print("=" * 60)
    print("  CMRE Neural Model — Status")
    print("=" * 60)
    print(f"\n  Modelo treinado:      {'✅ Sim' if s['is_fitted'] else '❌ Não'}")
    print(f"  Arquivo no disco:     {'✅ Sim' if s['model_exists'] else '❌ Não'}")
    print(f"  Ciclos de treino:     {s['training_runs']}")
    if s.get("last_training"):
        lt = s["last_training"]
        print(f"  Último treino:        {lt.get('timestamp','?')}")
        print(f"  Amostras:             {lt.get('samples',0)}")
        if "rmse_cci" in lt:
            print(f"  RMSE CCI:             {lt['rmse_cci']:.4f}")
            print(f"  RMSE User:            {lt['rmse_user']:.4f}")
    print()


# ─── Comando: weights ─────────────────────────────────────────────────────────

def cmd_weights():
    """Exibe os pesos CCI atuais."""
    from cmre_engine.learning.weight_calibrator import load_weights

    weights = load_weights()
    print("=" * 60)
    print("  CMRE — Pesos CCI Atuais")
    print("=" * 60)
    print()
    for pair, w in sorted(weights.items(), key=lambda x: -x[1]):
        bar = "█" * int(w * 45)
        print(f"  {pair:<25} {w:.4f}  {bar}")
    print(f"\n  Soma: {sum(weights.values()):.6f}")
    print()


# ─── Comando: serve ───────────────────────────────────────────────────────────

def cmd_serve(port: int = 8000):
    """Inicia o servidor FastAPI (requer uvicorn)."""
    try:
        import uvicorn
        print("=" * 60)
        print(f"  CMRE API Server  →  http://localhost:{port}")
        print(f"  Frontend UI      →  http://localhost:{port}/ui/")
        print(f"  Docs interativos →  http://localhost:{port}/docs")
        print("=" * 60)
        uvicorn.run(
            "cmre_engine.api.server:app",
            host="0.0.0.0",
            port=port,
            reload=True,
        )
    except ImportError:
        print("❌ uvicorn não encontrado. Instale com:")
        print("   pip install uvicorn fastapi --break-system-packages")


# ─── Entry point ──────────────────────────────────────────────────────────────

LEARNING_CMDS = {
    "harvest", "harvest-status", "feedback", "feedback-stats",
    "train", "train-status", "weights", "serve",
}

def main():
    args = sys.argv[1:]

    # python main.py analyze foto.jpg [foto2.jpg ...]
    if args and args[0] == "analyze":
        cmd_analyze(args[1:])

    # python main.py stats
    elif args and args[0] == "stats":
        cmd_stats()

    # python main.py compare foto.jpg "briefing..."
    elif args and args[0] == "compare" and len(args) >= 3:
        cmd_compare(args[1], " ".join(args[2:]))

    # ── Aprendizado Contínuo ──────────────────────────────
    elif args and args[0] == "harvest":
        cmd_harvest(args[1:])

    elif args and args[0] == "harvest-status":
        cmd_harvest_status()

    elif args and args[0] == "feedback":
        cmd_feedback()

    elif args and args[0] == "feedback-stats":
        cmd_feedback_stats()

    elif args and args[0] == "train":
        cmd_train()

    elif args and args[0] == "train-status":
        cmd_train_status()

    elif args and args[0] == "weights":
        cmd_weights()

    elif args and args[0] == "serve":
        port = int(args[1]) if len(args) > 1 else 8000
        cmd_serve(port)

    # python main.py "briefing..." (geração direta)
    elif args and args[0] not in (LEARNING_CMDS | {"analyze", "stats", "compare"}):
        print("=" * 60)
        print("  CMRE ENGINE — Geração de Imagem Ultra-Realista")
        print("=" * 60)
        cmd_generate(" ".join(args))

    # Menu interativo
    else:
        cmd_menu()


if __name__ == "__main__":
    main()
