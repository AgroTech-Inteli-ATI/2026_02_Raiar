---
title: Proposta para o mapa de distribuição
sidebar_label: Proposta de mapa
sidebar_position: 2
description: Dados existentes, cálculo provisório por câmera e decisões para o mapa de distribuição.
---

# Proposta para o mapa de distribuição

## O que o backend já oferece

O backend persiste análises com `camera_id`, `aviary_id`, horários, totais e estado do processamento. A tabela `analysis_level_count` guarda, por análise, o identificador do nível, a contagem de aves e o percentual. A ingestão associa o aviário cadastrado à câmera e registra o lote correspondente ao instante de captura [1].

`GET /analyses` aceita filtros por `camera_id`, `aviary_id`, `lot_id`, `status`, `lot_association_status`, `from`, `to`, `limit` e `offset`. Retorna `{data, pagination}`; cada linha inclui `visible_birds`, `assigned_total`, `unassigned_birds` e `levels`. `GET /cameras` fornece IDs, nomes e aviário associado. As duas rotas exigem autenticação.

O esquema não guarda coordenadas, setor nem posição de câmera na planta. As contagens permitem comparar o que cada câmera observou, mas não posicionar os dispositivos em um desenho físico. A primeira visualização, portanto, só pode ser uma lista ou grade esquemática, claramente identificada como não espacial.

## Módulo isolado implementado

`src/backend/src/distributionMap.ts` contém um plugin Fastify isolado para uma futura rota `GET /distribution/cameras` e a função de resumo por câmera. O cálculo considera somente análises com `status = 'valido'` e `visible_birds` disponível. Por câmera, retorna a média de aves visíveis por análise, a quantidade de análises válidas, o horário da análise mais recente e a classe de concentração.

A janela de tempo deve ser aplicada pela consulta, com `from` inclusivo e `to` exclusivo sobre `captured_at`. A paginação limita os resumos por câmera. Sem limites configurados, o plugin responde `503 distribution_not_configured`. O plugin ainda não foi registrado em `src/backend/src/app.ts`, respeitando o limite de não alterar o arquivo de integração mantido pelo Cauê.

Para integrar, o Cauê precisa importar `distributionMapRoutes` e `readProvisionalThresholds` de `./distributionMap.js` e adicionar dentro de `buildApp`, antes de `return app`, esta chamada:

```ts
app.register(distributionMapRoutes, {
  prefix: '/distribution',
  db,
  thresholds: readProvisionalThresholds(process.env),
});
```

A chamada deve permanecer dentro do app que aplica o hook global de autenticação. Os limites são configurados por `RAIAR_CONCENTRATION_LOW_MAX` e `RAIAR_CONCENTRATION_MEDIUM_MAX`, ambos em média de aves visíveis por análise. Não há valores padrão no código. Os valores `5` e `10` nos testes são fixtures artificiais para testar as faixas, não valores oficiais nem recomendação operacional.

## Limites e decisões pendentes

A média de aves visíveis não considera área, distância ou campo de visão de cada câmera. Ela é somente uma regra técnica inicial, não uma medida validada de densidade ou bem-estar. Os níveis baixa, média e alta, a janela de observação e o tratamento de câmeras sem dados válidos precisam ser acordados com a Raiar antes de usar o resultado para tomada de decisão.

Também é necessário confirmar se a primeira versão será uma lista/grade esquemática ou se há uma planta e posições de câmeras que podem ser usadas. Sem coordenadas, não se deve apresentar os resultados como um mapa físico.

Perguntas para fechar a proposta:

1. A média de aves visíveis por análise é uma medida aceitável para representar concentração por câmera?
2. Quais limites provisórios separam baixa, média e alta e quem da Raiar os valida?
3. Qual intervalo de tempo deve representar o estado mostrado?
4. O que mostrar para câmeras sem análise válida no período?
5. A Raiar pode fornecer uma planta e a posição aproximada de cada câmera ou a primeira versão será somente uma grade?
6. O Cauê pode registrar o plugin em `app.ts` e confirmar o contrato de resposta da rota?

Os testes do módulo ficam em `src/backend/tests/distribution-map.test.ts`. A regra e os limites devem continuar identificados como provisórios até validação operacional.

## Referências {#referencias}

[1] AGROTECH INTELI. **Backend e integração com o banco de dados**. [Documentação do backend](./backend.md), seções sobre análises, rotas e histórico de ocupação. Disponível em: repositório do projeto Raiar. Acesso em: 16 nov. 2026.
