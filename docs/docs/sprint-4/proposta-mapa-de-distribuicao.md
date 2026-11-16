---
title: Proposta para o mapa de distribuição
sidebar_label: Proposta de mapa
sidebar_position: 2
description: O que as análises atuais permitem concluir e o que falta definir para um mapa por câmera.
---

# Proposta para o mapa de distribuição

## O que já existe

O banco proposto no repositório registra cada análise com `camera_id`, `aviary_id`, horários, totais e estado do processamento. A tabela `analysis_level_count` registra, por análise, o identificador do nível, a contagem de aves e o percentual. A ingestão associa o aviário consultando a câmera [1].

Esses registros permitem resumir contagens observadas por câmera e nível ao longo de um período. Eles não definem por si só a posição da câmera dentro da planta do aviário nem a classificação de concentração baixa, média ou alta.

## Por que o cálculo ainda não foi implementado

O PR de backend consultado apresenta uma rota de consulta de análises com contagens por nível e identificador da câmera [2]. Porém, esse endpoint não está integrado ao backend desta branch e não fornece uma posição espacial da câmera. O esquema consultado também não guarda coordenadas, setor ou posição esquemática.

Para transformar contagens em concentração, também faltam limites aprovados para baixa, média e alta e uma janela temporal para combinar análises. Sem esses critérios, qualquer cor ou classificação seria uma regra inventada e poderia induzir a uma interpretação errada do aviário.

Por esse motivo, esta entrega não altera o banco, o backend do responsável pela API nem calcula classes de concentração. A aba de mapa do painel fica reservada, conforme o escopo da Sprint 4.

## Proposta mínima para discussão

Começar com uma representação esquemática, usando a câmera como unidade espacial, conforme a direção inicial da reunião. Antes de implementar, combinar:

1. O que significa concentração para a operação da Raiar: contagem absoluta, percentual por nível ou uma regra que combine ambos.
2. Quais valores separam baixa, média e alta, e quem valida esses limites.
3. Qual intervalo de tempo representa o estado exibido e como tratar análises ausentes ou inadequadas.
4. Como identificar a posição de cada câmera no desenho esquemático e manter esse vínculo quando o equipamento mudar.
5. Qual formato de resposta a API deve fornecer para o dashboard, incluindo câmera, horário da última análise válida e contagens por nível.

Depois desses acordos, pode-se decidir se o backend consulta e agrega `analysis` com `analysis_level_count` ou se a regra deve ser calculada em outro componente. A decisão de dados e qualquer mudança de esquema pertencem à pessoa responsável pelo backend e pelo banco.

## Referências {#referencias}

[1] AGROTECH INTELI. **Integração do nó de borda com o banco de dados**. [Documentação da integração](../sprint-3/integracao-no-banco.md), seções “Extensão do esquema” e “Sem alertas”. Disponível em: repositório do projeto Raiar. Acesso em: 15 nov. 2026.

[2] AGROTECH INTELI. **Feat/backend**. [Pull request 29](https://github.com/AgroTech-Inteli-ATI/2026_02_Raiar/pull/29). Disponível em: GitHub. Acesso em: 15 nov. 2026.
