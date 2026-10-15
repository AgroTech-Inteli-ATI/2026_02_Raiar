---
title: Detecção de aves com YOLO
sidebar_label: Detector de aves
sidebar_position: 1
description: Implementação do detector pré-treinado, preparação dos dados e evolução para treinamento próprio.
---

# Detecção de aves com YOLO

O módulo `chicken_yolo` localiza aves visíveis em imagens e quadros de vídeos,
produz contagens e permite ajustar o modelo com dados próprios. **Detecção de
objetos** localiza animais por caixas delimitadoras; OCR reconhece texto. A tarefa
deste projeto é detecção, de acordo com a [proposta de solução](../sprint-1/proposta-de-solucao.md).

O processamento mantém a separação entre quadro vazio, imagem inadequada e falha.
As contagens abrangem apenas as aves detectadas; aves ocultas e o total do lote
não são estimados. Os termos técnicos estão no [glossário](../sprint-1/glossario.md).

## Modelos e ambiente

| Modelo registrado | Origem e classes | Uso inicial |
| --- | --- | --- |
| `poultryvision` | PoultryVision, baseado em YOLO11m; `chicken` e `egg` [1] | Candidato especializado, aceitando somente aves |
| `coco` | YOLO11n pré-treinado; classe genérica `bird` no COCO [2][3] | Referência leve e ponto de partida para o treino na Raspberry Pi |

O primeiro download registra a revisão disponível, o caminho e o SHA-256 em
`models/pretrained/<modelo>/metadata.json`. Downloads posteriores reutilizam esse
artefato se o hash continuar igual. Uma troca de checkpoint exige preservar a
versão anterior. Resultados divulgados por terceiros não são métricas da Raiar.

O pacote requer Python 3.11 a 3.13. O ambiente de referência usa Python 3.12.
O `uv.lock` fixa as dependências; a instalação inicial e os downloads de modelos
exigem acesso à internet. Os pesos publicados declaram licença AGPL-3.0 [1][2].

```bash
uv sync --frozen
```

No PowerShell, ative o ambiente e use o comando curto:

```powershell
.\.venv\Scripts\Activate.ps1
chicken-yolo --help
chicken-yolo prepare-model
```

`prepare-model` utiliza PoultryVision por padrão. Para selecionar a referência
genérica, execute `chicken-yolo prepare-model coco`. Os demais exemplos desta
página pressupõem a `.venv` ativa. Sem ativá-la, use `uv run --frozen chicken-yolo`
seguido do subcomando. A execução por `python -m chicken_yolo` e o comando
`raiar-vision` continuam disponíveis.

Execute a partir da raiz. Para chamar o programa de outra pasta, use
`chicken-yolo --root CAMINHO_DO_REPOSITORIO` antes do subcomando.

## Organização do código e dos arquivos

| Pasta | Responsabilidade |
| --- | --- |
| `src/chicken_yolo/` | Captura, qualidade, detector, zonas, pipeline, armazenamento, dataset, treino, avaliação, benchmark e sincronização |
| `configs/` | Parâmetros e calibrações por câmera |
| `data/raw/` | Imagens e vídeos originais, preservados |
| `data/interim/` | Quadros extraídos e manifestos para anotação |
| `data/processed/` | Datasets preparados, com imagens e rótulos em `train`, `val` e `test` |
| `data/manifests/` | Manifestos revisados com origem, qualidade e grupos |
| `models/pretrained/` e `models/trained/` | Pesos e metadados locais |
| `outputs/` | Histórico SQLite e exportações de inferência |
| `runs/` | Artefatos de treino e curvas produzidas pela Ultralytics |
| `reports/generated/` | Relatórios locais de avaliação e capacidade |
| `tests/` | Verificação das regras e integrações do módulo |

Dados, pesos, caches e saídas são excluídos do Git. A equipe pode versionar
relatórios revisados em `reports/`, sem imagens ou metadados restritos.

## Inferência em imagens e vídeos

O modelo pré-treinado detecta as aves automaticamente. A execução de `predict`
recebe somente a imagem ou o vídeo e a configuração do detector, sem exigir
caixas desenhadas, arquivos de rótulos ou preparação de um dataset. Os rótulos
descritos na seção de treinamento são dados para um futuro ajuste supervisionado
e para medir a qualidade, separados da execução de predições.

Copie um arquivo para `data/raw/`. Os exemplos abaixo usam nomes ilustrativos:

```bash
chicken-yolo predict --source data/raw/imagem.jpg
chicken-yolo predict --source data/raw/video.mp4 --camera-id camera-01 --lote-id lote-01 --captured-at 2026-10-14T10:00:00-03:00
chicken-yolo predict --source data/raw/imagem.jpg --model coco
```

`configs/inference.yaml` define modelo, classes aceitas, confiança, IoU, resolução,
máximo de detecções e intervalo de amostragem. O intervalo de um segundo é apenas
um valor de desenvolvimento. A frequência homologada dependerá dos dados e do
ensaio no dispositivo. O detector recebe cada quadro individualmente [4].

Horário informado inclui fuso. Em vídeos, `--captured-at` corresponde ao início;
o programa acrescenta o deslocamento de cada quadro. Sem essa informação, o
horário fica nulo e a saída não pode integrar uma série temporal operacional.
O horário de processamento e a data de modificação do arquivo não substituem o
horário da captura. Uma pasta pode ser processada, mas seus arquivos precisam de
metadados próprios para uso histórico; um único horário não é aplicado à pasta.

O comando cria uma pasta por execução, contendo `results.jsonl`, `counts.csv` e
`annotated/`. `--output` aceita uma pasta nova, evitando sobrescrever análises.
O histórico completo fica em `outputs/results.sqlite3`, com chave `analise_id`.
Reenvio do mesmo resultado não cria outra linha; reprocessar gera nova análise.
O SQLite é a referência durável; CSV e JSON são exportações daquela execução.
Erros de leitura da entrada são registrados na tabela `events` do histórico local.

Cada resultado registra quadro, origem, câmera e lote quando informados, modelo,
hash da configuração, zonas, regra de atribuição, horários e duração. O campo
`quantidade_aves_visiveis` no JSON representa o total do quadro. No CSV, com zonas
configuradas, esse campo corresponde à contagem de cada nível. Quantidade sem
nível é repetida nas linhas por nível e não deve ser somada entre elas.

Falhas de inferência produzem `falha_processamento` e contagens nulas. Imagens
não decodificadas ou reprovadas na triagem técnica produzem `imagem_inadequada`.
O comando retorna código de erro se houver falha de processamento. Brilho,
resolução e desfoque são critérios configuráveis; essa triagem não garante que
os níveis físicos estejam visíveis e não substitui a revisão humana.

## Visualização com notebook

O notebook `src/chicken_yolo/notebooks/visualizar-deteccoes.ipynb` executa o mesmo pipeline de
detecção do comando `predict`. Ele oferece controles para entrada, modelo,
confiança, resolução, intervalo, limite de quadros e comparação entre o modo
direto e SAHI.

Instale as dependências opcionais na raiz do projeto:

```bash
uv sync --frozen --group notebooks
```

Com a `.venv` ativa, abra a interface:

```powershell
jupyter lab src/chicken_yolo/notebooks/visualizar-deteccoes.ipynb
```

Selecione o kernel Python da `.venv` e execute as células na ordem. A etapa 3
carrega o modelo e realiza novas inferências. A etapa 4 desenha o original e as
previsões lado a lado; mover seu controle de quadro apenas exibe resultados já
calculados. Para aplicar novos parâmetros, reexecute a etapa 3 e atualize a
visualização e a tabela.

Cada execução cria `outputs/notebook-.../`, com PNGs originais, imagens com as
caixas, configurações, CSV/JSONL e um resumo. O histórico SQLite é preservado.
O notebook entregue para versionamento não contém saídas nem imagens
incorporadas. A visualização facilita a exploração; não constitui treinamento
nem medição de acurácia.

## Exemplo no segundo vídeo da Raiar

Em 15 de outubro de 2026, foram extraídos 12 quadros do segundo vídeo fornecido,
um por segundo, em sua resolução original de 1024 × 576 pixels. A Figura 1
mostra o quadro em aproximadamente 2 segundos, processado automaticamente pelo
PoultryVision YOLO11m com SAHI: blocos de 256 × 256 pixels, sobreposição de 20%,
tamanho de inferência de 640 pixels e confiança mínima de 0,25.

**Figura 1 – Detecções automáticas de galinhas no segundo vídeo da Raiar**

![Quadro do aviário com duas caixas de detecção sobre galinhas próximas à plataforma.](/img/detector-aves/resultado-video-02.jpg)

Fonte: elaborado pelos autores (2026), a partir do vídeo fornecido pela Raiar e
das saídas automáticas do PoultryVision.

As duas caixas incidem sobre galinhas distinguíveis, mas muitas outras aves
visíveis permanecem sem detecção. No teste com essa configuração, oito dos
12 quadros receberam alguma caixa, com zero a duas caixas por quadro. Esses
números descrevem previsões do modelo; não demonstram contagem completa,
precisão, recall ou mAP. Não foi realizado treinamento próprio nesse ensaio.

O frame ilustrativo integra a documentação. Os demais frames, vídeos, pesos e
arquivos de execução continuam no armazenamento local, conforme o `.gitignore`.

## Zonas do Jump Start

Copie `configs/cameras/camera-example.yaml` para uma configuração da instalação.
Defina câmera, versão, dimensões da referência e polígonos normalizados entre 0 e
1. Após revisão, marque `calibrated: true`. O exemplo permanece bloqueado enquanto
não estiver calibrado. A câmera deve corresponder ao quadro, e sua proporção deve
ser compatível com a referência.

```bash
chicken-yolo predict --source data/raw/imagem.jpg --camera-id camera-01 --lote-id lote-01 --zones configs/cameras/camera-01.yaml
```

A regra usa o centro da borda inferior da caixa. Fronteiras, sobreposição de zonas
e pontos fora das zonas resultam em nível indeterminado. Perspectiva inadequada
exige rever a instalação e o protocolo, conforme o
[dicionário de dados](../sprint-1/dicionario-de-dados.md). O programa não resolve sozinho a
ambiguidade entre uma zona desenhada e um nível físico.

Percentuais usam a soma das aves atribuídas aos níveis. Total atribuído zero
produz percentuais nulos; uma imagem válida sem aves mantém contagens zero.
Imagens inválidas têm contagens nulas. Não somar câmeras sobrepostas nem quadros
sucessivos como se representassem aves distintas.

## Preparação opcional de dados para treinamento

Esta etapa se aplica somente à criação de um dataset próprio para treinamento
e avaliação. Para identificar aves com os pesos disponíveis, utilizar diretamente
o comando `predict` da seção de inferência.

Começar pelos 30 quadros de triagem previstos no dicionário, revisados por dois
anotadores. Ampliar a cobertura após confirmar o protocolo de visibilidade e
atribuição. O comando de extração preserva o original e gera um manifesto:

```bash
chicken-yolo extract --source data/raw/video.mp4 --session-id sessao-01 --camera-id camera-01 --lote-id lote-01 --sample-seconds 20 --captured-at 2026-10-14T10:00:00-03:00
```

A extração salva PNG por padrão; `--image-format jpg` é uma alternativa. O lote
pode ficar nulo quando desconhecido. O [piloto com o vídeo da Raiar](../sprint-1/piloto-video-raiar.md)
mostra a exportação de recortes e os testes automáticos com SAHI.

Anotar todas as galinhas distinguíveis e exportar um `.txt` por imagem no formato
YOLO, com a classe `0`, centro e dimensões normalizadas [5]:

```text
0 0.50 0.40 0.12 0.18
```

Para imagem revisada sem aves, criar um arquivo de rótulo explicitamente vazio.
Arquivo ausente não equivale a imagem negativa. Pré-anotações do modelo precisam
de revisão. O manifesto inicial tem `qualidade: pendente` e
`status_revisao: rascunho`; só registros avaliáveis e revisados são preparados.

Consolidar as entradas revisadas em `data/manifests/anotacoes.jsonl`, uma por linha:

```json
{"quadro_id":"quadro-01","imagem":"data/interim/sessao-01/quadro-01.jpg","rotulo":"data/interim/sessao-01/quadro-01.txt","grupo_origem":"camera-01-dia-2026-10-14","camera_id":"camera-01","lote_id":"lote-01","qualidade":"avaliavel","status_revisao":"revisada"}
```

Os caminhos são relativos à raiz. `grupo_origem` deve juntar sessões e trechos
próximos da mesma câmera e dia, inclusive de vídeos diferentes. A extração começa
com o ID da sessão como grupo; revisar essa classificação antes da divisão.
Quadros de um grupo ficam juntos. São necessários pelo menos três grupos
independentes; isso permite dividir, mas não comprova representatividade.

```bash
chicken-yolo prepare-dataset --manifest data/manifests/anotacoes.jsonl --output data/processed/galinhas-v1 --seed 42
```

A divisão padrão 70/15/15 opera sobre grupos e é aproximada em número de imagens.
O programa valida caixas e rejeita duplicatas exatas de pixels. Imagens parecidas
exigem a organização correta dos grupos. O dataset inclui cópias dos arquivos,
manifesto, partições, hashes e `dataset.yaml`. Uma versão existente não é
sobrescrita. Alterações ou arquivos extras são detectados antes do treino e da
avaliação. Criar outra versão ao corrigir ou ampliar a base e preservar o teste
reservado; a divisão não deve ser refeita para favorecer resultados.

## Treinamento próprio e comparação

`configs/training.yaml` começa com o YOLO11n pré-treinado para avaliar uma solução
leve. Pode-se selecionar `poultryvision` para comparar outra inicialização. O
fine-tuning parte dos pesos aprendidos, em vez de treinamento do zero [6].
Treinar em máquina com GPU quando disponível; a configuração inicial usa CPU
para ser executável sem GPU. Ajustar `device` e o ambiente PyTorch à máquina de
treino. A Raspberry Pi é o alvo de inferência.

```bash
chicken-yolo train --config configs/training.yaml
```

O treinamento usa as pastas de treino e validação. Ao terminar, copia `best.pt`
para uma pasta única em `models/trained/`, registra a origem e o dataset, e marca
o modelo como `aguardando_avaliacao`. Concluir o treino não comprova melhora.

Durante desenvolvimento, comparar os candidatos na validação:

```bash
chicken-yolo evaluate --dataset data/processed/galinhas-v1/dataset.yaml --model poultryvision --split val
chicken-yolo evaluate --dataset data/processed/galinhas-v1/dataset.yaml --model coco --split val
chicken-yolo evaluate --dataset data/processed/galinhas-v1/dataset.yaml --weights models/trained/NOME_DO_TREINO/best.pt --split val
```

Depois de fixar modelo e parâmetros, usar `--split test` para a avaliação final.
O avaliador compara uma única classe de ave, preservando os nomes originais do
modelo. Calcula AP50 e média de AP entre IoU 0,50 e 0,95, com interpolação em 101
pontos e correspondência por confiança. É uma avaliação local de uma classe,
sem as estratificações completas do benchmark COCO. A AP usa previsões a partir
de confiança 0,001; precisão, recall e contagens usam o limiar operacional.

A avaliação por nível requer `--zones` e, em cada referência, os campos manuais
`contagens_por_nivel` para todos os níveis e `zonas_versao` correspondente. Essas
contagens não são geradas pela mesma regra automática que será avaliada. Sem
zonas, são avaliadas detecção e contagem total por imagem.

O relatório inclui erro de contagem total e por nível, erro de distribuição em
pontos percentuais, falsos positivos e negativos, cobertura, rejeições e falhas.
Previsões vazias continuam penalizadas na contagem; quadros sem denominador são
excluídos apenas do cálculo percentual. As metas de 15% e 10 pontos percentuais
dos [requisitos](../sprint-1/requisitos.md) continuam preliminares. Nenhum resultado do
ambiente de desenvolvimento comprova essas metas na Raiar.

## Capacidade e exportação

O benchmark reproduz arquivos locais e mede duração, atrasos, CPU e memória:

```bash
chicken-yolo benchmark --source data/raw/video.mp4 --model coco --duration-seconds 60 --interval-seconds 5
```

No dispositivo, ampliar o ensaio para 24 horas com entrada representativa e
modelo, resolução e frequência fixados. O relatório inclui proporção das
inferências que terminam em até 80% do intervalo, janelas de CPU de até cinco
minutos e memória disponível. O ensaio de reprodução não comprova captura ao
vivo, conectividade, montagem, aquecimento ou capacidade com três dispositivos.
Essas verificações continuam necessárias para os RNF03, RNF11 e RNF12.

```bash
chicken-yolo export --weights models/trained/NOME_DO_TREINO/best.pt --format onnx
chicken-yolo export --weights models/trained/NOME_DO_TREINO/best.pt --format ncnn
```

A exportação pode instalar componentes adicionais. Após exportar, usar
`--weights CAMINHO_DO_ARTEFATO` na inferência e repetir a avaliação de qualidade
e capacidade. A escolha do formato depende do ensaio na Raspberry Pi [7].
Um arquivo de metadados `.raiar.json` preserva o hash do artefato exportado e
a referência ao checkpoint de origem.

## Contrato de sincronização e integração

O histórico local serve de fila durável enquanto não há rede. Um backend
configurado pode receber lotes de resultados por HTTPS:

```bash
chicken-yolo sync --url https://SEU_BACKEND/api/analyses --batch-size 100
```

Se necessário, definir o token na variável de ambiente `RAIAR_SYNC_TOKEN`.
Credenciais não são gravadas nas configurações. O comando envia uma requisição
POST com este formato:

```json
{"schema_version":1,"analyses":[{"analise_id":"ID_DA_ANALISE","quadro_id":"ID_DO_QUADRO"}]}
```

As entradas em `analyses` contêm o resultado completo, inclusive as detecções e
metadados; o exemplo foi abreviado. O servidor precisa deduplicar por
`analise_id` e responder com os IDs efetivamente aceitos:

```json
{"accepted_analysis_ids":["ID_DA_ANALISE"]}
```

Somente IDs confirmados saem da fila. Erros ou indisponibilidade preservam as
pendências. Não há envio automático nem endpoint real configurado. O backend,
dashboard, captura ao vivo, janelas operacionais e políticas de retenção serão
integrados conforme os requisitos e a infraestrutura disponíveis. CSV e JSON
já oferecem um contrato para consulta e comparação.

## Verificação e situação atual

```bash
uv run --frozen pytest
uv run --frozen ruff check src tests
uv run --frozen ruff format --check src tests
```

Os testes usam exemplos sintéticos e adapters controlados para verificar as
regras, incluindo fronteiras, sobreposição, zeros, falhas, partições,
integridade, referências manuais e confirmação de sincronização. Eles não medem
a qualidade do detector no aviário. O treino real depende de imagens e rótulos
revisados, e a homologação depende da Raspberry Pi instalada.

## Referências {#referencias}

[1] ASSA, Stephane Williams Anderson. **PoultryVision**. Disponível em: [https://huggingface.co/Williamsanderson/PoultryVision](https://huggingface.co/Williamsanderson/PoultryVision). Acesso em: 14 out. 2026.

[2] ULTRALYTICS. **Ultralytics YOLO11**. Disponível em: [https://docs.ultralytics.com/models/yolo11/](https://docs.ultralytics.com/models/yolo11/). Acesso em: 14 out. 2026.

[3] ULTRALYTICS. **COCO dataset**. Disponível em: [https://docs.ultralytics.com/datasets/detect/coco/](https://docs.ultralytics.com/datasets/detect/coco/). Acesso em: 14 out. 2026.

[4] ULTRALYTICS. **Model prediction**. Disponível em: [https://docs.ultralytics.com/modes/predict/](https://docs.ultralytics.com/modes/predict/). Acesso em: 14 out. 2026.

[5] ULTRALYTICS. **Object detection datasets overview**. Disponível em: [https://docs.ultralytics.com/datasets/detect/](https://docs.ultralytics.com/datasets/detect/). Acesso em: 14 out. 2026.

[6] ULTRALYTICS. **Fine-tuning guide**. Disponível em: [https://docs.ultralytics.com/guides/finetuning-guide](https://docs.ultralytics.com/guides/finetuning-guide). Acesso em: 14 out. 2026.

[7] ULTRALYTICS. **Raspberry Pi setup and benchmarks**. Disponível em: [https://docs.ultralytics.com/guides/raspberry-pi/](https://docs.ultralytics.com/guides/raspberry-pi/). Acesso em: 14 out. 2026.
