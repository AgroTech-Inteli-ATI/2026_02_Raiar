---
title: Análise dos dados dos experimentos
sidebar_label: Análise dos dados
sidebar_position: 2
description: Perfil, qualidade, cobertura e limitações dos datasets usados nos modelos de visão computacional da Sprint 2.
---

# Análise dos dados dos experimentos

Esta página consolida a análise exploratória dos dados usados nos três experimentos de visão computacional documentados na Sprint 2. Ela complementa o [dicionário de dados e a proposta de coleta](../sprint-1/dicionario-de-dados.md), separando a amostra anotada da câmera C1 usada pela RaiarNet da base pública PIO usada nos experimentos PIOFlow e YOLOPIO. Os dados brutos, quadros extraídos, rótulos e pesos são mantidos localmente e não fazem parte do repositório.

## Escopo observado

Para treinar e avaliar a RaiarNet, foram inspecionados quatro vídeos recebidos, todos com resolução de 1024 × 576 pixels e aproximadamente 15 quadros por segundo. Somente dois são compatíveis com o objetivo de medir a ocupação dos níveis do Jump Start: as gravações diurna e noturna da câmera C1, feitas em 29 de setembro de 2026. O vídeo externo sem aves e o vídeo de pintinhos em um galpão sem plataformas foram excluídos porque não representam esse cenário.

Os dois vídeos selecionados compartilham o enquadramento e os polígonos de interesse. A amostra anotada contém 18 quadros: nove para treino, dois para validação e sete para teste. A tabela registra as quantidades documentadas por partição. Como imagens e anotações são mantidas fora do Git, esses totais não podem ser recalculados apenas com os arquivos versionados.

| Partição | Quadros | Aves anotadas | Aves na ROI | Observação |
| --- | ---: | ---: | ---: | --- |
| Treino | 9 | 980 | 928 | Sete quadros diurnos entre 0 e 6 s e dois noturnos entre 0 e 4,5 s. |
| Validação | 2 | 178 | 152 | Um quadro diurno e um noturno em 7,5 s; usada para selecionar limiar e checkpoint. |
| Teste | 7 | 867 | 837 | Seis quadros diurnos entre 9 e 11,5 s e um noturno em 13,5 s. |

As quantidades por partição estão registradas na documentação do conjunto; a configuração `src/raiarnet/configs/dataset-splits.json` identifica os quadros de cada partição. A organização é temporal: quadros próximos não são distribuídos aleatoriamente entre treino e teste, reduzindo o risco de avaliar em imagens quase duplicadas. A validação fica entre os intervalos de treino e teste.

## Base pública PIO

Os experimentos PIOFlow e YOLOPIO usam outra fonte: a versão 1 do dataset público PIO, com imagens de frangos de corte em granjas comerciais. A cópia local contém 1.035 imagens de treino e 452 de validação. O leitor do PIOFlow encontrou 253.426 caixas válidas no treino e 73.857 na validação; cinco rótulos com largura ou altura zero foram descartados. Não há uma partição de teste separada nesses experimentos.

Os resultados quantitativos publicados para esses dois experimentos são calculados na validação PIO. As imagens da Raiar usadas nos notebooks servem para inspeção visual e não têm contagens de referência anotadas para essa avaliação. Assim, os resultados PIO não medem desempenho nas câmeras da Raiar e não podem ser comparados diretamente com os resultados de teste da RaiarNet. O protocolo, as métricas e as limitações estão detalhados em [Detecção e contagem de galinhas](./deteccao-e-contagem-de-galinhas.md).

## Qualidade visual e diferenças entre níveis

Os quadros apresentam condições distintas de iluminação, escala e oclusão. N0 tem aves menores e mais aglomeradas sobre a maravalha; N1 fica parcialmente encoberto pela estrutura; N2 tem menos aves e maior contraste. À noite, a câmera usa infravermelho. Essas diferenças afetam a facilidade de distinguir cada ave e tornam necessário olhar as métricas por nível, em vez de depender apenas de uma média geral.

O estudo de pré-processamento comparou dez pipelines nos 11 quadros de treino e validação, considerando 1.077 aves anotadas. Na imagem original, a separabilidade de luminância entre ave e fundo (d de Cohen) foi 0,44 em N0, 1,57 em N1 e 1,28 em N2. Isso confirma que o piso é o cenário visualmente mais difícil. O CLAHE em HSV elevou a medida de N0 para 0,51; o filtro guiado chegou a 0,61, mas reduziu a nitidez medida de 2.192 para 942. O MSRCR diminuiu a separabilidade nos três níveis.

Esses indicadores descrevem contraste e textura, não desempenho de detecção. Como o ganho visual não garante ganho no modelo e o filtro guiado remove parte da textura, a RaiarNet final foi treinada com os quadros originais e a máscara da ROI. A comparação quantitativa e a interpretação completa estão em [tratamento de imagens](./visao-computacional/tratamento-de-imagens.md); os valores originais estão em `src/raiarnet/reports/preprocessamento.json`.

## Preparação dos rótulos

Cada ave foi marcada inicialmente por um ponto no centro do corpo. A anotação assistida por fluxo óptico foi revisada manualmente; a verificação reversa encontrou 12 aves omitidas em quadros iniciais. Para as métricas de detecção, os pontos foram convertidos em caixas usando tamanho estimado por perspectiva e, quando a proposta do Segment Anything atendia aos critérios de tamanho e posição, refinamento automático. Assim, as caixas são referências aproximadas: cerca de 54% foram refinadas pelo Segment Anything e 46% mantiveram o prior de perspectiva. Essa origem limita a interpretação de métricas que dependem do ajuste exato das caixas, sobretudo mAP em vários limiares de IoU.

O fluxo de dados, a regra de anotação, as caixas e os detalhes da separação temporal estão em [dados, anotação e partição](./visao-computacional/dados-e-anotacao.md). A regra geométrica para associar cada centro a N0, N1 ou N2 está em [níveis e regra de contagem](./visao-computacional/niveis-e-regra-de-contagem.md).

## O que os resultados permitem concluir

No teste da RaiarNet, composto por sete quadros da mesma câmera e de duas gravações do mesmo dia, o modelo obteve F1 de 0,536 e mAP@50 de 0,412 para identificação. Na contagem fundida, o erro absoluto médio foi de 0,62 ave em N1 (2,9%), 1,00 ave em N2 e 13,50 aves em N0 (11,9%). O erro médio do total da ROI foi de 11,88 aves (8,7%). O desempenho mais fraco em N0 é coerente com o menor contraste e com a concentração de aves pequenas e aglomeradas no fundo do piso.

Esses resultados caracterizam um protótipo no enquadramento C1. O conjunto não contém diversidade suficiente para estimar desempenho em outros dias, lotes, idades ou câmeras: há apenas uma câmera, duas condições de iluminação de um mesmo dia e poucos instantes de teste. Portanto, os números não demonstram generalização nem validam uso operacional. A tabela completa, a comparação entre detecção, densidade e fusão e as limitações estão em [contagem e resultados](./visao-computacional/contagem-por-nivel.md).

## Próximos dados necessários

Para uma validação mais representativa, o próximo conjunto deve incluir gravações de outros dias e idades acordadas com a Raiar, preservando câmera, data, horário e condição de iluminação no manifesto. A divisão deve manter sessões ou dias inteiros fora do treino, e as contagens de referência precisam passar por revisão técnica. Câmeras adicionais exigem calibração própria dos níveis. O plano de amostragem e os metadados a solicitar estão no [dicionário de dados](../sprint-1/dicionario-de-dados.md).
