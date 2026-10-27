# Raiar Orgânicos — AgroTech Inteli

Projeto da AgroTech Inteli com a Raiar Orgânicos para monitorar, por visão computacional, a distribuição das aves visíveis nos níveis do Jump Start durante a recria.

## Estrutura do repositório

```text
.
├── docs/                   # Site de documentação (Docusaurus)
│   ├── docs/               # Páginas em Markdown/MDX, organizadas por sprint
│   ├── src/css/            # Estilos globais (paleta Raiar e formatação ABNT)
│   └── static/img/         # Imagens usadas nas páginas
├── src/
│   ├── chicken_yolo/       # Detector YOLO pré-treinado: inferência, dataset, treino e avaliação
│   │   ├── configs/        # Configurações de inferência, treino e câmeras
│   │   ├── models/         # Registro dos modelos e pesos locais
│   │   ├── notebooks/      # Execução visual e comparação das detecções
│   │   └── tests/          # Testes do pipeline e das regras dos dados
│   ├── raiarnet/           # Modelo construído do zero, com contagem por nível
│   └── modelos_PIO/        # Notebooks PIOFlow e YOLOPIO (base PIO)
├── data/                   # Dados do chicken_yolo, excluídos do Git
├── outputs/                # SQLite, CSV, JSON e imagens anotadas
├── runs/                   # Resultados dos treinamentos
├── reports/                # Relatórios; execuções em generated/ são locais
├── pyproject.toml          # Pacote Python e dependências
├── uv.lock                 # Versões fixadas das dependências
├── CONTRIBUTING.md         # Padrões de escrita e organização da documentação
└── README.md
```

## Documentação

A documentação é publicada com [Docusaurus](https://docusaurus.io/). Requer Node.js 20 ou superior.

```bash
cd docs
npm install
npm run start   # servidor local com recarga automática
npm run build   # gera o site estático em docs/build
```

Antes de criar ou editar páginas, consulte o [guia de contribuição](./CONTRIBUTING.md).

## Detector de aves

Requer Python 3.11 a 3.13; o ambiente de referência usa Python 3.12 e uv.
Execute os comandos abaixo na raiz do repositório:

```bash
uv sync --frozen
```

No PowerShell, ative o ambiente e prepare o modelo padrão:

```powershell
.\.venv\Scripts\Activate.ps1
chicken-yolo prepare-model
```

Com a `.venv` ativa, o comando `chicken-yolo` fica disponível diretamente no
terminal. `prepare-model` usa PoultryVision por padrão; `chicken-yolo --help`
mostra as operações e exemplos de uso.

Copie uma imagem para `data/raw/imagem.jpg` e execute:

```powershell
chicken-yolo predict --source data/raw/imagem.jpg
```

Para executar sem ativar o ambiente, use `uv run --frozen chicken-yolo` seguido
do subcomando e dos argumentos.

O YOLO identifica as aves automaticamente com os pesos pré-treinados. Não é
necessário desenhar caixas nem fornecer rótulos para executar as predições.
O mesmo comando aceita vídeos com `--source data/raw/video.mp4`.

O comando informa a pasta que contém `results.jsonl`, `counts.csv` e as imagens
anotadas. O histórico local fica em `outputs/results.sqlite3`.
O modelo padrão é o [PoultryVision](https://huggingface.co/Williamsanderson/PoultryVision),
pré-treinado para `chicken` e `egg`; o pipeline aceita somente as classes de aves
configuradas. Para comparar com a variante leve e genérica:

```powershell
chicken-yolo prepare-model coco
chicken-yolo predict --source data/raw/imagem.jpg --model coco
```

## Execução dos modelos com Docker

Docker executa os modelos em ambientes com dependências isoladas. As imagens deste
repositório executam inferência por linha de comando em CPU; não iniciam uma API nem
fazem treinamento. Vídeos, pesos e resultados ficam fora das imagens e são montados
como volumes. Coloque entradas em `data/`; os resultados persistem em `outputs/`.
Esta configuração cobre `chicken_yolo` e a RaiarNet; os experimentos PIOFlow e YOLOPIO
permanecem nos notebooks e não fazem parte destas imagens.

Instale Docker Desktop ou Docker Engine com o plugin Docker Compose e construa as imagens
a partir da raiz do repositório:

```bash
docker compose build
```

Prepare os pesos do detector YOLO uma vez. O primeiro download requer internet:

```bash
docker compose run --rm chicken-yolo prepare-model
```

Coloque uma imagem ou vídeo em `data/raw/` e execute o detector:

```bash
docker compose run --rm chicken-yolo predict --source /app/data/raw/video.mp4
```

O histórico SQLite e as exportações ficam em `outputs/` no computador host. Para a
RaiarNet, disponibilize o checkpoint `best.pt` em `src/raiarnet/runs/` e execute:

```bash
docker compose run --rm raiarnet --source /app/data/raw/video.mp4 --weights /app/src/raiarnet/runs/raiarnet/r1/best.pt --out /app/outputs/raiarnet/r1
```

O caminho do checkpoint é ilustrativo: use o caminho real do peso montado em
`src/raiarnet/runs/`. A imagem da RaiarNet inclui o código de inferência, a configuração
de câmera e as dependências de CPU. O Compose define `linux/arm64/v8`, arquitetura da
Raspberry Pi 4 com sistema operacional de 64 bits, incluindo Arch Linux ARM64. Para
construir no Windows ou em um PC x86, o Docker precisa de suporte a build multiplataforma;
também é possível construir diretamente na Pi. Um sistema operacional de 32 bits não é
contemplado por essas imagens.

Compatibilidade de arquitetura não comprova que o tempo de inferência atende à frequência
de captura do projeto. A RaiarNet foi medida a cerca de 3,5 quadros por segundo na CPU dos
testes documentados, que não é a Raspberry Pi 4. Meça tempo por quadro, CPU, memória e
temperatura na placa real antes de definir o intervalo de processamento em produção.

## Visualização com notebook

O [notebook de visualização](src/chicken_yolo/notebooks/visualizar-deteccoes.ipynb) permite escolher
o vídeo ou a imagem, ajustar o modelo e os parâmetros, executar a detecção e
comparar os quadros originais com as previsões lado a lado.

Instale as dependências opcionais:

```bash
uv sync --frozen --group notebooks
```

Com a `.venv` ativa, abra o notebook:

```powershell
jupyter lab src/chicken_yolo/notebooks/visualizar-deteccoes.ipynb
```

Selecione o Python da `.venv` e execute as células de cima para baixo. A etapa 3
executa o modelo; a etapa 4 permite trocar os quadros já processados sem repetir
a inferência. Alterar os parâmetros exige reexecutar a etapa 3. As novas saídas
ficam em `outputs/notebook-.../`; o notebook é entregue sem imagens incorporadas.

## Dados e evolução do detector

A contagem por nível exige zonas calibradas para a câmera. Até configurar as zonas,
o programa informa a quantidade detectada e mantém o nível indeterminado.
Confiança do detector não equivale à acurácia medida.

O [guia de detecção de aves](docs/docs/sprint-2/deteccao-de-aves.md) explica vídeos,
metadados, preparação de dados para treino, partições por grupo, fine-tuning,
avaliação, benchmark, exportação e o contrato de sincronização com o backend.

O [piloto com o vídeo da Raiar](docs/docs/sprint-1/piloto-video-raiar.md) registra a
extração de 30 quadros PNG e os testes automáticos com SAHI.
Os resultados detalhados estão em [src/raiarnet/reports/raiar-video-pilot.md](src/raiarnet/reports/raiar-video-pilot.md).

```bash
uv run --frozen pytest
uv run --frozen ruff check src
uv run --frozen ruff format --check src
```

Os pesos e as imagens são baixados ou fornecidos localmente e não entram no Git.
Treinamento próprio, calibração na Raiar e homologação na Raspberry Pi dependem
das imagens revisadas e do dispositivo real. O dashboard é uma integração posterior
que poderá consumir os registros estruturados do módulo.

## Modelo construído do zero (RaiarNet)

Identificação e contagem direta de aves em N0, N1 e N2, escritas do zero em
PyTorch em `src/raiarnet/` (`preprocessing`, `models`, `training`, `evaluation`,
`labeling` e `baseline`). Execute os comandos dentro de `src/raiarnet/`:

```bash
python -m training.train_raiarnet --name r1 --iters 3000
python -m models.predict --source video.mp4 --weights runs/raiarnet/r1/best.pt --out outputs/c1
python -m evaluation.benchmark --raiarnet runs/raiarnet/r1/best.pt
```

O processo completo e os resultados estão na seção
[Modelo de visão computacional](docs/docs/sprint-2/visao-computacional/index.mdx).
