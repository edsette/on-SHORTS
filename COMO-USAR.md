# Como usar o GTA6-SHORTS

Transforma um vídeo em vários Shorts / TikToks / Reels prontos a publicar: cortes escolhidos
automaticamente, enquadramento vertical, legendas animadas, título, descrição e hashtags.
Tudo corre no teu computador. **Nada é publicado automaticamente.**

---

## Opção 1 — Duplo clique (mais simples)

1. Abre a pasta `GTA6-SHORTS` e faz **duplo clique em `shorts.cmd`**.
2. Responde às perguntas (Enter aceita o valor sugerido):
   - **Vídeo:** arrasta o ficheiro para a janela, ou cola um link
   - **Quantos cortes**, **Duração**, **Idioma**, **Estilo**, **Formato**
3. Espera. No fim aparece a pasta com os vídeos.

## Opção 2 — No Claude Code, escreve `/shorts`

```
/shorts
Vídeo: C:\videos\gameplay.mp4
Cortes: 8
Duração: 45 segundos
Idioma: Português BR
Estilo: Gaming dinâmico
```

Podes escrever os campos pela ordem que quiseres, com ou sem acentos. Os campos que não indicares
usam os valores do ficheiro de configuração.

## Opção 3 — Numa linha de comando

```
shorts --video "C:\videos\gameplay.mp4" --cortes 8 --duracao "45 segundos" --idioma "Português BR" --estilo "Gaming dinâmico"
```

---

## O que posso escrever em cada campo

| Campo | Exemplos aceites |
|---|---|
| Vídeo | `C:\videos\clip.mp4`, ou um link (ver *Links* abaixo) |
| Cortes | `8`, `5 cortes` (1 a 30) |
| Duração | `45`, `45 segundos`, `1 minuto`, `1:30` (5 a 180 s) |
| Idioma | `Português BR`, `Brasil`, `Português PT`, `Portugal`, `Inglês`, `auto` |
| Estilo | `Gaming dinâmico`, `Minimalista`, `Viral` (com motion graphics) |
| Formato | `9:16` / `vertical` (Shorts, TikTok, Reels), `1:1` / `quadrado`, `4:5`, `16:9` / `horizontal` |
| Nome (opcional) | nome da pasta do projeto |
| Crédito (opcional) | texto de fonte/crédito para a descrição |

### Os 3 estilos

- **Gaming dinâmico:** legendas grandes palavra a palavra, zoom nos momentos fortes, abre com o melhor momento.
- **Minimalista:** vídeo inteiro sobre fundo desfocado, legendas discretas, sem efeitos.
- **Viral:** cores fortes, título animado, barra de progresso, convite final para seguir.

### Links

Só podes usar vídeos **teus**, com licença **CC-BY / CC0** ou com **autorização escrita** do autor.
Num link, acrescenta `Direitos: confirmados` ao pedido (ou responde "sim" no assistente).
Sem isso, o link é recusado.

---

## Onde ficam os resultados

Tudo fica dentro da pasta **`output/`**:

```
output/
├── INDEX.md                          ← lista de todos os projetos
└── gameplay/                         ← um projeto por vídeo
    └── gaming_9x16_8x45s_pt-BR/      ← uma pasta por pedido
        ├── export/                   ← OS TEUS SHORTS
        │   ├── short-01.mp4
        │   ├── short-01.txt          ← título, descrição e hashtags para copiar
        │   └── …
        ├── review/                   ← imagens de pré-visualização de cada Short
        └── report.md                 ← relatório da execução
```

## Se algo correr mal

- A mensagem explica o problema e o que fazer, em português.
- **Interrompeste ou o PC desligou-se?** Corre **o mesmo pedido** outra vez: continua de onde parou.
- **Um Short falhou?** Os outros continuam. Corre o mesmo pedido para tentar outra vez só esse.
- **Queres refazer tudo?** Acrescenta `--refazer`.
- **Ver o estado de todos os projetos:** `shorts --listar`.
- Detalhes técnicos de cada execução: pasta `logs/` dentro do pedido.

## Mudar os valores por omissão

Abre `config\shorts.toml` no Bloco de Notas, muda os valores depois do `=` e grava.
Exemplo: `cortes = 8` e `duracao = 45`.

## Dicas para melhores resultados

- Vídeos **com voz/comentário** dão muito melhores cortes: o sistema usa o que é dito para encontrar
  momentos engraçados, surpreendentes e interessantes.
- Revê sempre os vídeos e os textos antes de publicar.
