---
title: Arquitetura preliminar da solução
sidebar_label: Arquitetura preliminar
sidebar_position: 10
description: Componentes existentes e propostos para medir aves visíveis por nível do Jump Start.
---

# Arquitetura preliminar da solução

Esta arquitetura organiza a medição de **aves visíveis por nível e por câmera**. O recorte inicial continua sendo um lote, um aviário e um campo de visão fixo, conforme a [proposta de solução](./proposta-de-solucao.md). O número e os limites físicos dos níveis precisam de confirmação com a Raiar. As mesas do Jump Start podem mudar de configuração durante a recria; cada mudança relevante exige revisar e versionar as zonas da imagem.

**Figura 1 – Fluxo preliminar de captura, contagem e consulta**

![A câmera fornece vídeo para amostragem, detecção de aves e atribuição a zonas. A contagem por nível é guardada localmente e poderá seguir para a plataforma proposta; configurações versionadas e contagens manuais apoiam a medição.](/img/arquitetura-preliminar.svg)

Fonte: elaboração da equipe a partir da [proposta](./proposta-de-solucao.md), dos [requisitos](./requisitos.md), do [dicionário de dados](./dicionario-de-dados.md) e do [módulo de detecção](./deteccao-de-aves.md). Os blocos da plataforma representam integração futura, não um serviço já implantado.

## O que existe e o que está proposto

| Bloco | Estado em 15 out. 2026 | Limite atual |
| --- | --- | --- |
| Vídeo, amostragem, triagem, detecção e exportação | Implementados no módulo `raiar_vision` para execução local | O detector pré-treinado não produziu contagem útil no [piloto com a CAM16](./piloto-video-raiar.md). |
| Atribuição de nível | Implementada para polígonos calibrados por câmera | Os níveis reais e as zonas ainda não foram calibrados e aprovados para a instalação. Sem isso, o nível fica indeterminado. |
| Histórico e sincronização | SQLite e cliente de envio com confirmação por ID implementados | O servidor receptor e a operação contínua no aviário ainda não foram validados. |
| Plataforma de consulta | Requisito e proposta arquitetural | Backend, painel, controle de acesso e política de retenção ainda não são uma integração demonstrada. |
| Hardware local | Raspberry Pi 4 com 4 GB como alvo dos [requisitos](./requisitos.md) | Frequência, modelo e capacidade dependem de ensaio no dispositivo real. |

O resultado mínimo de uma análise identifica **quadro, câmera, lote quando conhecido, instante de captura, versões do modelo e das zonas, qualidade, contagem por nível e quantidade sem nível atribuível**. Uma imagem inadequada ou uma falha tem contagem nula, não zero. O percentual por nível usa apenas as aves visíveis que receberam um nível, segundo o [dicionário de dados](./dicionario-de-dados.md).

Telemetria ambiental, se disponível e validada, pode ser associada ao período no histórico. Ela não altera a contagem visual nem demonstra, por si, a causa de uma mudança de ocupação.

## Decisões provisórias de medição

- O sistema mede diretamente o que cada câmera consegue observar. **Não calcula o nível do meio como `total da seção - piso - plataforma`**: ainda não há total instantâneo confiável para a área das mesas, nem garantia de que todas as aves sejam visíveis.
- Uma segunda câmera é candidata apenas se uma avaliação manual demonstrar um nível relevante oculto ou erro de contagem acima da meta acordada. Cada câmera mantém resultados próprios; campos sobrepostos não são somados.
- Mudança de posição da câmera, resolução, recorte ou configuração das mesas exige nova versão das zonas antes de comparar períodos. Resultados anteriores preservam as versões usadas.
- Os nomes N0 (piso), N1 (meio) e N2 (plataforma) são rótulos de trabalho. A quantidade, a nomenclatura e as fronteiras dos níveis precisam de confirmação física; o diagrama não fixa três níveis.

## Verificações para evoluir a arquitetura

1. Obter croqui ou imagens de referência das configurações das mesas por idade, com limites físicos dos níveis, divisórias e possíveis passagens de aves.
2. Anotar uma amostra de quadros por dois avaliadores, incluindo condições de luz e casos de oclusão. Medir fração de quadros avaliáveis e erro de contagem por nível; separar treino e teste por sessão de captura.
3. Comparar uma câmera com uma vista complementar apenas se a etapa anterior mostrar uma lacuna de visibilidade. Definir qual vista responde por cada zona sem duplicar aves.
4. Testar inferência e armazenamento na Raspberry Pi, período sem rede e reenvio após reconexão antes de afirmar operação contínua ou cumprir metas dos requisitos.
