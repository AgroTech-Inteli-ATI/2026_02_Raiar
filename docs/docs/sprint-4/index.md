---
title: Dashboard e distribuição do aviário
sidebar_label: Visão geral da Sprint 4
sidebar_position: 0
description: Escopo do dashboard de alertas e proposta para evoluir o mapa de distribuição do aviário.
---

# Dashboard e distribuição do aviário

Esta página resume a integração local disponível para o painel e os limites atuais dos dados usados para alertas e distribuição espacial.

| Página | Conteúdo |
| --- | --- |
| [Alertas e dados esperados](./alertas-e-dados-esperados.md) | Campos já definidos, comportamento da tela demonstrativa e proposta de leitura dos alertas pelo dashboard. |
| [Proposta para o mapa de distribuição](./proposta-mapa-de-distribuicao.md) | Dados existentes, lacunas e decisões necessárias antes de calcular concentração por câmera. |

O painel é um site de frontend próprio em `src/frontend/`, separado deste site de documentação. Para executar a partir da raiz do repositório:

```powershell
cd src/frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

O arquivo `.env.local` precisa conter um token de desenvolvimento local igual ao `RAIAR_API_TOKEN` do backend e um endereço local em `RAIAR_BACKEND_URL`. O Vite encaminha `/api` ao backend e adiciona o bearer token no processo Node; o token não é enviado ao código do navegador. Para iniciar o backend, configure `src/backend/.env` com credenciais locais e siga o README do backend.

Com a API configurada, os filtros carregam câmeras e aviários, e o cabeçalho consulta `GET /health`. Os registros de alerta continuam demonstrativos porque não existe uma rota de leitura de alertas. O módulo isolado de distribuição por câmera ainda não está registrado no backend e usa limites provisórios. Em produção, é necessário disponibilizar proxy reverso de mesma origem e autenticação de usuário; o proxy do Vite existe somente durante o desenvolvimento. Consulte [Alertas e dados esperados](./alertas-e-dados-esperados.md) e [Proposta para o mapa](./proposta-mapa-de-distribuicao.md) para os contratos e limites atuais.
