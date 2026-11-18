---
title: Dashboard e distribuição do aviário
sidebar_label: Dashboard e distribuição
sidebar_position: 1
description: Escopo do dashboard de alertas e proposta para evoluir o mapa de distribuição do aviário.
---

# Dashboard e distribuição do aviário

Esta página resume a integração local disponível para o painel e os limites atuais dos dados usados para alertas e distribuição espacial.

## Prévia do frontend

![Dashboard do aviário na aba de alertas, com registros demonstrativos](/img/sprint-4/dashboard-alertas.png)

Captura do painel em modo demonstrativo. Os registros e a ilustração exibidos são exemplos, não dados reais do aviário.

| Página | Conteúdo |
| --- | --- |
| [Alertas e dados esperados](./alertas-e-dados-esperados.md) | Campos já definidos, comportamento da tela demonstrativa e proposta de leitura dos alertas pelo dashboard. |
| [Proposta para o mapa de distribuição](./proposta-mapa-de-distribuicao.md) | Dados existentes, lacunas e decisões necessárias antes de calcular concentração por câmera. |

O painel é um site de frontend próprio em `src/frontend/`, separado deste site de documentação. Para executar a partir da raiz do repositório:

```powershell
cd src/frontend
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm install
npm run dev
```

No arquivo `.env.local`, mantenha `VITE_API_BASE_URL=/api`, configure um endereço local em `RAIAR_BACKEND_URL` e defina `RAIAR_DEV_API_TOKEN` com o mesmo valor de `RAIAR_API_TOKEN` do backend. O Vite encaminha `/api` ao backend e adiciona o bearer token no processo Node; o token não é enviado ao código do navegador. Para iniciar o backend, configure `src/backend/.env` com credenciais locais e siga o README do backend.

Com a API configurada, os filtros carregam câmeras e aviários, e o cabeçalho consulta `GET /health`. Os registros de alerta continuam demonstrativos porque não existe uma rota de leitura de alertas. O módulo isolado de distribuição por câmera ainda não está registrado no backend e usa limites provisórios. Em produção, é necessário disponibilizar proxy reverso de mesma origem e autenticação de usuário; o proxy do Vite existe somente durante o desenvolvimento. Consulte [Alertas e dados esperados](./alertas-e-dados-esperados.md) e [Proposta para o mapa](./proposta-mapa-de-distribuicao.md) para os contratos e limites atuais.
