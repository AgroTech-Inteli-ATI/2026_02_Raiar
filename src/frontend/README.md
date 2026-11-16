# Painel Raiar Orgânicos

Aplicação estática de frontend para acompanhar alertas do aviário. O site é compilado em HTML, CSS e JavaScript e não inclui servidor próprio nem credenciais da API.

## Requisitos

Node.js 20.19 ou superior e npm. O repositório foi verificado com Node.js 24.13.0.

## Instalar e rodar

Na raiz do repositório, execute:

```powershell
cd src/frontend
npm install
npm run dev
```

O Vite abre o site em `http://localhost:5173`. A porta é diferente da usada pelo Docusaurus.

## Verificar tipos e gerar o site

```powershell
cd src/frontend
npm run typecheck
npm run build
npm run preview
```

`npm run build` gera os arquivos estáticos em `src/frontend/dist/`. A pasta `dist/` pode ser publicada em um servidor estático. `npm run preview` serve esse build localmente na porta 4173.

## API

Copie `.env.example` para `.env.local` e defina `VITE_API_BASE_URL` com a URL base pública da API. Sem essa variável, o frontend usa registros demonstrativos. Variáveis `VITE_*` são incluídas no JavaScript do navegador; portanto, essa variável pode conter somente uma URL pública, nunca um token, chave ou senha.

O contrato esperado para a integração é `GET {VITE_API_BASE_URL}/alerts`, com uma resposta no formato `{"alerts": [...]}`. Cada item usa `id`, `camera_id`, `aviary_id`, `datetime` e `alarm_type`. Os filtros podem ser combinados com parâmetros `camera_id`, `date_from` e `date_to`. O contrato precisa ser confirmado pelo responsável pelo backend antes da integração.

## Estrutura

```text
src/frontend/
├── public/                 # Arquivos estáticos públicos, como o logo
├── src/
│   ├── services/           # Acesso a dados e adaptador da API
│   ├── styles/             # Estilos da tela e tokens visuais
│   ├── App.tsx             # Tela principal do painel
│   └── main.tsx            # Inicialização React
├── index.html              # Entrada do Vite
├── package.json            # Dependências e comandos independentes
└── vite.config.ts          # Servidor de desenvolvimento e build
```

Os tokens de cores, tipografia, bordas e espaçamentos ficam em `src/styles/dashboard-tokens.css`.
