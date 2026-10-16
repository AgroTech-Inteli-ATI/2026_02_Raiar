---
title: Modelos de detecção e contagem de aves
sidebar_label: Visão geral da Sprint 2
sidebar_position: 0
description: Os três modelos desenvolvidos na Sprint 2 para identificar e contar aves, com a documentação de cada um.
---

# Modelos de detecção e contagem de aves

Na Sprint 2, a equipe desenvolveu três abordagens para identificar aves em imagens e vídeos da Raiar. Cada uma tem documentação própria, mantida como foi produzida por seu responsável. Esta página apenas as aproxima para consulta.

| Modelo | Abordagem | Dados usados | Documentação |
| --- | --- | --- | --- |
| RaiarNet | Rede escrita do zero em PyTorch, com contagem direta nos níveis N0, N1 e N2 | Vídeos da Raiar, anotados pela equipe | [Modelo de visão computacional](./visao-computacional/index.mdx) |
| Detector de aves (`chicken_yolo`) | YOLO11 pré-treinado (PoultryVision e COCO), com inferência, avaliação e integração | Vídeos da Raiar, com opção de dataset próprio | [Detecção de aves com YOLO](./deteccao-de-aves.md) |
| PIOFlow e YOLOPIO | Rede experimental em TensorFlow/Keras com pesos aleatórios e YOLO11n ajustado | Base pública PIO (Zenodo) | [Detecção e contagem de galinhas](./deteccao-e-contagem-de-galinhas.md) |

Os resultados quantitativos de cada página foram obtidos em dados e protocolos diferentes. Por isso, não são diretamente comparáveis entre si. Os termos técnicos estão no [glossário](../sprint-1/glossario.md).

A composição e as limitações dos conjuntos de dados estão resumidas em [Análise dos dados dos experimentos](./analise-dos-dados.md).
