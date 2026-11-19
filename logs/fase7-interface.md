# Fase 7 — Interface simplificada de produção

- **Data:** 2026-11-19
- **Estado:** implementada e testada (com o vídeo sintético da Fase 6). Sem dependências novas, nem pagas nem gratuitas: o TOML é lido com o `tomllib` da biblioteca padrão do Python.
- **Guia para o utilizador:** [`COMO-USAR.md`](../COMO-USAR.md)

## 1. O que foi criado

| Requisito | Implementação |
|---|---|
| Comando simplificado | **`shorts.cmd`** na raiz: duplo clique abre um assistente com perguntas; também aceita opções em português (`--video --cortes --duracao --idioma --estilo --formato`), `--pedido "texto"` ou `--pedido-ficheiro pedido.txt`. **`/shorts`** no Claude Code (skill em `.claude/skills/shorts/SKILL.md`), que só invoca o `shorts.cmd`, sem lógica própria |
| Pedido em linguagem simples | `scripts/shorts_cli.py` interpreta "45 segundos", "1 minuto", "1:30", "Português BR/PT", "Brasil", "Inglês", "Gaming dinâmico", "Minimalista", "Viral", "vertical", "quadrado"…, com ou sem acentos e em qualquer ordem |
| Ficheiro de configuração | `config/shorts.toml` (comentado em PT): predefinições (cortes, duração, idioma, estilo, formato), pasta de saída e opções avançadas (modelo, GPU/CPU, encoder, teaser, espaço mínimo, intervalo de duração) |
| Estrutura de projetos | `output/<projeto>/` (um por vídeo: `input/` e `analysis/` partilhados) → `output/<projeto>/<estilo>_<formato>_<N>x<D>s_<idioma>/` com `export/`, `review/`, `work/`, `logs/`, `state.json` e `report.md`. Índice global em `output/INDEX.md` |
| Fluxo completo | Ingestão → Análise + Transcrição → Seleção → Edição/Legendas → Renderização → Exportação → Relatório (`scripts/shorts_engine/pipeline.py`) |
| Relatórios | `report.md` por execução (estado, etapas com resumo, cortes com origem no vídeo, títulos, erros, histórico de execuções, próximos passos) + `logs/run-*.log` técnico + `INDEX.md` |
| Tratamento de erros | Validação antes de criar pastas (ficheiro inexistente, link sem direitos, valores fora do intervalo, FFmpeg/yt-dlp em falta). Mensagens em PT com o próximo passo. Erro num corte não para os outros. Erros inesperados → log com traceback + estado guardado. Espaço em disco mínimo. Vídeo sem som, sem imagem ou demasiado curto. Config com sintaxe inválida → linha exata |
| Retomar projetos | `state.json` gravado de forma atómica após cada etapa e cada corte. Correr o mesmo pedido salta o que está feito (ingestão, análise em cache, seleção gravada, cortes exportados) e refaz só o que falta. `--refazer` recomeça. Pedido já concluído → mostra onde estão os resultados |
| Sem programação | Duplo clique, perguntas em PT, arrastar o ficheiro para a janela, resultados numa pasta `export/` com `.txt` para copiar e colar |

Códigos de saída: 0 concluído · 1 concluído com cortes falhados · 2 pedido/entrada inválidos · 3 interrompido · 4 erro inesperado.

Outras alterações:
- `scripts/make_shorts.py` passou a ser uma interface avançada (opções em inglês) sobre o mesmo pipeline. Também escreve em `output/`.
- `.gitignore`: `output/` ignorado; as junctions das skills do vendor passam a estar listadas uma a uma, para a skill `/shorts` ser versionada.
- `.gitattributes`: `*.cmd`, `*.bat` e `*.ps1` com CRLF (o `cmd.exe` não lê bem batch com LF).
- O PATH é recarregado a partir do registo do Windows no arranque, para que FFmpeg/yt-dlp sejam encontrados mesmo em terminais abertos antes da instalação.

## 2. Testes

| Teste | Resultado |
|---|---|
| Opções com acentos via `shorts.cmd` ("45 segundos", "Português BR", "Gaming dinâmico") | interpretado: 8 × 45 s, pt-BR, gaming |
| Pedido em ficheiro no formato do utilizador (`/shorts`, "1 minuto", "Português de Portugal", "Viral com motion graphics", "vertical") | interpretado: 3 × 60 s, pt-PT, viral, 9:16 |
| Valores inválidos ("rápido", "cinema") | lista os 2 erros + exemplo, exit 2 |
| Ficheiro inexistente / link sem direitos / 50 cortes | mensagem clara, exit 2, **nenhuma pasta criada** |
| Assistente (stdin simulado) | pergunta todos os campos. Num link pede a confirmação de direitos e recusa com "não" |
| Execução completa 3 × 25 s gaming | 5 etapas, 3 Shorts |
| **Interrupção forçada** (processo morto após o 1.º corte, com o 2.º a meio) | estado: etapas 1–3 concluídas, `short-01` concluído, `short-02` parcial |
| **Retoma** com o mesmo pedido | "A retomar…", ingestão/análise/seleção reaproveitadas, `short-01` saltado, `short-02` refeito, `short-03` feito → 3/3 |
| Mesmo pedido já concluído | "Este pedido já foi concluído" + caminho, exit 0 |
| 8 × 45 s num vídeo de 100 s | aviso "só há 2 momentos distintos", gera 2, exit 0 |
| Outro estilo do mesmo vídeo | transcrição reaproveitada (cache do projeto) |
| `--listar` | tabela de execuções com estado e nº de Shorts |
| Config com valor inválido (`cortes = cinco`) | "Invalid value (at line 8, column 11)" |
| Config gravado com BOM | aceite |
| `make_shorts.py --dry-run` | funciona sobre o pipeline novo e escreve em `output/` |

### Problemas encontrados e corrigidos

1. `shorts.cmd` gravado com LF → o `cmd.exe` partia os comandos. Convertido para CRLF + `.gitattributes`.
2. FFmpeg "não encontrado" num terminal com PATH antigo → PATH recarregado do registo.
3. Pedidos inválidos criavam pastas vazias em `output/` → validação (`preflight`) antes de criar pastas.
4. Títulos com `|` partiam a tabela do relatório; detalhes das etapas ilegíveis → escape + resumos por etapa.
5. Config com BOM dava um erro na linha 1 → leitura com `utf-8-sig`.
6. BOM na entrada colada impedia reconhecer links → removido.
7. Saída sem buffer (`PYTHONUNBUFFERED`) para o progresso aparecer em tempo real.
8. Títulos sem tema conhecido deixam de levar um sufixo fraco ("| Times").

## 3. Pendente (vem das fases anteriores)

- Teste com **vídeo real** e com **áudio em português** (Fases 4 e 6).
- A Fase 5 não foi pedida.
