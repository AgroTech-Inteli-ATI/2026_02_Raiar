# Piloto de detecção no vídeo da Raiar

Ensaio realizado em 14 de outubro de 2026. Os arquivos reais ficam apenas no armazenamento local, excluídos do Git.

## Material e preparação

- Vídeo original preservado em `data/raw/raiar-cam16-video-01/video.mp4`, com cópia verificada por SHA-256.
- Duração aproximada de 9 min 59 s; 1024 × 576 pixels, cerca de 15 quadros/s.
- 30 quadros PNG sem perda adicional, amostrados a cada 20 segundos.
- 30 recortes de 460 × 170 pixels da região `[90, 330, 550, 500]`, sem redimensionar os arquivos.
- Câmera identificada pelo texto CAM16; lote e horário absoluto permanecem não confirmados.
- Todos os quadros e recortes mantêm o mesmo grupo de origem; não há partições independentes artificiais.

## Comparação com o modelo pré-treinado

PoultryVision YOLO11m, classe `chicken`, confiança mínima 0,25 e imagem de inferência de 640 pixels. Foram realizadas 120 análises, 30 por método. Tempos medidos na CPU deste computador, incluindo chamadas por recortes; não representam a Raspberry Pi.

| Método | Quadros | Caixas previstas | Mediana de inferência |
| --- | ---: | ---: | ---: |
| Quadro inteiro | 30 | 0 | 0.27 s |
| Quadro inteiro + SAHI 256 | 30 | 1 | 5.04 s |
| Região próxima | 30 | 0 | 0.55 s |
| Região próxima + SAHI 128 | 30 | 0 | 7.55 s |

A única caixa, em aproximadamente 03:40, incide sobre a estrutura/anteparo em primeiro plano, e não sobre uma ave identificável. Foi classificada como falso positivo na inspeção visual e não será usada como rótulo positivo. A análise técnica dos quadros terminou, mas não produziu uma contagem útil de aves.

Como diagnóstico adicional, o YOLO11n pré-treinado em COCO, filtrando a classe `bird`, foi executado sobre três quadros (início, meio e fim), em três métodos: quadro inteiro, quadro inteiro com SAHI e região próxima com SAHI. As nove análises terminaram sem falha e sem detecções. Essa triagem está em `coco-triage/` e não tem a mesma cobertura da comparação principal. Foram 129 análises no total, incluindo os dois modelos.

Sem referências manuais completas, não foram calculadas acurácia, recall, mAP ou melhora em relação ao modelo original. Zero previsões não significa quadro sem aves.

## Detecção automática e arquivos

O comando `predict` processa imagens e vídeos com o YOLO pré-treinado e retorna caixas e contagens automaticamente. A inferência não exige marcações manuais nem arquivos de rótulos. As imagens em `annotated/` mostram as caixas produzidas pelo próprio detector.

```bash
uv run --frozen raiar-vision predict --source data/raw/raiar-cam16-video-01/video.mp4 --camera-id CAM16 --config configs/raiar/full.yaml
```

- Quadros: `data/interim/raiar-cam16-video-01/`.
- Recortes do piloto: `data/interim/raiar-cam16-video-01/near-floor/`.
- Recortes reproduzidos pelo comando `crop`: `data/interim/raiar-cam16-video-01/near-floor-cli/`.
- Comparação e 120 resultados: `outputs/raiar-cam16-pilot-v1/`.
- Resumo estruturado: `pilot-report.json`; planilha: `comparison.csv`; visão geral: `frames-overview.jpg`.
- Configurações reproduzíveis: `configs/raiar/`.

## Próximas condições para treinamento

O futuro treinamento supervisionado utiliza um dataset próprio com referências revisadas e outras sessões para avaliação independente. Isso é separado da detecção automática com os pesos disponíveis. O preparador preserva grupos e exige ao menos três grupos de origem para a divisão completa.

Nenhum treinamento próprio foi executado. A biblioteca SAHI está integrada ao detector. O ensaio documentado não produziu contagem confiável neste vídeo; retirar componentes auxiliares não muda os resultados do modelo.
