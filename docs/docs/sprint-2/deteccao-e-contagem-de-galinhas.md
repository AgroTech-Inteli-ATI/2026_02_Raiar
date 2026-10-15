---
title: Detecção e contagem de galinhas em imagens
sidebar_label: Detector PIOFlow e YOLOPIO
sidebar_position: 3
description: Dados, experimentos e resultados dos detectores PIOFlow e YOLOPIO desenvolvidos na Sprint 2.
---

# Detecção e contagem de galinhas em imagens

Este trabalho investiga a identificação de galinhas em quadros de vídeo por meio de caixas delimitadoras. A quantidade de caixas aceitas em cada quadro também é usada como estimativa da **contagem de aves visíveis naquela imagem**. Foram desenvolvidos dois experimentos: o PIOFlow, implementado em TensorFlow/Keras com pesos iniciados aleatoriamente, e o YOLOPIO, que ajusta um YOLO11n com pesos iniciais pré-treinados. Os três notebooks e os arquivos usados pelos experimentos estão organizados em `src/modelos_PIO/`.

Os resultados quantitativos desta página vêm da divisão de validação da base PIO. Os vídeos da Raiar foram usados para inspeção visual das previsões, pois seus quadros ainda não têm anotações de referência. Portanto, as métricas da PIO não medem o desempenho nas câmeras da Raiar.

## Dados e preparação das imagens

### Base PIO

A base **PIO** (*A Large-Scale Dataset for Broiler Chicken Detection under Real Poultry Farming Conditions*) é um conjunto público de imagens de frangos de corte em granjas comerciais do Panamá, anotado em formato YOLO e disponibilizado sob licença CC BY 4.0 [1]. O dataset foi obtido em [https://zenodo.org/records/16686320](https://zenodo.org/records/16686320).

A base PIO disponível localmente contém imagens e arquivos de rótulos nas divisões `train` e `val`. Cada linha de rótulo segue o formato YOLO: classe, centro horizontal, centro vertical, largura e altura da caixa, com coordenadas normalizadas entre 0 e 1. A única classe utilizada é `0`, correspondente a **galinha**.

| Divisão | Imagens | Caixas válidas lidas pelo PIOFlow |
| --- | ---: | ---: |
| Treino | 1.035 | 253.426 |
| Validação | 452 | 73.857 |

Os notebooks verificam a presença dos arquivos e o formato dos rótulos antes de usar a base. Foram encontradas cinco anotações com largura ou altura igual a zero, três no treino e duas na validação; elas são informadas e desconsideradas nas leituras de caixas válidas. A avaliação apresentada adiante usa as 452 imagens de `val`. Não há, neste experimento, uma avaliação quantitativa em uma divisão de teste separada.

### Vídeos da Raiar

O notebook `analise_imagens.ipynb` serve para preparar e examinar visualmente os quadros dos vídeos da Raiar antes de aplicá-los aos detectores. Ele lê `camera-raiar.mp4`, com aproximadamente 599 segundos, e `video-galinhas2.mp4`, com 15 segundos, e extrai um quadro a cada dois segundos, preservando os frames já existentes. A extração registrada no notebook produziu 300 quadros do primeiro vídeo e 8 do segundo, em pastas distintas.

Depois da extração, o notebook permite visualizar quadros de diferentes instantes, examinar um recorte e comparar o quadro completo com o recorte ajustados para uma entrada de 640 × 640 pixels, mantendo a proporção e preenchendo as bordas. Essa análise ajudou a observar a diferença de enquadramento e a dificuldade de distinguir aves pequenas em parte das imagens.

## Organização dos experimentos

| Local em `src/modelos_PIO/` | Conteúdo |
| --- | --- |
| `analise_imagens.ipynb` | Extração e inspeção dos frames dos dois vídeos da Raiar. |
| `PIOFlow.ipynb` | Construção, treinamento e avaliação do detector em TensorFlow/Keras. |
| `YOLOPIO.ipynb` | Treinamento, validação e inferência com YOLO11n por meio do Ultralytics. |
| `midias/PIO/data/` | Imagens e rótulos da base PIO. |
| `midias/raiar/camera-raiar/` e `midias/raiar/video-galinhas2/` | Cada vídeo e seus respectivos frames. |
| `pesos_iniciais/yolo11n.pt` | Pesos pré-treinados usados no início do experimento YOLOPIO. |
| `resultados/detector_pio.weights.h5` | Pesos salvos do PIOFlow. |
| `resultados/treinos_yolo11/pio_yolo11n/` | Checkpoints, histórico por época e gráficos do treinamento YOLOPIO. |

As mídias, os pesos e os resultados do treinamento permanecem locais e fora do Git nesta versão. Os notebooks podem localizar esses arquivos na estrutura do projeto; o PIOFlow também prevê caminhos alternativos para execução no Colab.

## Modelos desenvolvidos

### PIOFlow: implementação experimental em TensorFlow/Keras

O PIOFlow usa blocos convolucionais inspirados na arquitetura YOLO11n e três saídas de detecção, nas escalas P3, P4 e P5. Para entradas de 640 × 640 pixels, essas saídas têm dimensões `80 × 80 × 4 × 5`, `40 × 40 × 4 × 5` e `20 × 20 × 4 × 5`. A rede, a cabeça de detecção, a formação dos alvos, a função de perda e a decodificação das caixas foram implementadas no notebook. É uma implementação experimental própria, com cerca de 4,1 milhões de parâmetros, e não a implementação oficial do YOLO11.

Os pesos começaram aleatórios. O treinamento foi configurado para até 50 épocas, lote de 2 imagens, otimizador Adam, taxa de aprendizado inicial de `0,001` e parada antecipada após oito épocas sem melhora na perda de validação. O histórico preservado no notebook registra 50 épocas; a menor perda de validação ocorreu na época 44, com valor aproximado de `3,11`. O checkpoint utilizado para a avaliação está em `resultados/detector_pio.weights.h5`.

### YOLOPIO: ajuste do YOLO11n pré-treinado

O YOLOPIO utiliza a implementação do Ultralytics e parte do arquivo `yolo11n.pt`. O notebook prepara a configuração local da base com uma classe, treina o modelo e salva o melhor checkpoint em `resultados/treinos_yolo11/pio_yolo11n/weights/best.pt`. A execução registrada chegou a 30 épocas, com imagens de 640 × 640 pixels, lote de 4 imagens, semente aleatória 42 e paciência de oito épocas. O histórico por época está em `results.csv` na mesma pasta de treinamento.

Os pesos iniciais deste segundo experimento já continham aprendizado anterior; por isso seu resultado não representa treinamento a partir de pesos aleatórios. O notebook mantém o treinamento desativado por padrão para reutilizar o checkpoint existente e também permite retomar uma execução interrompida a partir de `last.pt`.

## Avaliação na base PIO

Os dois notebooks avaliam detecção e contagem nas 452 imagens da divisão de validação. A detecção compara caixas previstas e anotadas; a contagem compara o número de detecções aceitas com o número de caixas válidas em cada imagem. Os procedimentos de cálculo das métricas de detecção são próprios de cada notebook, portanto a tabela indica a tendência dos experimentos e não substitui uma comparação com protocolo único.

| Métrica na validação PIO | PIOFlow | YOLOPIO |
| --- | ---: | ---: |
| Precisão | 34,20% | 92,78% |
| Recall | 94,11% | 89,67% |
| AP ou mAP@0,50 | 83,96% | 94,52% |
| mAP@0,50:0,95 | 45,52% | 63,93% |
| MAE da contagem | 286,24 galinhas/imagem | 20,92 galinhas/imagem |
| RMSE da contagem | 310,17 galinhas/imagem | 31,18 galinhas/imagem |
| MAPE da contagem | 351,77% | 11,72% |
| Viés médio da contagem | +286,24 galinhas/imagem | +19,79 galinhas/imagem |

**Precisão** indica a proporção das detecções aceitas que correspondem a uma anotação; **recall**, a proporção de anotações encontradas. AP/mAP resume o desempenho ao variar o limiar de confiança e exigir sobreposição entre caixas. O **MAE** é a média do erro absoluto entre contagem prevista e real, em galinhas por imagem; o **RMSE** penaliza mais os erros grandes. O **MAPE** expressa a média do erro relativo à contagem anotada, em porcentagem. O **viés** preserva o sinal da diferença: valor positivo indica tendência a contar aves a mais. O MAPE calculado nos notebooks exclui imagens sem galinhas anotadas; nenhuma das 452 imagens avaliadas precisou ser excluída por esse motivo.

O PIOFlow apresentou muitos falsos positivos no limiar de confiança de `0,25`: o notebook registra 203.239 detecções para 73.857 caixas válidas anotadas. O YOLOPIO registrou 82.802 detecções para as mesmas 73.857 caixas válidas, ainda com viés positivo de contagem. O melhor resultado do YOLOPIO na PIO não elimina o erro por imagem nem demonstra que a contagem será correta em outros cenários.

## Inspeção dos vídeos da Raiar

Cada notebook de treinamento mostra previsões em até três quadros de cada vídeo da Raiar. Na execução registrada, o PIOFlow produziu centenas de caixas nos seis quadros exibidos. O YOLOPIO produziu uma detecção em cada um dos três quadros escolhidos de `camera-raiar.mp4` e, no segundo vídeo, 32, 32 e 43 detecções nos quadros exibidos.

Esses valores são **saídas do modelo**, não contagens verificadas de galinhas. Sem caixas e contagens anotadas para os mesmos quadros, não é possível calcular precisão, recall ou erro de contagem nas câmeras da Raiar. A diferença observada entre os vídeos indica que o desempenho medido na PIO não pode ser transferido diretamente para as imagens das câmeras locais.

**Resultados do PIOFlow nas câmeras da Raiar**

![Output do modelo PIOFlow: Resultados nas câmeras da Raiar.](/img/outputFLOW.png)

Fonte: notebook 'PIOFlow' elaborado pelos autores (2026).

**Resultados do YOLOPIO nas câmeras da Raiar**

![Output do modelo PIOYOLO: Resultados nas câmeras da Raiar.](/img/outputYOLO.png)

Fonte: notebook 'YOLOPIO' elaborado pelos autores (2026).

## Estado atual e validações pendentes

O experimento com pesos pré-treinados alcançou métricas de detecção e contagem melhores na validação PIO do que a implementação experimental com pesos aleatórios. O próximo resultado necessário para avaliar uso nas câmeras da Raiar é um conjunto de quadros locais anotados e revisados, com caixas e contagens de referência. Essa avaliação deverá separar sessões de captura entre desenvolvimento e teste e informar os resultados por câmera e condição de imagem. Até lá, as previsões nos vídeos da Raiar servem para inspeção, sem uma medida quantitativa de desempenho local.

## Referências {#referencias}

[1] BONICHE, Keyla; CRUZ, Edmanuel. **PIO, A Large-Scale Dataset for Broiler Chicken Detection under Real Poultry Farming Conditions: DATASET v.1**. Zenodo, 2025. DOI: 10.5281/zenodo.16686320. Disponível em: [https://zenodo.org/records/16686320](https://zenodo.org/records/16686320). Acesso em: 15 out. 2026.
