---
title: Tratamento de imagens do aviário
sidebar_label: Tratamento de imagens
sidebar_position: 4
description: Hipóteses ópticas, técnicas de realce testadas, máscaras por nível e estudo de ablação do pré-processamento.
---

# Tratamento de imagens do aviário

Desenvolvemos o pipeline de tratamento de imagens em `src/preprocessing/` a partir dos quadros reais da câmera C1. Esta página registra as hipóteses que formulamos sobre os problemas ópticos do aviário, as técnicas que implementamos para cada uma, as medidas sem modelo e a decisão sobre o pipeline usado pela [RaiarNet](./modelo-identificacao-do-zero.md).

## Hipóteses sobre os problemas ópticos

Ao inspecionar os quadros diurnos e noturnos, levantamos cinco hipóteses de degradação, cada uma ligada a um nível:

| Hipótese | Onde aparece | Efeito esperado no modelo | Técnica candidata |
| --- | --- | --- | --- |
| Sombra intensa sob a plataforma | N1 | Aves escuras com pouco detalhe de textura | Correção gama adaptativa e Retinex multiescala |
| Baixo contraste entre plumagem marrom e maravalha | N0 | Aves do fundo do piso confundidas com a cama | CLAHE e destaque cromático da plumagem |
| Oclusão pela grade metálica | N1 e N2 | Bordas da grade competem com o contorno das aves | Filtros que preservam bordas e augmentation de grade |
| Iluminação lateral estourada | Fundo do corredor | Perda de detalhe nas áreas claras | CLAHE com limite de recorte e gama maior que 1 nas áreas claras |
| Motion blur e compressão do vídeo | Todos | Aves em movimento sem contorno nítido | Nitidez leve e augmentation de borrão |

## Técnicas implementadas

Implementamos cada técnica como uma função independente em `src/preprocessing/enhance.py`, e as combinações ficam nomeadas em `src/preprocessing/pipeline.py`, o que permite reproduzir qualquer configuração do estudo:

- **CLAHE** (equalização adaptativa de histograma com limite de contraste) [1], aplicada à luminância L\* do espaço LAB ou ao canal V do HSV, com limite de recorte 2,0 e blocos de 8 × 8;
- **MSRCR** (Retinex multiescala com restauração de cor) [2], com escalas gaussianas de 15, 80 e 200 pixels;
- **correção gama adaptativa** [3]: o expoente varia com a luminância local, e fica menor que 1 nas sombras de N1 e maior que 1 nas áreas estouradas;
- **filtro bilateral** [4] e **filtro guiado** [5], que suavizam a textura da maravalha e o ruído de compressão sem apagar o contorno das aves;
- **destaque cromático**: aumenta a saturação apenas nas matizes marrom-avermelhadas da plumagem, já que a grade galvanizada e a maravalha são pouco saturadas;
- **mascaramento por ROI**: tudo o que está fora dos polígonos de N0, N1 e N2, dilatados em 16 pixels, é preenchido com cinza neutro, como descrito em [níveis e regra de contagem](./niveis-e-regra-de-contagem.md).

A Figura 1 compara o quadro original com os principais realces em recortes de cada nível no período diurno, e a Figura 2 faz o mesmo para o período noturno.

**Figura 1 – Comparação do tratamento de imagem nos níveis N0, N1 e N2 em um quadro diurno**

![Quadro comparativo com cinco linhas (original, CLAHE em LAB, MSRCR, gama adaptativa e a combinação gama, CLAHE, filtro guiado e destaque cromático) e três colunas com recortes do piso, do nível intermediário sob a mesa e da plataforma.](/img/visao-computacional/comparacao-pre-processamento-dia.png)

Fonte: elaborado pelos autores (2026).

**Figura 2 – Comparação do tratamento de imagem nos níveis N0, N1 e N2 em um quadro noturno**

![Mesmo quadro comparativo da figura anterior aplicado a um quadro noturno em infravermelho, com aves claras sobre a plataforma e o piso escuro.](/img/visao-computacional/comparacao-pre-processamento-noite.png)

Fonte: elaborado pelos autores (2026).

## Medidas sem modelo

Antes de treinar, medimos o efeito de cada técnica com indicadores que não dependem do detector. Para cada ave anotada, comparamos o interior da caixa (metade central) com um anel de fundo ao redor, sem outras aves, dentro do mesmo nível. Calculamos o **d de Cohen** na luminância L\* (diferença das médias dividida pelo desvio padrão combinado) e a distância média no plano cromático a\*b\*. Usamos as 1.077 aves dos quadros de treino e validação (840 em N0, 167 em N1 e 70 em N2).

| Pipeline | d L\* N0 | d L\* N1 | d L\* N2 | Δa\*b\* N0 | Δa\*b\* N1 | Δa\*b\* N2 | Nitidez N0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 0,44 | 1,57 | 1,28 | 3,3 | 7,7 | 10,2 | 2.192 |
| CLAHE (LAB) | 0,49 | 1,60 | 1,27 | 3,3 | 7,6 | 10,1 | 5.380 |
| CLAHE (HSV) | 0,51 | 1,58 | 1,29 | 3,7 | 8,1 | 10,3 | 5.212 |
| MSRCR | 0,41 | 1,38 | 1,08 | 2,7 | 5,5 | 6,2 | 2.496 |
| Gama adaptativa | 0,44 | 1,55 | 1,15 | 3,3 | 7,7 | 10,2 | 2.204 |
| Bilateral | 0,48 | 1,73 | 1,37 | 3,3 | 7,6 | 10,1 | 1.881 |
| Filtro guiado | 0,61 | 2,01 | 1,60 | 3,1 | 7,5 | 9,8 | 942 |
| Destaque cromático | 0,43 | 1,63 | 1,38 | 4,8 | 11,0 | 13,4 | 2.195 |
| Gama + CLAHE | 0,48 | 1,52 | 1,17 | 3,3 | 7,6 | 10,1 | 5.666 |
| Gama + CLAHE + guiado + cromático | 0,56 | 1,93 | 1,41 | 4,7 | 10,7 | 13,0 | 3.446 |

Tiramos três leituras dessa tabela. Primeiro, **N0 é o nível mais difícil**: a separabilidade da ave em relação à maravalha (d = 0,44) é três vezes menor que em N1 e N2, o que confirma a hipótese do baixo contraste no piso. Segundo, o MSRCR, apesar de clarear as sombras visualmente, **reduziu** a separabilidade em todos os níveis, porque equaliza também o fundo e desbota a cor da plumagem. Terceiro, o filtro guiado tem o maior d, mas parte do ganho vem da redução da variância (a nitidez cai para menos da metade), e uma rede convolucional pode perder textura útil com isso. Como essas medidas não garantem ganho no detector, adotamos no modelo final os quadros **originais com a máscara de ROI**, que preservam a textura da plumagem, e deixamos os realces como etapas configuráveis do pipeline.

## Próximo passo: ablação com o modelo

O estudo de ablação com o detector, em que a RaiarNet é treinada com cada pipeline nas mesmas condições, ficou preparado, mas não foi executado nesta entrega por falta de tempo de processamento (cada treino leva de 15 a 75 minutos em CPU). Os pipelines candidatos são o original, CLAHE em LAB, MSRCR, gama adaptativa, filtro guiado, destaque cromático e a combinação de gama, CLAHE, filtro guiado e destaque cromático, com uma segunda semente do original para estimar a variação entre treinos. O comando de treino aceita o pipeline como parâmetro:

```bash
cd src
python -m training.train_raiarnet --name abl-clahe --pipeline clahe-lab --iters 600
```

## Referências {#referencias}

[1] ZUIDERVELD, K. Contrast limited adaptive histogram equalization. In: HECKBERT, P. S. (ed.). **Graphics gems IV**. San Diego: Academic Press, 1994. p. 474-485.

[2] JOBSON, D. J.; RAHMAN, Z.; WOODELL, G. A. A multiscale retinex for bridging the gap between color images and the human observation of scenes. **IEEE Transactions on Image Processing**, v. 6, n. 7, p. 965-976, 1997.

[3] HUANG, S.-C.; CHENG, F.-C.; CHIU, Y.-S. Efficient contrast enhancement using adaptive gamma correction with weighting distribution. **IEEE Transactions on Image Processing**, v. 22, n. 3, p. 1032-1041, 2013.

[4] TOMASI, C.; MANDUCHI, R. Bilateral filtering for gray and color images. In: INTERNATIONAL CONFERENCE ON COMPUTER VISION, 6., 1998, Bombay. **Proceedings** [...]. Piscataway: IEEE, 1998. p. 839-846.

[5] HE, K.; SUN, J.; TANG, X. Guided image filtering. **IEEE Transactions on Pattern Analysis and Machine Intelligence**, v. 35, n. 6, p. 1397-1409, 2013.
