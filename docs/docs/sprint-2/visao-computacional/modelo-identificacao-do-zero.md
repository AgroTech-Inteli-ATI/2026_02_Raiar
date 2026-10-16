---
title: Modelo de identificação construído do zero
sidebar_label: Modelo do zero
sidebar_position: 5
description: Decisão de arquitetura, blocos, funções de perda e treino da RaiarNet, escrita do zero em PyTorch para identificar aves no Jump Start.
---

# Modelo de identificação construído do zero

Construímos o modelo de identificação de aves inteiramente em PyTorch, sem bibliotecas de detecção prontas e sem pesos pré-treinados. Chamamos esse modelo de **RaiarNet**. O código está em `src/raiarnet/models/`: blocos em `blocks.py`, rede em `raiarnet.py`, alvos e perdas em `losses.py` e decodificação em `decode.py`. A adaptação para contagem por nível e os resultados no teste estão em [contagem e resultados](./contagem-por-nivel.md).

## Decisão de paradigma

Avaliamos três paradigmas que poderíamos escrever do zero:

| Paradigma | Pontos fortes | Pontos fracos para o nosso caso |
| --- | --- | --- |
| Detector de estágio único estilo YOLO, com âncoras ou sem âncoras por caixa | Saída direta em caixas, ecossistema conhecido | Depende de NMS, que suprime aves aglomeradas cujas caixas se sobrepõem; muitos hiperparâmetros de atribuição de rótulos para poucos dados |
| Detector por pontos-chave (heatmap de centros) | Cada ave é um pico local; não precisa de NMS entre caixas; supervisão densa, adequada a poucos quadros anotados | Precisa de resolução alta na saída para separar centros próximos |
| Regressão de mapa de densidade | Conta bem multidões e oclusões parciais | Não identifica aves individualmente, o que impede mAP, F1 e auditoria visual |

Formulamos a hipótese de que um **detector híbrido de duas cabeças** combinaria o melhor dos dois últimos: o heatmap identifica cada ave, e a densidade recupera as aves parcialmente ocultas que não formam um pico nítido. Também consideramos que a anotação por pontos já fornece exatamente o alvo do heatmap. Por isso, escolhemos esse caminho. O estilo YOLO continua como referência externa: a reimplementação do Chicken-YOLO ficou pronta para a comparação da próxima etapa.

## Arquitetura da RaiarNet

A Figura 1 resume a arquitetura. A entrada é o quadro completo da C1 (1024 × 576 pixels), já realçado e mascarado fora da ROI.

**Figura 1 – Arquitetura da RaiarNet**

![Diagrama de blocos: quadro de entrada, backbone com quatro estágios SPD-Conv e CSP com atenção por coordenadas nos strides 2, 4, 8 e 16, pescoço BiFPN repetido duas vezes, cabeça de detecção e cabeça de densidade em stride 4 e saídas de aves identificadas e contagem por nível.](/img/visao-computacional/arquitetura-raiarnet.png)

Fonte: elaborado pelos autores (2026).

### Backbone

O backbone tem quatro estágios. Em cada um, a redução de resolução usa **SPD-Conv** [1]: o bloco reorganiza cada vizinhança 2 × 2 em canais e aplica uma convolução sem passo, em vez de descartar três de cada quatro pixels como faz a convolução com stride 2. Adotamos esse bloco porque as aves do fundo do corredor têm de 10 a 15 pixels, e qualquer perda espacial precoce apaga essas aves. Depois de cada redução, um **bloco CSP** (Cross Stage Partial) processa metade dos canais por gargalos residuais e concatena o resultado com a outra metade, o que mantém o custo baixo.

Nos estágios de stride 4, 8 e 16, incluímos **atenção por coordenadas** [2]. Ela codifica separadamente as direções horizontal e vertical; como as barras da grade das mesas têm orientação dominante, esperávamos que a atenção ajudasse a destacar aves atrás da grade em N1. Implementamos também o **CBAM** [3] como alternativa. O último estágio tem um **SPPF** (pooling espacial em pirâmide) para ampliar o campo receptivo.

### Pescoço

O pescoço é um **BiFPN** [4] com três níveis (strides 4, 8 e 16), repetido duas vezes. Cada fusão soma as entradas com pesos aprendidos e normalizados e aplica uma convolução separável em profundidade. O caminho descendente leva contexto semântico para a resolução alta, e o ascendente devolve detalhe aos níveis profundos. A saída de stride 4 (256 × 144 células) alimenta as cabeças: com ela, duas aves só se confundem se os centros estiverem a menos de 4 pixels.

### Cabeças

A **cabeça de detecção** prevê, em cada célula, a probabilidade de existir um centro de ave (heatmap), o tamanho da caixa em escala logarítmica e o deslocamento subcélula do centro, seguindo a formulação de detecção por pontos [5]. Na inferência, cada máximo local 3 × 3 acima do limiar é uma ave. Não aplicamos NMS entre caixas, o que evita suprimir aves aglomeradas. O Soft-NMS [6] ficou implementado como opção de pós-processamento.

A **cabeça de densidade** prevê um mapa não negativo cuja soma estima o número de aves [7][8]. Ela é usada na [adaptação para contagem](./contagem-por-nivel.md).

### Funções de perda

Implementamos todas as perdas em `src/raiarnet/models/losses.py`:

- **focal loss** modificada sobre o heatmap gaussiano [5][9], com raio da gaussiana calculado a partir do tamanho da ave;
- **L1** para o tamanho e o deslocamento nas células de centro;
- **Wise-IoU** [10] entre a caixa decodificada e a caixa de referência, que pondera o erro pela distância normalizada entre os centros;
- **erro quadrático** entre o mapa de densidade previsto e o alvo (uma gaussiana de massa 1 por ave) e uma perda de **consistência de contagem** entre a soma do mapa e o número de aves do recorte.

### Treino

Treinamos em CPU (AMD Ryzen 5 5600G), sem GPU, com recortes aleatórios de 320 × 320 pixels dos quadros de treino, escala aleatória entre 0,7 e 1,4, lote de 8, otimizador AdamW e taxa de aprendizado com ciclo único (pico de 0,002). As augmentations simulam as condições do aviário: **grade metálica sintética** sobreposta em faixas do recorte (oclusão do Jump Start), motion blur direcional, variação de exposição, matiz e saturação, conversão para tons de cinza (como nos quadros infravermelhos) e espelhamento horizontal. A cada 300 iterações, avaliamos na validação e guardamos o checkpoint com maior soma de mAP@50 e F1.

## Evolução do treino

Treinamos o modelo final por 3.000 iterações (cerca de 75 minutos em CPU). A Figura 2 mostra as perdas de treino e as métricas de validação ao longo das iterações. O melhor checkpoint, na iteração 2.700, foi salvo como `best.pt` na pasta da execução, por exemplo `src/raiarnet/runs/raiarnet/r1/best.pt`.

**Figura 2 – Perdas de treino e métricas de validação da RaiarNet ao longo das iterações**

![Dois gráficos de linha: à esquerda, a perda total e a perda focal do heatmap caindo ao longo de 3.000 iterações; à direita, mAP@50, mAP@50:95 e F1 na validação subindo até se estabilizarem em torno de 0,61, 0,26 e 0,69.](/img/visao-computacional/curvas-treino-raiarnet.png)

Fonte: elaborado pelos autores (2026).

| Iteração | mAP@50 | mAP@50:95 | Precisão | Revocação | F1 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | 0,149 | 0,029 | 0,239 | 0,366 | 0,289 |
| 600 | 0,359 | 0,098 | 0,525 | 0,418 | 0,465 |
| 1.200 | 0,576 | 0,192 | 0,710 | 0,608 | 0,655 |
| 2.700 | 0,612 | 0,265 | 0,712 | 0,680 | 0,696 |

As métricas de validação crescem rapidamente até 1.200 iterações e depois se estabilizam, enquanto a perda de treino continua caindo. Esse comportamento indica que, a partir daí, o limite é a quantidade de dados anotados, e não o tempo de treino. O modelo final tem 1,16 milhão de parâmetros.

## Referências {#referencias}

[1] SUNKARA, R.; LUO, T. No more strided convolutions or pooling: a new CNN building block for low-resolution images and small objects. In: EUROPEAN CONFERENCE ON MACHINE LEARNING AND PRINCIPLES AND PRACTICE OF KNOWLEDGE DISCOVERY IN DATABASES, 2022, Grenoble. **Proceedings** [...]. Cham: Springer, 2023. p. 443-459.

[2] HOU, Q.; ZHOU, D.; FENG, J. Coordinate attention for efficient mobile network design. In: IEEE/CVF CONFERENCE ON COMPUTER VISION AND PATTERN RECOGNITION, 2021, Nashville. **Proceedings** [...]. Piscataway: IEEE, 2021. p. 13713-13722.

[3] WOO, S. *et al*. CBAM: convolutional block attention module. In: EUROPEAN CONFERENCE ON COMPUTER VISION, 2018, Munich. **Proceedings** [...]. Cham: Springer, 2018. p. 3-19.

[4] TAN, M.; PANG, R.; LE, Q. V. EfficientDet: scalable and efficient object detection. In: IEEE/CVF CONFERENCE ON COMPUTER VISION AND PATTERN RECOGNITION, 2020, Seattle. **Proceedings** [...]. Piscataway: IEEE, 2020. p. 10781-10790.

[5] ZHOU, X.; WANG, D.; KRÄHENBÜHL, P. **Objects as points**. arXiv:1904.07850, 2019. Disponível em: [https://arxiv.org/abs/1904.07850](https://arxiv.org/abs/1904.07850). Acesso em: 14 out. 2026.

[6] BODLA, N. *et al*. Soft-NMS: improving object detection with one line of code. In: IEEE INTERNATIONAL CONFERENCE ON COMPUTER VISION, 2017, Venice. **Proceedings** [...]. Piscataway: IEEE, 2017. p. 5561-5569.

[7] LEMPITSKY, V.; ZISSERMAN, A. Learning to count objects in images. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS, 23., 2010, Vancouver. **Proceedings** [...]. Red Hook: Curran Associates, 2010. p. 1324-1332.

[8] LV, J. *et al*. DFCCNet: a dense flock of chickens counting network based on density map regression. **Animals**, v. 13, n. 23, 3729, 2023.

[9] LAW, H.; DENG, J. CornerNet: detecting objects as paired keypoints. In: EUROPEAN CONFERENCE ON COMPUTER VISION, 2018, Munich. **Proceedings** [...]. Cham: Springer, 2018. p. 734-750.

[10] TONG, Z. *et al*. **Wise-IoU**: bounding box regression loss with dynamic focusing mechanism. arXiv:2301.10051, 2023. Disponível em: [https://arxiv.org/abs/2301.10051](https://arxiv.org/abs/2301.10051). Acesso em: 14 out. 2026.
