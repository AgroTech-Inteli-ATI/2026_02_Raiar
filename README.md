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

O Compose na raiz configura os serviços `vision` e `sync`. A imagem `raiar/vision` é
construída a partir de `sprint-3/docker/chicken-yolo/Dockerfile`; o nome `raiar-vision`
é usado como comando para evitar conflito com a CLI do Ultralytics. Os pesos do modelo
selecionado por `MODELO` (por padrão, `coco`) são baixados durante o build e ficam na
imagem, sem volume que os sobrescreva. O Dockerfile da RaiarNet em `sprint-3/docker/raiarnet/Dockerfile` produz uma imagem separada e não é um serviço do Compose atual. Seu checkpoint `best.pt` não está no Git nem é baixado durante o build.

### Configuração local

Copie `.env.exemplo` para `.env` e edite os valores. O arquivo `.env` contém a URL RTSP e
o token de sincronização: mantenha-o local, fora do Git, e restrinja suas permissões:

```bash
cp .env.exemplo .env
chmod 600 .env
```

Em produção, prepare os diretórios persistentes e pertencentes ao usuário `raiar` (UID
1000) no host:

```bash
sudo install -d -o raiar -g raiar -m 0750 /opt/raiar/data /opt/raiar/models
```

Copie o `best.pt` recebido ou produzido para `/opt/raiar/models/best.pt` no nó. O container recebe essa
pasta como `/opt/raiar/models`, somente para leitura. Os dados do SQLite e as saídas são
gravados em `/opt/raiar/data`, que não é `tmpfs` e sobrevive à recriação do container.

Para RTSP, `RAIAR_CAMERA_SOURCE` recebe a URL do DVR, por exemplo
`rtsp://USUARIO:SENHA@IP_DO_DVR:554/caminho/stream`. Cada canal do DVR deve ter seu próprio
`RAIAR_CAMERA_ID`. Prefira o substream em H.264 para reduzir o uso de CPU da Raspberry Pi;
o transporte RTSP está configurado para TCP pelo FFmpeg incluído no OpenCV. Não compartilhe
saídas de `docker compose config` sem remover as variáveis interpoladas, pois elas podem
conter credenciais.

### Build e execução

Valide a configuração e construa a imagem na arquitetura da máquina atual:

```bash
docker compose --env-file .env.exemplo config -q
docker compose build
```

O serviço `vision` fica no profile `captura` porque ainda não há captura ao vivo. Por padrão,
suba apenas a sincronização:

```bash
docker compose up -d sync
```

Para conferir o comando inofensivo do serviço de visão, habilite o profile explicitamente:

```bash
docker compose --profile captura run --rm vision
```

Ele mostra a ajuda e termina; não inicia leitura RTSP nem abre `/dev/video0`. A variável
`RAIAR_CAMERA_SOURCE` continua disponível no ambiente para a futura implementação. A URL não
é colocada nos argumentos do processo; ela continua no ambiente do container e pode ser vista
por quem tem acesso ao Docker no host. Não compartilhe `docker inspect` sem redigir esse valor.

O build do `chicken_yolo` usa PyTorch 2.14.1 e torchvision 0.29.1 exclusivamente do índice
CPU, sem consultar o PyPI para esses pacotes; o OpenCV da imagem é
`opencv-python-headless`. A medição disponível antes da correção do cache do uv foi de 4,62 GB;
ela não representa a imagem reconstruída com `UV_NO_CACHE=1`. O tamanho final após essa correção
precisa ser medido com `docker images`; não foi possível medi-lo neste ambiente. O serviço
`sync` envia os registros
pendentes a cada 300 segundos, usando o comando existente `raiar-vision sync`; falhas de
rede não encerram o loop. Defina uma versão em `RAIAR_TAG` para poder voltar a uma imagem
anterior.

`MODELO` seleciona os pesos embutidos durante o build. Se mudar o valor, reconstrua a imagem
antes de executá-la. Use o mesmo valor em `--model` ao chamar `predict` manualmente; trocar
somente o argumento de execução não baixa nem prepara pesos adicionais.

Exemplo de inferência local com uma imagem montada somente para leitura (defina `MODELO` com
o mesmo valor usado no build):

```bash
MODELO=coco
docker run --rm \
  -v "$PWD/data/raw:/inputs:ro" \
  -v "$PWD/outputs:/app/outputs" \
  raiar/vision:0.1.0 predict --source /inputs/imagem.jpg --model "$MODELO"
```

Depois do build, valide a imagem e o UID:

```bash
docker run --rm raiar/vision:0.1.0 --help
docker run --rm --entrypoint id raiar/vision:0.1.0
```

Troque `0.1.0` pela tag configurada em `RAIAR_TAG` quando for diferente.

Para a fonte USB, altere `RAIAR_CAMERA_SOURCE=/dev/video0` em `.env`, obtenha o GID do
grupo `video` com `getent group video | cut -d: -f3`, defina `VIDEO_GID` e inicie com o
override:

```bash
docker compose --profile captura -f compose.yaml -f compose.usb.yaml run --rm vision
```

O Compose principal não concede dispositivos. Somente o override USB concede acesso a
`/dev/video0` e ao GID informado. Como a captura ao vivo ainda não foi implementada, esse
comando apenas executa `--help`; ele não processa a câmera. Para conferir a configuração USB
sem iniciar serviços:

```bash
docker compose --env-file .env.exemplo -f compose.yaml -f compose.usb.yaml config -q
```

Esse exemplo usa a URL fictícia do arquivo de exemplo. Para validar o modo USB, sobreponha
a fonte no comando, sem colocar credenciais reais na linha de comando:

```bash
RAIAR_CAMERA_SOURCE=/dev/video0 docker compose --env-file .env.exemplo -f compose.yaml -f compose.usb.yaml config -q
```

Para construir em um computador x86 e levar uma imagem ARM64 à Raspberry Pi, use Buildx
com a arquitetura indicada, uma tag explícita e depois envie o arquivo comprimido por SSH:

```bash
docker buildx build --platform linux/arm64 --build-arg MODELO=coco -f sprint-3/docker/chicken-yolo/Dockerfile -t raiar/vision:0.1.0 --load .
docker save raiar/vision:0.1.0 | gzip | ssh raiar@IP_DA_RASPBERRY 'gunzip | docker load'
```

Na Raspberry Pi, defina a mesma `RAIAR_TAG` no `.env` e execute `docker compose up -d`.
Para revisar os limites de CPU e memória durante a operação, use `docker stats`.

### Estado da captura

O Compose já injeta `RAIAR_CAMERA_SOURCE`, `RAIAR_CAMERA_ID` e as opções FFmpeg sem
reconstruir a imagem. A implementação atual de `raiar-vision predict` ainda lê arquivos
locais, não URLs RTSP nem `/dev/video0`. Portanto, a captura ao vivo e a gravação periódica
em `/frames` dependem da próxima etapa de implementação. O serviço `vision` está no profile
`captura`, usa `--help` e `restart: "no"` até essa implementação para evitar ciclos de falha
e gravação excessiva de logs. O serviço `sync` permanece disponível por padrão.

### Estado dos testes desta entrega

Foi executado `git diff --check`. O ambiente de desenvolvimento usado para esta entrega não
tem Docker nem uv disponíveis, então não foi possível validar o Compose, construir ou medir a
imagem, conferir `torch.__version__`/`torch.version.cuda`, verificar a ausência do pacote
`nvidia`, nem executar os containers. Também não foram testados Raspberry Pi/ARM64, DVR,
câmera USB, inferência RaiarNet ou sincronização com backend real. A configuração de
healthcheck do `sync` permanece como pendência.

Os experimentos PIOFlow e YOLOPIO permanecem em notebooks e não fazem parte da imagem
`raiar/vision`.

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
