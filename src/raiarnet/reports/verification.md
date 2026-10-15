# Verificação do módulo de aves

Data: 14 de outubro de 2026. Ambiente: Windows, Python 3.12.14,
Ultralytics 8.4.177 e PyTorch 2.14.1, com dependências fixadas em `uv.lock`.

- 53 testes passaram. Cobrem contagem, zonas, dados revisados, partições,
  integridade, horários, persistência, falhas de captura e processamento,
  avaliação, treino, exportação, recursos e confirmação de sincronização.
- `ruff check src tests` e `ruff format --check src tests` passaram.
- `npm run build` em `docs/` gerou o site de documentação com sucesso.
- Os pesos PoultryVision e YOLO11n foram baixados, registrados e carregados.
  Uma inferência com cada modelo terminou sem falhas. O especializado retornou
  detecções da classe `chicken`.

A entrada do ensaio de inferência foi a prévia pública `val_batch0_pred.jpg` do
[PoultryVision](https://huggingface.co/Williamsanderson/PoultryVision), revisão
`345029f92876389af7c7da2aaef96df074a7531a`. Essa prévia já contém anotações e
foi usada somente para verificar execução e filtro de classes. Não é uma base
independente e não mede acurácia, melhora do modelo ou desempenho na Raiar.
Os arquivos locais desse ensaio ficam em `outputs/smoke-poultryvision/` e
`outputs/smoke-coco/`, excluídos do Git.

Treino e exportação foram verificados por adapters controlados nos testes.
Não foi realizado treinamento com imagens reais da Raiar. A sincronização foi
testada com respostas simuladas, sem envio para um serviço externo. Calibração
dos níveis, teste independente, captura ao vivo, integração ao backend e ensaio
de 24 horas na Raspberry Pi continuam dependendo dos dados e da infraestrutura.

## Piloto com o vídeo da Raiar

Os testes do piloto incluem recortes em pixels originais, coordenadas de
ROI/SAHI, extração PNG, preservação dos grupos e publicação atômica de dados.
O fluxo de inferência usa diretamente imagens e vídeos com os pesos
pré-treinados, sem exigir marcações manuais.

A versão atual passou com 67 testes. Ruff e o build da documentação passaram;
a CLI expõe a detecção automática em `predict` e a preparação opcional dos
dados para treinamento próprio.

Uma inferência real no primeiro PNG do vídeo terminou sem falha, sem arquivos
de rótulos como entrada: um quadro válido e zero detecções, consistente com o
piloto. Os arquivos estão em `outputs/predict-without-editor-20261014/`.
O wheel atualizado foi conferido para conter apenas os componentes atuais.

Foram executadas 120 análises com PoultryVision e nove análises de triagem com
YOLO11n COCO no vídeo real. A única detecção do ensaio principal foi classificada
como falso positivo após inspeção visual. O [relatório do piloto](./raiar-video-pilot.md)
registra os parâmetros, tempos e arquivos. Esses resultados não validam acurácia
nem constituem treinamento próprio.
