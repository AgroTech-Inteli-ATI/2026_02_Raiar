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

## API e estado da integração

Sem `VITE_API_BASE_URL`, o frontend usa registros demonstrativos. O adaptador está preparado para `GET {VITE_API_BASE_URL}/alerts`, com resposta `{"alerts": [...]}`, e aplica os filtros de câmera e data no próprio frontend.

Essa rota ainda não existe no backend integrado. O backend oferece `GET /analyses`, que exige autenticação e retorna `{ "data": [...], "pagination": {...} }`; análises não são alertas e não devem ser convertidas automaticamente em alertas. Até que a regra de geração, a rota, os campos e a autenticação do dashboard sejam acordados, mantenha `VITE_API_BASE_URL` vazia para ver a demonstração. Se definir a variável agora, a consulta falhará.

Variáveis `VITE_*` são incluídas no JavaScript do navegador. Nunca coloque `RAIAR_API_TOKEN`, `RAIAR_SYNC_TOKEN`, chave de serviço, senha ou outro segredo em `.env.local` ou no bundle do frontend. O frontend ainda não implementa login nem envia bearer token. A integração segura depende de autenticação de usuário ou proxy de mesma origem acordado com o backend.

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
