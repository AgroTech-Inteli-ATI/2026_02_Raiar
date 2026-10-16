---
title: Piloto com o vídeo da Raiar
sidebar_label: Piloto do vídeo
sidebar_position: 9
description: Preparação de quadros e recortes e comparação da detecção automática de aves no vídeo.
---

# Piloto com o vídeo da Raiar

O vídeo fornecido foi utilizado para verificar a transferência do detector
pré-treinado ao enquadramento real da câmera CAM16. O arquivo tem aproximadamente
9 minutos e 59 segundos, resolução de 1024 × 576 pixels e cerca de 15 quadros por
segundo. Uma cópia foi preservada e conferida por SHA-256. Os arquivos reais,
quadros e resultados permanecem locais e excluídos do Git.

O [guia do detector](../sprint-2/deteccao-de-aves.md) explica o pacote. O resultado deste
piloto ainda não comprova a qualidade exigida nos [requisitos](./requisitos.md).
Os termos técnicos estão no [glossário](./glossario.md).

A identificação é automática: `predict` recebe o vídeo ou a imagem, carrega o
YOLO pré-treinado e retorna as caixas e contagens. A execução não exige marcações
manuais nem arquivos de rótulos.

## Preparação dos quadros

Foram extraídos 30 quadros, um a cada 20 segundos, em PNG na resolução original.
O PNG evita uma nova etapa de compressão com perda; não recupera informação já
perdida na gravação. Capturas da interface do player não são necessárias.

```bash
uv run --frozen raiar-vision extract --source data/raw/raiar-cam16-video-01/video.mp4 --session-id raiar-cam16-video-02 --camera-id CAM16 --sample-seconds 20 --image-format png
```

O exemplo usa outro ID para preservar a sessão já criada. O ID do lote e o
horário absoluto ficam nulos quando desconhecidos. O horário sobreposto na
imagem é uma pista a confirmar com o responsável pela câmera; não foi convertido
automaticamente em horário operacional.

Quadros da sessão ficam em `data/interim/raiar-cam16-video-01/`. Cada registro
identifica origem, posição no vídeo, hashes e grupo de captura. Todos os quadros
e recortes conservam um único grupo de origem.

## Região próxima e detecção por blocos

Foi selecionada a região `[90, 330, 550, 500]` em pixels, correspondente a um
recorte de 460 × 170 pixels da parte mais próxima do chão. Trata-se de uma região
para comparar a detecção automática, sem calibração dos níveis físicos do Jump Start.

O comando `crop` exporta PNGs sem redimensionar e preserva a relação com o quadro
completo. A exportação de recortes é opcional; `predict` aceita o vídeo original.

```bash
uv run --frozen raiar-vision crop --manifest data/interim/raiar-cam16-video-01/manifest.jsonl --output data/interim/raiar-cam16-video-01/near-floor-v2 --roi 0.087890625 0.5729166666666666 0.537109375 0.8680555555555556
```

Os recortes utilizados no piloto estão em `near-floor/`; a reprodução pelo
comando versionado também foi verificada em `near-floor-cli/`.

A biblioteca SAHI permite dividir uma imagem em blocos e combinar as previsões
novamente no sistema de coordenadas original [1]. A implementação preserva as
classes aceitas e registra as coordenadas da região. Caixas sobrepostas são
filtradas por NMS; os parâmetros ficam na configuração da execução.

As configurações em `configs/raiar/` cobrem quatro métodos. É possível executar
qualquer um deles diretamente sobre o vídeo:

```bash
uv run --frozen raiar-vision predict --source data/raw/raiar-cam16-video-01/video.mp4 --camera-id CAM16 --config configs/raiar/full-sliced.yaml
```

Quando há uma ROI, `escopo_contagem` indica `regiao_configurada`. Essa contagem
não representa o quadro inteiro. As caixas retornam às coordenadas originais
para revisão. O NMS busca reduzir caixas duplicadas entre os blocos.

## Resultado do piloto

Foram executadas 120 análises com PoultryVision YOLO11m, confiança mínima de
0,25 e tamanho de inferência de 640 pixels. Cada método recebeu os mesmos 30
quadros. As medianas abaixo foram medidas na CPU do computador de desenvolvimento.

| Método | Quadros | Caixas previstas | Mediana de inferência |
| --- | ---: | ---: | ---: |
| Quadro inteiro | 30 | 0 | 0,27 s |
| Quadro inteiro com SAHI, blocos de 256 pixels | 30 | 1 | 5,04 s |
| Região próxima | 30 | 0 | 0,55 s |
| Região próxima com SAHI, blocos de 128 pixels | 30 | 0 | 7,55 s |

A única caixa, no instante aproximado 03:40, marcou um elemento da estrutura
em primeiro plano. A inspeção visual a classificou como falso positivo; ela não
foi utilizada como rótulo positivo. Os recortes aumentaram o custo de execução e
não demonstraram uma contagem útil nesta amostra.

Também foi realizada uma triagem com YOLO11n pré-treinado em COCO, filtrando a
classe `bird`: três quadros (início, meio e fim) em três métodos, totalizando
nove análises adicionais sem detecções e sem falhas de processamento. Os
resultados ficam em `coco-triage/`. Essa triagem tem cobertura menor que a
comparação principal; foram 129 análises ao somar os dois modelos.

As aves aparecem pequenas e parte da cena fica encoberta. A causa exata das
falhas do modelo ainda precisa de referências manuais e ensaios adicionais.
Zero previsões não equivale a imagem sem aves. Não foram calculados recall,
mAP, erro de contagem ou melhora com treinamento próprio.

Os dados detalhados ficam em `outputs/raiar-cam16-pilot-v1/`: resultados por
método, imagens anotadas, `comparison.csv`, `pilot-report.json`, inspeção da
detecção isolada e montagem dos 30 quadros. O relatório textual versionado fica
em `reports/raiar-video-pilot.md`.

## Execução automática e consulta dos resultados

Para processar o vídeo com o modelo disponível, executar na raiz do repositório:

```bash
uv run --frozen raiar-vision predict --source data/raw/raiar-cam16-video-01/video.mp4 --camera-id CAM16 --config configs/raiar/full.yaml
```

O comando informa a pasta de saída, a quantidade de quadros e os estados de
processamento. A pasta contém `results.jsonl`, `counts.csv` e imagens com as
caixas desenhadas pelo detector em `annotated/`. Essas caixas são resultados
automáticos do YOLO. O histórico é salvo em `outputs/results.sqlite3`.

O estado `valido` confirma o processamento técnico do quadro; não comprova
acerto do modelo. Uma execução com zero caixas deve registrar esse resultado,
sem tratar a ausência de detecções como comprovação de ausência de aves.

## Condições para treinamento e avaliação

O treinamento próprio é uma evolução posterior. As referências usadas para
treinar e medir erros não são entradas obrigatórias de `predict`. Nenhum
treinamento próprio foi executado neste piloto.

Conservar o único vídeo como grupo de origem. A divisão aleatória de quadros
vizinhos não produz um teste independente. O preparador exige ao menos três
grupos para criar treino, validação e teste; ainda são necessárias outras
gravações e cobertura das condições relevantes.

Depois das revisões e de novas sessões, consolidar os manifestos revisados e
seguir o [fluxo de treinamento e comparação](../sprint-2/deteccao-de-aves.md). Se as aves
continuarem indistinguíveis para anotação, será necessário rever a resolução
ou o enquadramento. A instalação na Raspberry Pi também depende de ensaio no
dispositivo, sem utilizar os tempos desta máquina como comprovação.

## Referências {#referencias}

[1] ULTRALYTICS. **Sliced inference with SAHI**. Disponível em: [https://docs.ultralytics.com/guides/sahi-tiled-inference/](https://docs.ultralytics.com/guides/sahi-tiled-inference/). Acesso em: 14 out. 2026.
