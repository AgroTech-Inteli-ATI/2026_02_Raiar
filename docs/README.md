# Site de documentação

Site da documentação do projeto Raiar Orgânicos, construído com [Docusaurus](https://docusaurus.io/). Requer Node.js 20 ou superior.

## Comandos

| Comando | Descrição |
| --- | --- |
| `npm install` | Instala as dependências. |
| `npm run start` | Inicia o servidor local com recarga automática. |
| `npm run build` | Gera o site estático em `build/`. Falha se houver link ou imagem quebrada. |
| `npm run serve` | Serve localmente o conteúdo de `build/`. |
| `npm run typecheck` | Verifica os tipos dos arquivos TypeScript. |

## Organização

- `docs/`: páginas da documentação. A barra lateral é gerada a partir das pastas.
- `src/css/custom.css`: paleta da Raiar e formatação ABNT do corpo do texto, das figuras e das referências.
- `static/img/`: imagens, referenciadas nas páginas como `/img/...`.

Os padrões de nomes, frontmatter, títulos, figuras e referências estão no [guia de contribuição](../CONTRIBUTING.md).
