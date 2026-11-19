---
name: shorts
description: Gera Shorts/TikTok/Reels a partir de um vídeo local ou link autorizado com um único pedido (vídeo, cortes, duração, idioma, estilo). Use quando o utilizador escrever /shorts, pedir para "fazer shorts/cortes" de um vídeo, retomar um projeto de shorts ou ver o estado dos projetos em output/.
---

# /shorts — produção de Shorts num só comando

Todo o trabalho é feito pelo pipeline local `shorts.cmd` (sem APIs pagas). O teu papel é só:
passar o pedido, garantir as confirmações obrigatórias, executar, e apresentar o resultado.
Não reimplementes etapas nem chames FFmpeg/Python diretamente.

## 1. Recolher o pedido

O utilizador escreve normalmente algo como:

```
/shorts
Vídeo: C:\videos\gameplay.mp4   (ou um link)
Cortes: 8
Duração: 45 segundos
Idioma: Português BR
Estilo: Gaming dinâmico
```

- Campos em falta usam os valores de `config/shorts.toml` — **não perguntes** por eles.
- Só pergunta se faltar o **vídeo**.
- Opcionais: `Formato:` (9:16, 1:1, 4:5, 16:9), `Nome:`, `Crédito:`, `Direitos:`.

## 2. Links: confirmação de direitos (obrigatória)

Se o vídeo for um link (http/https) e o pedido **não** trouxer `Direitos: confirmados`, pergunta
ao utilizador, e espera pela resposta, se tem direitos de utilização comercial (conteúdo próprio, licença
CC-BY/CC0 ou autorização escrita). Só acrescenta `Direitos: confirmados` se ele disser que sim.
Nunca assumas a confirmação.

## 3. Executar

Passa cada valor tal como o utilizador o escreveu (o pipeline percebe acentos, "45 segundos",
"Português BR", "Gaming dinâmico", etc.), uma opção por campo, numa só linha, a partir da raiz do repositório:

```powershell
.\shorts.cmd --video "<caminho ou link>" --cortes "<...>" --duracao "<...>" --idioma "<...>" --estilo "<...>"
```

Opções extra quando existirem no pedido: `--formato "<...>"`, `--nome "<...>"`, `--credito "<...>"`,
`--trecho "<...>"` (só links: ex. "primeiros 30 minutos", "10:00-40:00"; recomendado para lives longas),
`--direitos` (só depois da confirmação do passo 2). Omite as opções de campos que o utilizador não indicou.
Não uses `--pedido` com várias linhas (o `cmd.exe` parte o texto nas quebras de linha); se precisares
do texto completo, grava-o num `.txt` e usa `--pedido-ficheiro <ficheiro>`.

- Para verificar a interpretação sem processar: acrescenta `--simular`.
- Vídeos longos (> 10 min) ou muitos cortes: corre em segundo plano (run_in_background) e espera pela
  notificação — não faças polling.
- Correr o **mesmo pedido** outra vez retoma uma execução interrompida ou repete só os cortes que falharam.
  `--refazer` recomeça do zero (só se o utilizador pedir).
- `.\shorts.cmd --listar` mostra todos os projetos e o seu estado.

Códigos de saída: 0 = concluído · 1 = concluído com cortes falhados · 2 = pedido inválido / entrada inválida ·
3 = interrompido · 4 = erro inesperado (ver o log indicado).

## 4. Apresentar o resultado

Lê `output/<projeto>/<execução>/report.md` e apresenta ao utilizador:
- quantos Shorts ficaram prontos e onde (`export/`);
- para cada um: duração e título;
- avisos (menos cortes do que os pedidos, falhas, falta de fala);
- lembra que **nada foi publicado**: o título, a descrição e as hashtags estão em `export/short-NN.txt`.

Se houver erro, mostra a mensagem do comando (já está em linguagem simples) e o próximo passo sugerido.
Não publiques nada nem faças upload para nenhuma plataforma.
