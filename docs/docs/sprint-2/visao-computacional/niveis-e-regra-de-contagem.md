---
title: Níveis do Jump Start e regra de contagem
sidebar_label: Níveis e regra de contagem
sidebar_position: 2
description: Como delimitamos N0, N1 e N2 na câmera C1 e por que medimos cada nível diretamente, sem inferir N1 por diferença.
---

# Níveis do Jump Start e regra de contagem

Antes de escrever qualquer linha do modelo, precisamos decidir **o que exatamente contar** em cada quadro. Esta página registra a leitura que fizemos da geometria do aviário, o esclarecimento técnico validado com a Raiar e a regra de contagem que adotamos no MVP. Os termos técnicos estão no [glossário](../../sprint-1/glossario.md).

## Geometria observada pela câmera C1

A câmera **C1** é a câmera lateral superior que gerou os vídeos `.mp4` recebidos (identificada como CAM 3 na sobreposição da imagem). Ela enxerga, em perspectiva, uma seção do corredor do **Jump Start** [1]: a plataforma de grade metálica à esquerda, a borda das mesas com aves sob ela e o piso de maravalha à direita, até a divisória do fundo. Os dois vídeos diurnos e noturnos de 29 de setembro mostram o mesmo enquadramento, o que confirmamos sobrepondo pilares e bordas das mesas nos dois horários.

A partir dessa leitura, definimos três níveis observáveis:

| Nível | Nome | O que a C1 enxerga | Confiabilidade da observação |
| --- | --- | --- | --- |
| N0 | Piso | Cama de maravalha entre a borda das mesas e a cortina lateral | Alta no primeiro plano; aves pequenas e aglomeradas no fundo |
| N1 | Meio / parcialmente oculto | Faixa sob a borda da plataforma, onde as aves usam o patamar intermediário | Média: sombra intensa e oclusão pelas barras e pela própria mesa |
| N2 | Plataforma | Superfície de grade da plataforma superior | Média de dia; à noite, parte das aves empoleiradas na borda distante sai do campo útil |

A Figura 1 mostra os polígonos de cada nível sobre um quadro diurno e um noturno, além da máscara aplicada antes da inferência.

**Figura 1 – Regiões de interesse de N0, N1 e N2 na câmera C1 e máscara aplicada fora dos níveis**

![Quatro painéis: quadro diurno e quadro noturno da câmera C1 com os polígonos de N0 em azul, N1 em magenta e N2 em laranja; quadro diurno com tudo o que está fora dos níveis preenchido em cinza; legenda das cores.](/img/visao-computacional/roi-niveis-c1.png)

Fonte: elaborado pelos autores (2026).

## Divisória verde fixa e região azul móvel

Nas imagens de referência das câmeras que recebemos, duas marcações sobre o quadro real da C1 orientam a delimitação das zonas, e o parceiro esclareceu o significado de cada uma.

A **divisória verde**, no fundo do corredor, corresponde a uma divisória física fixa da seção. Por isso, usamos essa divisória como limite geométrico fixo da **região de interesse (ROI)**: os polígonos de N0, N1 e N2 terminam nela, e nenhuma ave além dela é contada pela C1. No arquivo `configs/cameras/c1-jump-start.json`, o segmento `divisoria` registra essa referência.

A **região azul**, no alto à esquerda do quadro, atrás da plataforma, não é uma divisória física fixa nem uma área fechada. Ali ficam as estruturas e mesas laterais e centrais, em diferentes níveis, cuja configuração e posição a equipe da Raiar altera ao longo da recria, conforme a idade das aves e o manejo adotado para estimular a movimentação vertical e a ocupação progressiva. As aves se deslocam horizontalmente entre essas áreas e a seção que observamos.

Tiramos duas consequências práticas desse esclarecimento. Primeiro, a região azul fica **fora** dos polígonos da C1: as aves vistas ali, ao fundo e atrás de pilares e barras, não pertencem a N0, N1 ou N2 desta câmera. Segundo, a borda entre N2 e a região azul é uma **linha de medição**, e não uma parede: aves a atravessam o tempo todo. Por isso, tratamos os polígonos de N1 e N2 como **calibração versionada do enquadramento atual**. Quando as mesas mudam de altura ou de posição, os polígonos precisam ser revisados, enquanto o limite do fundo continua o mesmo.

Nas referências iniciais, a plataforma chegou a ser chamada de N1 e a faixa sob a borda, de "área oclusa". Adotamos a nomenclatura consolidada no conceito de três câmeras: N0 para o piso, N1 para o meio parcialmente oculto e N2 para a plataforma.

## Por que descartamos N1 = total da seção − N0 − N2

Uma alternativa tentadora seria contar o piso e a plataforma e obter o nível intermediário por diferença, usando um total conhecido da seção. Identificamos dois motivos para proibir essa conta no projeto.

O primeiro é que **o total da seção não é estável**. Como a região azul é aberta, as aves entram e saem horizontalmente da área enquadrada a todo momento. Nos 12 segundos de vídeo diurno que anotamos, a contagem de aves visíveis na ROI variou de 122 a 138, sem que nenhuma ave fosse adicionada ao lote; parte dessa variação vem de aves que atravessam a borda com a região azul e o fundo do corredor. Qualquer "total" fixo usado como referência estaria errado na maior parte dos instantes.

O segundo é que **os erros se acumulam no nível intermediário**. Se o total fosse 140 e o modelo deixasse de ver 10 aves ocultas no piso e 5 na plataforma, a diferença atribuiria essas 15 aves a N1. Em uma seção com cerca de 20 aves visíveis em N1, isso inflaria a contagem do nível em 75%, justamente no nível que mais interessa para avaliar a ocupação vertical. A conta por diferença transforma toda oclusão de N0 e N2 em ocupação fictícia de N1.

Por isso, medimos **cada nível diretamente**: uma ave só entra na contagem de N1 se o modelo a identificar dentro do polígono de N1.

## Regra adotada no MVP

Implementamos a regra em `src/preprocessing/roi.py` e `src/models/counter.py`:

1. Cada ave identificada é atribuída a um único nível pelo **centro do corpo** (o mesmo ponto que anotamos). Escolhemos o centro, e não a base da caixa, porque os pés ficam ocultos na maioria das aves aglomeradas ou atrás das barras.
2. Aves com centro fora dos três polígonos não são contadas pela C1.
3. Cada câmera responde apenas pelos níveis que observa com confiabilidade e gera **uma contagem por nível e instante**. As contagens de câmeras diferentes **não são somadas**, para não duplicar aves em áreas sobrepostas.
4. Os conceitos de câmera **C2** (vista inferior oposta do nível intermediário) e **C3** (vista superior sobre a plataforma) seguem a mesma regra: cada uma terá polígonos próprios e será responsável pelo nível que enxerga melhor, sem soma com a C1.

Essa regra tem uma consequência que documentamos com transparência. À noite, um grupo grande de aves se empoleira junto à borda distante da plataforma, na transição para a região azul, e o centro do corpo delas fica acima da linha de N2 vista pela C1. Nos quadros noturnos anotados, 26 das 47 aves visíveis estavam nessa situação e ficaram fora da ROI. Essa é uma limitação de ângulo, e não do modelo: ela reforça a necessidade da câmera C3 sobre a plataforma para medir N2 à noite.

## Referências {#referencias}

[1] VENCOMATIC GROUP. **Jump Start**. Disponível em: [https://www.vencomaticgroup.com/layers/jump-start](https://www.vencomaticgroup.com/layers/jump-start). Acesso em: 14 out. 2026.
