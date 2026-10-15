# Raiar Orgânicos — AgroTech Inteli

Projeto da AgroTech Inteli com a Raiar Orgânicos para monitorar, por visão computacional, a distribuição das aves visíveis nos níveis do Jump Start durante a recria.

## Estrutura do repositório

```text
.
├── docs/                   # Site de documentação (Docusaurus)
│   ├── docs/               # Páginas em Markdown/MDX, organizadas por sprint
│   ├── src/css/            # Estilos globais (paleta Raiar e formatação ABNT)
│   └── static/img/         # Imagens usadas nas páginas
├── src/chicken_yolo/        # Detecção, níveis, dataset, treino e avaliação
│   └── notebooks/          # Execução visual e comparação das detecções
├── configs/                # Configurações de inferência, treino e câmeras
├── data/                   # Dados locais, excluídos do Git
├── models/                 # Registro dos modelos e pesos locais
├── outputs/                # SQLite, CSV, JSON e imagens anotadas
├── runs/                   # Resultados dos treinamentos
├── reports/                # Relatórios; execuções em generated/ são locais
├── tests/                  # Testes do pipeline e das regras dos dados
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
Os resultados detalhados estão em [reports/raiar-video-pilot.md](reports/raiar-video-pilot.md).

```bash
uv run --frozen pytest
uv run --frozen ruff check src tests
uv run --frozen ruff format --check src tests
```

Os pesos e as imagens são baixados ou fornecidos localmente e não entram no Git.
Treinamento próprio, calibração na Raiar e homologação na Raspberry Pi dependem
das imagens revisadas e do dispositivo real. O dashboard é uma integração posterior
que poderá consumir os registros estruturados do módulo.

## Modelo construído do zero (RaiarNet)

Identificação e contagem direta de aves em N0, N1 e N2, escritas do zero em
PyTorch em `src/` (`preprocessing`, `models`, `training`, `evaluation`,
`labeling` e `baseline`). Execute os comandos dentro de `src/`:

```bash
python -m training.train_raiarnet --name r1 --iters 3000
python -m models.predict --source video.mp4 --weights ../models/trained/raiarnet-r1.pt --out ../outputs/c1
python -m evaluation.benchmark --raiarnet ../models/trained/raiarnet-r1.pt
```

O processo completo e os resultados estão na seção
[Modelo de visão computacional](docs/docs/sprint-2/visao-computacional/index.mdx).
