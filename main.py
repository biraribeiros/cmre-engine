"""
CMRE Engine — Ponto de entrada principal.
Execute: python main.py
"""
import sys
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


def main():
    print("=" * 60)
    print("  CMRE ENGINE — Cross-Modal Realism Engine v1.0")
    print("  Motor de 30 Agentes para Geração de Imagem")
    print("=" * 60)

    engine = CMREOrchestrator()

    # Modo interativo
    if len(sys.argv) > 1:
        briefing = " ".join(sys.argv[1:])
    else:
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

    print(f"\n📋 Briefing: {briefing[:100]}{'...' if len(briefing) > 100 else ''}")

    # Executar o motor
    report = engine.run(briefing)

    # Exibir resultado
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


if __name__ == "__main__":
    main()
