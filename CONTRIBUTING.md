# Guia de contribuição da documentação

Este guia define o padrão das páginas em `docs/docs/`. Toda página nova ou editada deve segui-lo.

## Organização das pastas

```text
docs/docs/
├── index.mdx                      # Visão geral (página inicial)
└── sprint-N/
    ├── _category_.json            # Rótulo e posição da sprint na barra lateral
    ├── nome-da-pagina.md
    └── nome-da-secao/             # Seção com várias páginas
        ├── _category_.json
        ├── index.mdx              # Página de abertura da seção
        └── subpagina.mdx
```

- Cada sprint tem sua pasta `sprint-N/`, com um `_category_.json` que define `label` e `position`.
- Uma seção com várias páginas vira uma subpasta com `index.mdx` de abertura.
- Toda página nova deve ser incluída na tabela da [visão geral](docs/docs/index.mdx).
- Documentos de apoio recebidos do parceiro não entram em `docs/`.

## Nomes de arquivos

- Use `kebab-case`, em minúsculas, sem acentos, espaços ou `_`: `dicionario-de-dados.md`.
- O nome descreve o conteúdo, não a entrega: `requisitos.md`, e não `DOCUMENTACAO_REQUISITOS.md`.
- Use `.md` por padrão e `.mdx` somente quando a página importar componentes ou usar JSX.
- Imagens ficam em `docs/static/img/`, também em `kebab-case`, em subpastas por seção quando houver várias (`img/personas/`).

## Codificação

UTF-8 sem BOM, finais de linha LF e linha em branco no fim do arquivo. O `.editorconfig` e o `.gitattributes` aplicam essas regras.

## Frontmatter

Toda página começa com frontmatter, nesta ordem:

```yaml
---
title: Requisitos funcionais e não funcionais
sidebar_label: Requisitos          # opcional: rótulo curto para a barra lateral
sidebar_position: 4
description: Frase curta, terminada em ponto, usada em buscas e prévias de link.
---
```

- `title` é igual ao título H1 da página.
- `sidebar_position` é único dentro da pasta e segue a ordem de leitura.
- Use aspas apenas quando o valor tiver `:` (por exemplo, `title: "Personas: acompanhamento da recria"`).

## Títulos

- Um único `#` (H1) por página, logo após o frontmatter, igual ao `title`.
- Seções com `##` e subseções com `###`; não pule níveis.
- Letra maiúscula só no início e em nomes próprios: `## Escopo do MVP`, não `## ESCOPO DO MVP`.
- Não numere títulos manualmente (`## 1 Introdução`); o sumário lateral já organiza as seções.

## Texto

- Parágrafos em Markdown simples. O recuo de primeira linha, a justificação e o espaçamento ABNT vêm do CSS; não use `&emsp;`, `&nbsp;` ou espaços para recuar.
- Não use `---` como divisor de seções; os títulos já separam o conteúdo.
- Use **negrito** para termos-chave na primeira ocorrência e tabelas para dados estruturados.
- Termos técnicos devem estar no [glossário](docs/docs/sprint-1/glossario.md).

## Links

- Entre páginas, use o caminho relativo do arquivo com extensão: `[requisitos](./requisitos.md)`. Assim o link funciona no GitHub e no site, e o build falha se ele quebrar.
- Não aponte para páginas da própria documentação por URL do GitHub. Use URL fixada em commit apenas para citar uma versão histórica.

## Figuras

Padrão NBR 14724: título acima, imagem e fonte logo abaixo, cada um em seu próprio parágrafo.

```md
**Figura 1 – Canvas de Proposta de Valor**

![Descrição da imagem para leitores de tela.](/img/canvas-proposta-de-valor.png)

Fonte: elaborado pelos autores (2026).
```

- Numere as figuras em sequência dentro da página e cite-as no texto (“conforme a Figura 1”).
- O texto alternativo descreve a imagem; não o deixe vazio.

## Citações e referências

Sistema numérico, com referências no formato NBR 6023.

- No texto, cite com o número entre colchetes antes da pontuação: `... durante a recria [3].` Para várias fontes: `[2][5]`.
- Liste as fontes ao fim da página, sob o título abaixo. A âncora `{#referencias}` aplica a formatação ABNT.

```md
## Referências {#referencias}

[1] SOBRENOME, N. Título do artigo. **Nome do Periódico**, v. 1, n. 2, p. 10-20, 2024.

[2] ORGANIZAÇÃO. **Título da página**. Disponível em: https://exemplo.org/pagina. Acesso em: 24 set. 2026.
```

- Um parágrafo por referência, na ordem em que aparece no texto.
- Fontes on-line terminam com `Disponível em:` e `Acesso em:`.

## Fluxo de trabalho

1. Crie uma branch a partir de `develop` com o prefixo `docs/` (por exemplo, `docs/requisitos-sprint-2`).
2. Rode `npm run build` em `docs/` antes de abrir o pull request. O build falha com links ou imagens quebrados.
3. Abra o pull request para `develop`.
