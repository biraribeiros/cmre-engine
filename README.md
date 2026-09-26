# CMRE Engine — Cross-Modal Realism Engine

**Motor de 30 Agentes para Geração de Imagem Ultra-Realista**

> Desenvolvido por **Bira Ribeiro** — Via Multimidia  
> Patos de Minas, MG, Brasil · 2026

---

## O que é o CMRE?

O **Cross-Modal Realism Engine** é um sistema de orquestração de 30 agentes especializados que transforma um briefing textual simples em um prompt fotorrealista otimizado para geradores de imagem por IA.

O motor vai muito além de "reescrever o prompt": ele decompõe a cena em **16 blocos técnicos independentes**, valida **7 pares de coerência cross-modal** e calcula um **Índice de Coerência Cross-Modal (CCI)** antes de submeter qualquer imagem para geração.

---

## Arquitetura: 5 Camadas · 30 Agentes

```
Briefing do Usuário
        │
        ▼
┌──────────────────────────────────┐
│  L0 — AGENTE 00                  │
│  CMREOrchestrator                │
└──────────────┬───────────────────┘
               │
        ┌──────▼──────┐
        │   CAMADA 1  │  (Agentes 01–02)
        │  Análise    │  IntentParser + SceneClassifier
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   CAMADA 2  │  (Agentes 03–18)
        │  16 Blocos  │  Técnicos: saída, enquadramento, sensor,
        │  Técnicos   │  óptica, exposição, luz, cor, sujeito,
        └──────┬──────┘  materiais, ambiente, profundidade...
               │
        ┌──────▼──────┐
        │   CAMADA 3  │  (Agentes 19–25)
        │  7 Cross-   │  Luz×Sombra, Clima×Corpo, Câmera×Física,
        │  Validators │  Anatomia×Física, Materiais×Cor,
        └──────┬──────┘  Entropia×Contexto, Escala×Proporção
               │
        ┌──────▼──────┐
        │   CAMADA 4  │  (Agentes 26–30)
        │  CCI + Saída│  CCI Calculator → Conflict Resolver →
        └──────┬──────┘  Prompt Synthesizer → Negative → Executor
               │
        ┌──────▼──────┐
        │   BACKEND   │  Gemini · Fooocus · DALL-E
        └─────────────┘
```

---

## CCI — Índice de Coerência Cross-Modal

O CCI é o "coração" do CMRE. Calcula-se como média ponderada dos 7 pares validados:

| Par Cross-Modal       | Peso  | O que verifica                          |
|-----------------------|-------|-----------------------------------------|
| Luz × Sombra          | 0.22  | Consistência de direção e temperatura   |
| Anatomia × Física     | 0.20  | Postura, proporções, centro de gravidade|
| Câmera × Física       | 0.15  | Motion blur vs. velocidade do obturador |
| Materiais × Cor       | 0.13  | Reflectância vs. grading de cor         |
| Clima × Corpo         | 0.12  | Roupas e postura condizentes com o tempo|
| Entropia × Contexto   | 0.10  | Nível de detalhe adequado ao contexto   |
| Escala × Proporção    | 0.08  | Tamanho relativo de objetos e pessoas   |

**Aprovação: CCI ≥ 0.75**. Abaixo disso, o Conflict Resolver tenta auto-corrigir.

---

## Backends Suportados

| Backend      | Custo        | Requisito       | Resolução        |
|--------------|-------------|-----------------|------------------|
| **Gemini**   | Gratuito (500/dia) | API key Google | 1024×1024 (padrão) |
| **Fooocus**  | Gratuito (local) | 4GB VRAM + DirectML | 1024×1024–2048 |
| **DALL-E 3** | ~$0.04/imagem | API key OpenAI | 1792×1024 HD |

> **Recomendado para hardware 4GB VRAM sem CUDA:** Gemini (API) como primário + Fooocus (DirectML) como backup local.

---

## Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/biraribeiros/cmre-engine
cd cmre-engine

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure o ambiente
cp .env.example .env
# Edite .env com sua GEMINI_API_KEY

# 4. Execute
python main.py
```

### Obter chave Gemini (gratuita)
1. Acesse: https://aistudio.google.com/apikey
2. Clique em **"Create API Key"**
3. Cole no `.env`: `GEMINI_API_KEY=sua_chave_aqui`

---

## Uso como Biblioteca

```python
from cmre_engine import CMREOrchestrator

engine = CMREOrchestrator()

report = engine.run(
    "Fotógrafa profissional em floresta tropical ao entardecer, "
    "raios de luz dourada atravessando as folhas, câmera Canon na mão"
)

print(f"CCI Score: {report.cci_score:.3f}")  # ex: 0.847
print(f"Prompt gerado ({len(report.prompt_final)} chars):")
print(report.prompt_final)

# Imagem salva em: outputs/gemini/cmre_20260925_213042.jpg
print(f"Imagem: {report.image_path}")
```

---

## Variáveis de Ambiente

| Variável          | Padrão    | Descrição                           |
|-------------------|-----------|-------------------------------------|
| `CMRE_BACKEND`    | `gemini`  | Backend: `gemini` / `fooocus` / `dalle` |
| `GEMINI_API_KEY`  | —         | Chave da API Google Gemini          |
| `OPENAI_API_KEY`  | —         | Chave da API OpenAI (DALL-E)        |
| `FOOOCUS_HOST`    | `http://localhost:7865` | Endereço do Fooocus local |
| `CMRE_VERBOSE`    | `true`    | Logs detalhados por camada          |
| `CMRE_OUTPUT_DIR` | `outputs` | Pasta de saída das imagens          |

---

## Estrutura do Projeto

```
cmre-engine/
├── main.py                    # CLI com exemplos interativos
├── requirements.txt
├── .env.example
└── cmre_engine/
    ├── __init__.py
    ├── config.py              # Configuração e seleção de backend
    ├── models.py              # CCIReport, TechnicalBlocks, ValidationResult
    ├── orchestrator.py        # Agente 00 — CMREOrchestrator
    ├── agents/
    │   ├── layer1.py          # Agentes 01-02: IntentParser, SceneClassifier
    │   ├── layer2.py          # Agentes 03-18: 16 Blocos Técnicos
    │   ├── layer3.py          # Agentes 19-25: 7 Cross-Domain Validators
    │   └── layer4.py          # Agentes 26-30: CCI, Resolver, Synthesizer
    └── backends/
        ├── gemini_backend.py  # Google Gemini 2.5 Flash (gratuito)
        ├── fooocus_backend.py # Fooocus local (DirectML, sem CUDA)
        └── dalle_backend.py   # OpenAI DALL-E 3 (pago)
```

---

## Os 30 Agentes em Detalhe

| # | Agente | Camada | Responsabilidade |
|---|--------|--------|-----------------|
| 00 | CMREOrchestrator | L0 | Coordena todas as camadas |
| 01 | IntentParser | L1 | Extrai intenção, palavras-chave e estilo |
| 02 | SceneClassifier | L1 | Classifica domínios ativos da cena |
| 03 | Agente_Saida | L2 | Formato, resolução, aspect ratio |
| 04 | Agente_Enquadramento | L2 | Composição, plano, ângulo de câmera |
| 05 | Agente_SensorMeio | L2 | Câmera, lente, meio fotográfico |
| 06 | Agente_Optica | L2 | Abertura, bokeh, distorções ópticas |
| 07 | Agente_Exposicao | L2 | Velocidade, ISO, exposição |
| 08 | Agente_Luz | L2 | Temperatura, direção, qualidade da luz |
| 09 | Agente_Cor | L2 | Grading, paleta, saturação |
| 10 | Agente_Sujeito | L2 | Descrição detalhada do sujeito principal |
| 11 | Agente_Materiais | L2 | Texturas, materiais, superfícies |
| 12 | Agente_Ambiente | L2 | Cenário, fundo, atmosfera |
| 13 | Agente_Profundidade | L2 | Planos, perspectiva, profundidade de campo |
| 14 | Agente_TexturaCaptura | L2 | Grain, ruído, textura fotográfica |
| 15 | Agente_Imperfeicoes | L2 | Imperfeições realistas, artefatos naturais |
| 16 | Agente_EntropiaContexto | L2 | Nível de detalhe e complexidade |
| 17 | Agente_MovimentoFisica | L2 | Movimento, física, dinâmica |
| 18 | Agente_Exclusoes | L2 | Negative prompt contextual |
| 19 | Validator_LuzSombra | L3 | Coerência luz ↔ sombras (peso 0.22) |
| 20 | Validator_ClimaCopo | L3 | Clima ↔ roupas/postura (peso 0.12) |
| 21 | Validator_CameraFisica | L3 | Parâmetros câmera ↔ física (peso 0.15) |
| 22 | Validator_AnatomiaFisica | L3 | Anatomia ↔ física/gravidade (peso 0.20) |
| 23 | Validator_MateriaisCor | L3 | Materiais ↔ grading de cor (peso 0.13) |
| 24 | Validator_EntropiaContexto | L3 | Caos visual ↔ contexto (peso 0.10) |
| 25 | Validator_EscalaProportcao | L3 | Escala relativa dos elementos (peso 0.08) |
| 26 | CCICalculator | L4 | Calcula o CCI final ponderado |
| 27 | ConflictResolver | L4 | Auto-corrige conflitos identificados |
| 28 | PromptSynthesizer | L4 | Monta o prompt final otimizado |
| 29 | NegativePromptFinal | L4 | Consolida o negative prompt completo |
| 30 | Executor | L4 | Chama o backend e salva a imagem |

---

## Fooocus com DirectML (4GB VRAM, sem CUDA)

Para usar o backend local sem CUDA:

```bash
# 1. Clone o Fooocus
git clone https://github.com/lllyasviel/Fooocus
cd Fooocus

# 2. Instale o DirectML
pip install torch-directml

# 3. Inicie o servidor API
python entry_with_update.py --directml --listen

# 4. Configure no .env
CMRE_BACKEND=fooocus
FOOOCUS_HOST=http://localhost:7865
```

---

## Sobre o Projeto

O CMRE nasceu da necessidade de gerar imagens fotorrealistas com qualidade profissional para campanhas de marketing e produção audiovisual, sem depender de hardware de alta gama.

A arquitetura de múltiplos agentes permite que cada domínio técnico (luz, óptica, materiais, anatomia) seja tratado por um especialista dedicado, enquanto os validadores cross-modais garantem que os domínios sejam coerentes entre si — o mesmo problema que faz muitas imagens geradas por IA parecerem "erradas" sem que o observador consiga identificar o motivo.

---

**Via Multimidia · Patos de Minas, MG · 2026**  
🔗 [github.com/biraribeiros](https://github.com/biraribeiros)
