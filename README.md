# Raiar Orgânicos — AgroTech Inteli

Projeto da AgroTech Inteli com a Raiar Orgânicos para monitorar, por visão computacional, a distribuição das aves visíveis nos níveis do Jump Start durante a recria.

## Estrutura do repositório

```text
.
├── docs/                   # Site de documentação (Docusaurus)
│   ├── docs/               # Páginas em Markdown/MDX, organizadas por sprint
│   ├── src/css/            # Estilos globais (paleta Raiar e formatação ABNT)
│   └── static/img/         # Imagens usadas nas páginas
├── src/raiar_vision/        # Detecção, níveis, dataset, treino e avaliação
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
uv run --frozen raiar-vision prepare-model poultryvision
```

Copie uma imagem para `data/raw/imagem.jpg` e execute:

```bash
uv run --frozen raiar-vision predict --source data/raw/imagem.jpg
```

O YOLO identifica as aves automaticamente com os pesos pré-treinados. Não é
necessário desenhar caixas nem fornecer rótulos para executar as predições.
O mesmo comando aceita vídeos com `--source data/raw/video.mp4`.

O comando informa a pasta que contém `results.jsonl`, `counts.csv` e as imagens
anotadas. O histórico local fica em `outputs/results.sqlite3`.
O modelo padrão é o [PoultryVision](https://huggingface.co/Williamsanderson/PoultryVision),
pré-treinado para `chicken` e `egg`; o pipeline aceita somente as classes de aves
configuradas. Para comparar com a variante leve e genérica:

```bash
uv run --frozen raiar-vision prepare-model coco
uv run --frozen raiar-vision predict --source data/raw/imagem.jpg --model coco
```

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
