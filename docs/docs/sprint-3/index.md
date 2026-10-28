---
title: Nó de borda e containers
sidebar_label: Visão geral da Sprint 3
sidebar_position: 0
description: Preparação do Raspberry Pi 4 como nó de borda e material para containerizar os modelos da Raiar.
---

# Nó de borda e containers

Na Sprint 3, a equipe preparou o nó de borda, o pequeno computador que executará os modelos no aviário, e reuniu o material para containerizar os modelos da Sprint 2. Um container é um pacote que leva o programa e tudo o que ele precisa, para funcionar igual em qualquer equipamento. O objetivo é que os modelos rodem no Raspberry Pi e enviem seus resultados ao backend. A origem das imagens segue a [arquitetura preliminar](../sprint-2/arquitetura-preliminar.md), cujo acesso ao servidor de câmeras ainda será validado com a Raiar. Os termos técnicos estão no [glossário](../sprint-1/glossario.md).

| Entrega | O que contém |
| --- | --- |
| [Nó de borda no Raspberry Pi](./provisionamento-raspberry-pi.md) | Arch Linux ARM `aarch64` ultra-leve no cartão SD, otimização de RAM, Docker e captura de câmera. |
| [Containers no nó de borda](./integracao-containers-no-no-de-borda.md) | Arquitetura, orçamento de recursos, entrega e validação dos containers. |
| [Exemplo de containers](./exemplo-containers/index.md) | Guia de Docker, exercícios e os exemplos executáveis para o colega. |

Os scripts de provisionamento estão em `src/edge/`.
