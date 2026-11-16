---
title: Dashboard e distribuição do aviário
sidebar_label: Visão geral da Sprint 4
sidebar_position: 0
description: Escopo do dashboard de alertas e proposta para evoluir o mapa de distribuição do aviário.
---

# Dashboard e distribuição do aviário

Esta página registra o que a estrutura atual do projeto permite entregar para o painel e o que ainda precisa ser combinado para transformar análises por câmera em uma distribuição espacial confiável.

| Página | Conteúdo |
| --- | --- |
| [Alertas e dados esperados](./alertas-e-dados-esperados.md) | Campos já definidos, comportamento da tela demonstrativa e proposta de leitura dos alertas pelo dashboard. |
| [Proposta para o mapa de distribuição](./proposta-mapa-de-distribuicao.md) | Dados existentes, lacunas e decisões necessárias antes de calcular concentração por câmera. |

O painel é um site de frontend próprio em `src/frontend/`, separado deste site de documentação. Para executar a partir da raiz do repositório:

```powershell
cd src/frontend
npm install
npm run dev
```

O Vite informa o endereço local, normalmente `http://localhost:5173/`. Sem `VITE_API_BASE_URL`, a aba de alertas usa registros demonstrativos. O backend integrado oferece consultas de análises, mas ainda não oferece geração ou leitura de alertas. O módulo isolado para cálculo de distribuição por câmera também aguarda validação dos limites e registro da rota no backend. A configuração e as lacunas estão descritas em `src/frontend/README.md`, [Alertas e dados esperados](./alertas-e-dados-esperados.md) e [Proposta para o mapa](./proposta-mapa-de-distribuicao.md).
