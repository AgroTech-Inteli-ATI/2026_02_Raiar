---
title: Dados, anotação e partição do conjunto
sidebar_label: Dados e anotação
sidebar_position: 3
description: Vídeos usados, critérios de escopo, anotação assistida por pontos, caixas de referência e partição temporal sem vazamento.
---

# Dados, anotação e partição do conjunto

Esta página descreve como transformamos os vídeos `.mp4` recebidos da Raiar em um conjunto rotulado para treinar e avaliar os modelos. Como não havia nenhuma imagem anotada no início, a anotação foi a primeira etapa de engenharia do projeto. A regra de níveis aplicada aos rótulos está em [níveis e regra de contagem](./niveis-e-regra-de-contagem.md).

## Vídeos recebidos e escopo

Inspecionamos os quatro vídeos disponíveis, todos com 1024 × 576 pixels e cerca de 15 quadros por segundo.

| Vídeo | Duração | Conteúdo | Uso no projeto |
| --- | ---: | --- | --- |
| v3 (29/09, 09h48) | 11,9 s | Câmera C1 de dia, recria no Jump Start | Treino, validação e teste |
| v2 (29/09, 05h14) | 15,0 s | Câmera C1 à noite, infravermelho, aves empoleiradas | Treino, validação e teste |
| v1 (28/09, 19h56) | 11,0 s | Câmera CAM16 externa, vegetação, sem aves | Fora do escopo |
| v4 (07/10, 16h29) | 599,1 s | Câmera CAM16 em galpão de cria, pintinhos sem estrutura de níveis | Fora do escopo |

Os vídeos v2 e v3 mostram exatamente o mesmo enquadramento da C1, um de dia e outro à noite, e por isso compartilham os mesmos polígonos de nível. O vídeo v4 é o mesmo usado no [piloto com o detector pré-treinado](../../sprint-1/piloto-video-raiar.md): ele mostra pintinhos de poucos dias, com cerca de 5 pixels cada, espalhados por um galpão de cria sem plataformas. Como o objetivo é medir a ocupação de N0, N1 e N2 no Jump Start durante a recria, deixamos v1 e v4 fora do conjunto.

## Anotação assistida por pontos

Anotamos cada ave visível como **um ponto no centro do corpo**. Escolhemos pontos, e não caixas, porque as aves se sobrepõem com frequência e o ponto é o rótulo mais rápido e menos ambíguo em aglomerações [1]. Desenvolvemos uma ferramenta própria em `src/raiarnet/labeling/annotate.py` com três recursos:

1. **Blocos ampliados com grade de coordenadas**: o quadro é recortado em blocos de 160 a 300 pixels, ampliados de 2 a 4 vezes, com realce de exposição e saturação apenas para a revisão visual. A grade permite registrar a posição de cada ave em pixels do quadro original, como mostra a Figura 1.
2. **Propagação por fluxo óptico**: depois de anotar um quadro, os pontos são levados ao quadro seguinte pelo fluxo óptico denso de Farnebäck [2]. A revisão passa a consistir em corrigir aves que se moveram, entraram ou saíram, em vez de recomeçar do zero.
3. **Verificação reversa**: propagamos os pontos de um quadro posterior para trás e listamos as aves que não tinham correspondente. Com isso, encontramos 12 aves que tinham ficado sem rótulo nos dois primeiros quadros de treino.

**Figura 1 – Bloco ampliado usado na anotação, com grade de coordenadas e pontos marcados**

![Recorte ampliado do fundo do piso, com aves marrons aglomeradas, linhas de grade numeradas a cada 32 pixels e pontos vermelhos sobre o centro de cada ave anotada.](/img/visao-computacional/anotacao-bloco-ampliado.png)

Fonte: elaborado pelos autores (2026).

Testamos também um detector de vocabulário aberto (OWLv2) para propor caixas automaticamente. No quadro diurno, ele gerou centenas de caixas sobre grade, maravalha e grupos de aves, sem separar indivíduos, e por isso o descartamos como fonte de rótulos.

## Caixas de referência

As métricas de detecção (mAP, precisão e revocação) e o treino do baseline exigem caixas. Convertemos cada ponto em uma caixa em duas etapas, implementadas em `src/raiarnet/labeling/boxes.py`:

1. **Prior de perspectiva**: medimos manualmente o tamanho de 34 aves isoladas em N0, N1 e N2 e interpolamos o tamanho esperado em qualquer posição do quadro. Uma ave no primeiro plano mede cerca de 50 × 45 pixels; no fundo do corredor, cerca de 12 × 11 pixels.
2. **Refinamento com Segment Anything (SAM)** [3]: usamos o ponto como prompt positivo e os quatro vizinhos mais próximos como prompts negativos. A caixa do SAM só é aceita quando tem entre 0,6 e 1,6 vez o tamanho do prior e contém o ponto perto do centro. Nos demais casos, mantemos a caixa do prior.

O SAM foi usado apenas como ferramenta de rotulagem; ele não faz parte de nenhum dos modelos avaliados. Em média, 54% das caixas vieram do SAM e 46% do prior. A Figura 2 mostra os pontos atribuídos a cada nível e as caixas resultantes em um quadro de teste.

**Figura 2 – Pontos anotados por nível e caixas de referência em um quadro de teste**

![À esquerda, quadro diurno da C1 com pontos azuis no piso, magenta no nível intermediário e laranja na plataforma; à direita, o mesmo quadro com caixas verdes aceitas do SAM e caixas amarelas geradas pelo prior de perspectiva.](/img/visao-computacional/anotacao-pontos-e-caixas.png)

Fonte: elaborado pelos autores (2026).

Como parte das caixas vem de um prior de tamanho, o **mAP@50:95** mede também o quanto cada modelo reproduz esse prior. Por isso, damos mais peso ao mAP@50, ao F1 e às métricas de contagem, que dependem da localização da ave, e não do ajuste fino da caixa.

## Partição temporal

Separamos os quadros por instante, e não aleatoriamente, para que o teste não contenha quadros quase idênticos aos de treino. A validação fica entre treino e teste e é usada apenas para escolher o limiar de confiança e o melhor checkpoint.

| Partição | Quadros | Aves anotadas | Aves na ROI | Conteúdo |
| --- | ---: | ---: | ---: | --- |
| Treino | 9 | 980 | 928 | v3 de 0 a 6 s (7 quadros) e v2 em 0 e 4,5 s |
| Validação | 2 | 178 | 152 | v3 em 7,5 s e v2 em 7,5 s |
| Teste | 7 | 867 | 837 | v3 de 9 a 11,5 s (6 quadros) e v2 em 13,5 s |

As partições estão em `src/raiarnet/configs/dataset-splits.json`. Os quadros e anotações ficam em `data/`, fora do Git, como os demais dados do projeto.

Reconhecemos o principal limite deste conjunto: ele vem de uma única câmera, em dois horários de um mesmo dia, e o teste cobre poucos segundos de vídeo. Os resultados medem o desempenho neste enquadramento e devem ser confirmados com gravações de outros dias e idades do lote antes de qualquer uso operacional.

## Referências {#referencias}

[1] LEMPITSKY, V.; ZISSERMAN, A. Learning to count objects in images. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS, 23., 2010, Vancouver. **Proceedings** [...]. Red Hook: Curran Associates, 2010. p. 1324-1332.

[2] FARNEBÄCK, G. Two-frame motion estimation based on polynomial expansion. In: SCANDINAVIAN CONFERENCE ON IMAGE ANALYSIS, 13., 2003, Halmstad. **Proceedings** [...]. Berlin: Springer, 2003. p. 363-370.

[3] KIRILLOV, A. *et al*. Segment anything. In: IEEE/CVF INTERNATIONAL CONFERENCE ON COMPUTER VISION, 2023, Paris. **Proceedings** [...]. Piscataway: IEEE, 2023. p. 4015-4026.
