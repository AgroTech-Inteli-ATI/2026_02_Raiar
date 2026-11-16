# Painel Raiar Orgânicos

Frontend em React, TypeScript e Vite para acompanhar os registros de alerta do aviário. O build gera arquivos estáticos. A API é acessada pelo proxy do servidor de desenvolvimento, que mantém o token fora do navegador.

## Requisitos

Node.js 20.19 ou superior e npm para o frontend. O backend requer Node.js 22 ou superior. Para executar o banco local pelo Compose, também é necessário Docker Desktop com o plugin Docker Compose.

## Executar frontend e backend localmente

O banco local definido em `src/backend/compose.yaml` publica somente em `127.0.0.1:5432`. Abra um terminal para iniciar o PostgreSQL:

```powershell
cd src/backend
docker compose up -d database
```

No mesmo terminal, crie a configuração local do backend e edite os valores. O arquivo `.env` é ignorado pelo Git:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.exemplo .env }
notepad .env
npm install
```

Para esse ambiente local, configure `DATABASE_URL` para `postgres://raiar:raiar_local@127.0.0.1:5432/raiar`, `DATABASE_SSL=false`, `HOST=127.0.0.1` e `PORT=3000`. Gere valores aleatórios diferentes para `RAIAR_API_TOKEN` e `RAIAR_SYNC_TOKEN`, cada um com ao menos 32 caracteres. Não reutilize credenciais reais. Depois, aplique as migrações e inicie o backend:

```powershell
npm run migrate
npm run dev
```

Em outro terminal, configure e inicie o frontend:

```powershell
cd src/frontend
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
notepad .env.local
npm install
npm run dev
```

Em `.env.local`, mantenha `VITE_API_BASE_URL=/api`, use `RAIAR_BACKEND_URL=http://127.0.0.1:3000` e copie o mesmo valor local de `RAIAR_API_TOKEN` para `RAIAR_DEV_API_TOKEN`. A aplicação fica em `http://localhost:5173/`. Não registre os valores dos tokens em terminal, documentação, logs ou capturas de tela.

Se o Docker não estiver disponível, o frontend ainda abre em modo demonstrativo. O backend precisa de um PostgreSQL local com as migrações aplicadas; sem o banco, não será possível validar consultas reais.

## Como o proxy protege o token

`VITE_API_BASE_URL` contém somente o caminho relativo `/api`. O `vite.config.ts` lê `RAIAR_BACKEND_URL` e `RAIAR_DEV_API_TOKEN` no processo Node, valida que o destino é HTTP em loopback e encaminha as requisições ao backend local. O proxy remove o prefixo `/api` e inclui o bearer token no cabeçalho. Nenhum segredo é lido pelo código React ou incluído no bundle.

O proxy existe somente no servidor de desenvolvimento Vite. Em produção, o frontend estático precisa de proxy reverso HTTPS de mesma origem para o backend e autenticação de usuário. O backend atual aceita token de serviço ou, se configurado, JWT de usuário do Supabase. O dashboard ainda não implementa login; não publique o token de serviço no navegador.

## Integração disponível

Quando `VITE_API_BASE_URL=/api`, o dashboard busca todas as páginas de `GET /cameras` e `GET /aviaries`, respeitando `limit`, `offset` e `pagination.has_more`. Os nomes disponíveis são usados nos filtros e rótulos. O cabeçalho consulta `GET /health`, que não exige autenticação.

O backend não oferece `GET /alerts`. Portanto, os alertas continuam sendo três registros demonstrativos. Se `/alerts` responder 404, o painel informa que os avisos não estão disponíveis nesse ambiente e mantém os exemplos com o aviso demonstrativo. Erros de rede, autenticação ou indisponibilidade do serviço são mostrados em português e podem ser tentados novamente. `GET /analyses` não é convertido em alerta.

O módulo de distribuição por câmera ainda não está registrado no backend. A integração precisa adicionar esse registro no `app.ts` e definir os limites operacionais antes de usar o resultado como mapa.

## Verificar tipos e gerar o site

```powershell
cd src/frontend
npm run typecheck
npm run build
npm run preview
```

`npm run build` gera arquivos em `src/frontend/dist/`. O preview fica disponível em `http://localhost:4173/`. O proxy de desenvolvimento não é incluído no build estático.

## Estrutura

```text
src/frontend/
├── public/                 # Arquivos estáticos públicos, como o logo
├── src/
│   ├── services/           # Cliente da API e repositórios de dados
│   ├── styles/             # Estilos da tela e tokens visuais
│   ├── App.tsx             # Tela principal do painel
│   └── main.tsx            # Inicialização React
├── index.html              # Entrada do Vite
├── package.json            # Dependências e comandos independentes
└── vite.config.ts          # Servidor de desenvolvimento, proxy e build
```

Os tokens de cores, tipografia, bordas e espaçamentos ficam em `src/styles/dashboard-tokens.css`.
