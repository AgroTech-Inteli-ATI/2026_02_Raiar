---
title: Contagem de aves por nível e resultados do modelo
sidebar_label: Contagem e resultados
sidebar_position: 6
description: Adaptação da RaiarNet para contagem direta em N0, N1 e N2, filtragem temporal em vídeo, resultados no teste e próximos passos.
---

# Contagem de aves por nível e resultados do modelo

Nesta etapa, adaptamos o modelo de identificação construído do zero, a [RaiarNet](./modelo-identificacao-do-zero.md), para entregar o que o projeto precisa: a **contagem direta de aves em N0, N1 e N2** a cada instante, a partir de uma imagem ou de um vídeo `.mp4`. A regra de contagem segue a decisão registrada em [níveis e regra de contagem](./niveis-e-regra-de-contagem.md).

## Do detector à contagem por nível

Implementamos a adaptação em `src/models/counter.py`. Para cada quadro, a RaiarNet produz duas estimativas por nível:

- **contagem por detecção**: número de aves identificadas (picos do heatmap acima do limiar) cujo centro cai no polígono do nível;
- **contagem por densidade**: soma do mapa de densidade dentro do polígono do nível.

A detecção é precisa onde as aves estão separadas, mas perde aves aglomeradas ou atrás da grade, que não formam um pico nítido. A densidade capta essas aves, mas acumula ruído em áreas vazias. Por isso, desenvolvemos uma **fusão sensível à oclusão**: dividimos cada nível em janelas de 32 × 32 pixels e, em cada janela, somamos às detecções apenas o excedente da densidade que ultrapassa uma tolerância de 0,5 ave:

contagem da janela = detecções + máx(0, densidade − detecções − 0,5)

Escolhemos o tamanho da janela e a tolerância na validação, entre 18 combinações (`src/evaluation/count_analysis.py`). A versão sem tolerância superestimava a contagem, porque somava o ruído da densidade em todas as janelas.

Em nenhum momento calculamos N1 como total menos N0 e N2: cada nível é medido no próprio polígono, e as câmeras não são somadas.

## Estabilização temporal no vídeo

Em vídeo, a contagem de um quadro oscila quando aves se cruzam ou ficam momentaneamente ocultas. Aplicamos um **filtro de Kalman** unidimensional por nível [1], com modelo de nível constante: a variância do processo (0,5) representa aves entrando e saindo entre quadros, e a da medição (4,0), o ruído do detector. Uma média móvel exponencial também está disponível como alternativa.

O comando abaixo recebe um vídeo e grava o CSV com a contagem por quadro (bruta e filtrada), o resumo em JSON e o vídeo anotado:

```bash
cd src
python -m models.predict --source caminho/do/video.mp4 --weights ../models/trained/raiarnet-r1.pt --out ../outputs/c1 --stride-frames 3
```

A Figura 1 mostra a série de contagem ao longo do vídeo diurno, comparada com a anotação manual. A faixa destacada corresponde aos quadros de teste.

**Figura 1 – Contagem por nível ao longo do vídeo diurno, com e sem filtro de Kalman, comparada à anotação manual**

![Três gráficos de linha, um por nível, com a contagem por quadro em azul claro, a série filtrada pelo Kalman em azul escuro e os pontos vermelhos da anotação manual; a faixa entre 9 e 12 segundos marca o período de teste.](/img/visao-computacional/serie-contagem-video-dia.png)

Fonte: elaborado pelos autores (2026).

O filtro reduziu a variação média entre quadros processados consecutivos de 2,78 para 0,75 ave em N0 e de 0,94 para 0,26 ave em N1; a maior oscilação de N0 caiu de 10,9 para 2,5 aves. Em N0, a série acompanha a anotação no período de treino, mas fica abaixo dela no período de teste, o que discutimos a seguir.

## Resultados no teste

Avaliamos o modelo final nos 7 quadros de teste (6 diurnos e 1 noturno), que o modelo não viu no treino. O limiar de confiança (0,30) foi escolhido na validação. A Figura 2 mostra as predições em um quadro de teste diurno e no noturno.

**Figura 2 – Aves identificadas pela RaiarNet e contagem por nível em quadros de teste**

![Dois quadros da câmera C1, um diurno e um noturno, com caixas coloridas pelo nível (azul no piso, magenta no meio, laranja na plataforma) e um painel com a contagem de N0, N1 e N2.](/img/visao-computacional/predicoes-raiarnet-teste.png)

Fonte: elaborado pelos autores (2026).

### Identificação

| Métrica | Validação | Teste |
| --- | ---: | ---: |
| mAP@50 | 0,612 | 0,412 |
| mAP@50:95 | 0,265 | 0,143 |
| Precisão | 0,712 | 0,573 |
| Revocação | 0,680 | 0,504 |
| F1 | 0,696 | 0,536 |

### Contagem por nível

| Nível | MAE | RMSE | MAPE | Viés médio |
| --- | ---: | ---: | ---: | ---: |
| N0 · piso | 13,50 | 14,83 | 11,9% | −13,5 |
| N1 · meio | 0,62 | 0,97 | 2,9% | +0,6 |
| N2 · plataforma | 1,00 | 1,25 | 50,0% | +1,0 |
| Total da ROI | 11,88 | 13,15 | 8,7% | −11,9 |

A fusão sensível à oclusão reduziu o erro de N0 em relação às duas estimativas isoladas (MAE de 16,14 só com detecção e de 18,73 só com densidade) e o erro total de 14,57 para 11,88 aves. O modelo tem 1,16 milhão de parâmetros e processa **3,5 quadros por segundo** na CPU usada nos testes, incluindo pré-processamento, rede e decodificação. Esse desempenho atende a uma amostragem de um quadro a cada poucos segundos, mas ainda precisa ser medido na Raspberry Pi prevista nos [requisitos](../../sprint-1/requisitos.md).

Também testamos a inferência com espelhamento horizontal (TTA). Ela aumentou o mAP@50 para 0,441, mas piorou a contagem de N0 (MAE de 28,2), porque deslocou a calibração do limiar escolhido na validação. Por isso, o modelo final não usa TTA.

### Leitura dos resultados

- **N1 é o destaque**: no nível parcialmente oculto, que motivou a proibição da conta por diferença, o erro médio ficou abaixo de 1 ave (2,9%). A medição direta funcionou justamente onde a inferência por diferença acumularia os erros dos outros níveis.
- **O quadro noturno foi contado sem erro** em N0, N1 e N2.
- **N0 tem subcontagem de cerca de 12%** no teste diurno. O diagnóstico na validação mostrou que o modelo localiza 112 de 132 aves pelo centro, mas só 84 passam no critério de IoU ≥ 0,5. Logo, parte da perda de mAP vem do tamanho das caixas, e parte da subcontagem vem das aves pequenas e aglomeradas do fundo do corredor.
- **N2 tem MAPE alto por ter poucas aves**: com 0 a 2 aves no nível durante o dia, 1 ave a mais representa 50%.
- A queda entre validação e teste mostra que **9 quadros de treino são pouco**. Além disso, a contagem manual de N0 cresceu de 101 para 116 aves ao longo do vídeo, e parte desse crescimento pode refletir a anotação mais minuciosa dos últimos quadros.

## Limitações e próximos passos

Concluímos nesta entrega o modelo de identificação construído do zero e a sua adaptação para contagem por nível. Registramos o que ainda não foi feito, para orientar a próxima etapa:

1. **Comparação com o Chicken-YOLO** [2]: deixamos pronta a reimplementação do baseline em `src/baseline/` (YOLO11n com MSEIExtractor, CGDown e DHMSEAM, com 5,43 milhões de parâmetros e 8,5 GFLOPs, próximos dos 5,5 milhões e 9,0 GFLOPs do artigo) e o protocolo de benchmark em `src/evaluation/benchmark.py`, com mesmos quadros, ROI e escolha de limiar na validação. A comparação será feita em conjunto com o colega responsável pelo Chicken-YOLO. Um ponto de atenção: o baseline precisa receber número de passos de otimização equivalente ao da RaiarNet (cerca de 3.000), pois 250 épocas sobre 9 imagens correspondem a apenas 750 passos.
2. **Ablação do pré-processamento com o modelo**: o modelo final usa os quadros originais com a máscara de ROI. As medidas sem modelo estão em [tratamento de imagens](./tratamento-de-imagens.md); falta treinar a RaiarNet com cada pipeline de realce.
3. **Mais dados de treino**: densificar os rótulos por fluxo óptico (já implementado em `src/labeling/densify.py`, com 22 quadros extras) e anotar gravações de outros dias e idades do lote.
4. **Regressão de tamanho e recall no fundo de N0**: aumentar o peso das perdas de caixa e a resolução efetiva no fundo do corredor.
5. **Câmeras C2 e C3**: calibrar polígonos próprios e medir N1 e N2 por elas, sem somar câmeras.

## Referências {#referencias}

[1] KALMAN, R. E. A new approach to linear filtering and prediction problems. **Journal of Basic Engineering**, v. 82, n. 1, p. 35-45, 1960.

[2] PAN, F. *et al*. Occlusion-aware caged chicken detection based on multi-scale edge information extractor and context fusion. **Animals**, v. 15, n. 18, 2669, 2025. Disponível em: [https://doi.org/10.3390/ani15182669](https://doi.org/10.3390/ani15182669). Acesso em: 14 out. 2026.
