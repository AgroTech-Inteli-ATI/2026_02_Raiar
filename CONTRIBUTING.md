# Guia de contribuição da documentação

Este guia define o padrão das páginas em `docs/docs/`. Toda página nova ou editada deve segui-lo.

## Organização das pastas

```text
docs/docs/
├── index.mdx                      # Solução e escopo
├── funcionamento.mdx
├── resultados.mdx
├── painel.mdx
├── tecnico/                       # Instalação, contratos e modelos
└── apoio/                         # Perfis, estudos, glossário e histórico
```

- A barra lateral em `docs/sidebars.ts` define o percurso principal, a referência técnica e o apoio.
- Antes de criar uma página, procure o assunto existente. Use uma seção quando o conteúdo fizer parte da mesma tarefa de leitura.
- Cada contrato, procedimento ou resultado detalhado tem uma página de referência; as demais páginas trazem uma síntese com link.
- Ao consolidar documentos, preserve condições de teste, limitações, referências, figuras e contexto histórico. Não apresente proposta antiga como implementação atual.
- Os caminhos antigos estão mapeados em `docs/legacy-routes.json`, incluindo âncoras. O plugin `docs/plugins/legacy-routes/` mantém os redirecionamentos no preview e no build.
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
- `sidebar_position` pode ser preservado como metadado histórico. A ordem de leitura da barra lateral é definida em `docs/sidebars.ts`.
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
- Termos técnicos devem estar no [glossário](docs/docs/apoio/glossario.mdx).

## Links

- Entre páginas, use o caminho relativo do arquivo com extensão: `[requisitos](./requisitos.md)`. Assim o link funciona no GitHub e no site, e o build falha se ele quebrar.
- Não aponte para páginas da própria documentação por URL do GitHub. Use URL fixada em commit apenas para citar uma versão histórica.

## Figuras

Padrão NBR 14724: título acima, imagem e fonte logo abaixo, cada um em seu próprio parágrafo.

```mdx
**Figura 1 – Canvas de Proposta de Valor**

![Descrição da imagem para leitores de tela.](/img/canvas-proposta-de-valor.png)

<p className="figure-source">Fonte: produzido pela equipe, 2026</p>

Parágrafo com o contexto da figura e as considerações necessárias para interpretá-la.
```

- Numere as figuras em sequência dentro da página e cite-as no texto (“conforme a Figura 1”).
- O texto alternativo descreve a imagem; não o deixe vazio.
- Para material autoral, use exatamente `Fonte: produzido pela equipe, 2026`. Preserve a atribuição original de material externo.
- Escreva contexto, limitações e outras considerações em um parágrafo simples abaixo da fonte. Os links para a imagem original e o código podem ficar em um bloco `figure-links` separado.

### Diagramas de fluxo

Produza ou revise os fluxos no [Mermaid Live](https://mermaid.live/), confira a renderização e exporte o SVG pelo site. Converta-o para PNG em alta resolução para exibição nas páginas. Guarde o código `.mmd` e o SVG ao lado do PNG em `docs/static/img/`. Inclua os links para o PNG e para o código editável abaixo das considerações sobre a figura. Preserve a distinção entre etapas implementadas, propostas e integrações ainda não verificadas.

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
