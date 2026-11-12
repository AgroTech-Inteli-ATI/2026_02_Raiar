# Backend Raiar

API HTTP em Node.js 22+ e TypeScript, com PostgreSQL (local ou Supabase).
As dependencias sao independentes das bibliotecas de visao computacional.

## Executar localmente

Na pasta `src/backend`, no PowerShell:

```powershell
npm ci
Copy-Item .env.exemplo .env
node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))"
```

Edite `.env`: configure `DATABASE_URL` e substitua os dois tokens por segredos distintos.
O comando Node gera um segredo; execute-o novamente para obter o segundo.
Os valores de exemplo dos tokens sao recusados pelo servidor.

Se nao houver um banco de desenvolvimento, inicie o Docker Desktop e execute:

```powershell
docker compose up -d database
npm run migrate
npm run dev
```

O Compose fornece somente o PostgreSQL local, em `127.0.0.1:5432`; a API roda pelo Node
em `http://127.0.0.1:3000`. A senha padrao `raiar_local` serve apenas ao desenvolvimento.
Se alterar `POSTGRES_PASSWORD`, ajuste tambem `DATABASE_URL`.
Com um banco ja disponivel, pule o comando Docker.

Para Supabase, use uma connection string PostgreSQL direta ou do pooler em modo session,
com `DATABASE_SSL=true` e certificado confiavel. Nao use a URL HTTP de REST como `DATABASE_URL`.
Configure TLS por `DATABASE_SSL`; remova parametros `sslmode`/`sslcert`/`sslkey`/`sslrootcert`
da connection string para nao sobrescrever a verificacao de certificado do driver.
Se o provedor usar uma CA especifica, configure `NODE_EXTRA_CA_CERTS` antes de iniciar o Node.

## Migracoes e conexao

`src/database.ts` cria o pool PostgreSQL, limita conexoes e tempos de espera, usa parametros
nas consultas e garante rollback e liberacao do cliente em transacoes.

`npm run migrate` cria uma base vazia ou atualiza as tabelas existentes. Os SQLs canonicos
continuam em `../database/`; nao ha uma segunda copia dentro do backend.
O comando aplica `002`, `003` e `004` em ordem, com transacao, trava de migracao e checksums.
Uma instalacao anterior completa de `002` e reconhecida sem recriar suas tabelas.
Esquemas parciais ou migracoes registradas com checksum diferente interrompem a operacao.
O controle fica em `backend_internal.migration`, fora das tabelas publicas da API.

Aplique com um usuario autorizado a alterar o esquema. Para executar a API em producao,
prefira uma credencial de banco com apenas os acessos necessarios. As rotas nao aplicam DDL
nem migram o banco automaticamente na inicializacao.

```powershell
npm run check
npm test
npm run build
npm start
```

Depois do build, `npm run migrate:prod` executa as migracoes compiladas.
Os testes padrao usam PostgreSQL embarcado (PGlite), sem exigir Docker ou Supabase.
O teste do driver `pg` roda adicionalmente quando `TEST_DATABASE_URL` aponta para um banco
de teste vazio e exclusivo; o CI configura esse banco. Nunca use producao nessa variavel.

## Autenticacao

- `RAIAR_API_TOKEN`: credencial de servico com acesso de gestor aos cadastros e consultas.
  Use em integracoes de servidor e testes; nao embuta esse segredo no frontend.
- `RAIAR_SYNC_TOKEN`: credencial exclusiva de `POST /ingest-analyses`.
- Opcionalmente configure `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY` para receber JWT de
  usuarios do Supabase Auth. O backend valida o token no provedor a cada requisicao e le
  `app_metadata.role`: `gestor` ou `operador`. `user_metadata` nao concede permissoes.
  A equipe administra os papeis pelo Supabase; nao ha rota de autopromocao de usuario.

Envie `Authorization: Bearer VALOR`. Gestor pode manter os quatro cadastros; operador
consulta todos e altera dispositivos/cameras. A unica rota publica e `GET /health`.
`GET /ready` verifica acesso ao banco e exige autenticacao; `GET /me` retorna identidade e papel.
Use HTTPS e mesma origem/reverse proxy na publicacao; o backend nao abre CORS irrestrito.

## Rotas

| Recurso | Operacoes |
| --- | --- |
| `/raspberries` | GET com filtros `active`, `limit`, `offset`; POST |
| `/aviaries` | GET com `current_lot_id`, `limit`, `offset`; POST |
| `/cameras` | GET com `raspberry_id`, `aviary_id`, `active`, `limit`, `offset`; POST |
| `/lots` | GET com `archived`, `limit`, `offset`; POST |
| Cada cadastro `/:id` | GET e PATCH; nao ha exclusao fisica |
| `/ingest-analyses` | POST no contrato `schema_version: 1` do sincronizador existente |
| `/analyses` | GET com `camera_id`, `aviary_id`, `lot_id`, `status`, `from`, `to`, `limit`, `offset` |
| `/analyses/:id` | GET da analise, contagens por nivel e payload completo |

Listas retornam `{data: [...], pagination: {limit, offset, has_more}}`, ordenadas por ID nos
cadastros e por captura/processamento/ID nas analises. O limite padrao e 50 e o maximo e 100.
Os filtros temporais usam captura: `from` inclusivo e `to` exclusivo, ambos com fuso.
Capturas de horario desconhecido ficam fora dos filtros temporais e aparecem no fim da lista sem filtro.

Exemplo de cadastro:

```powershell
$headers = @{ Authorization = "Bearer $env:RAIAR_API_TOKEN" }
$body = @{
  name = 'Lote piloto'
  age_days_reference = 10
  age_reference_date = '2026-11-01'
  age_reference_source = 'Registro informado pela Raiar'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:3000/lots `
  -Headers $headers -ContentType application/json -Body $body
```

O servidor carrega `.env` para si; o exemplo pressupoe que o token tambem esteja definido
em `$env:RAIAR_API_TOKEN` na sessao PowerShell.
Cadastre dispositivo, lote e aviario antes da camera, usando os IDs retornados pelo servidor.

- Dispositivo: `name`, `hostname`; opcionais `model`, `active` (padrao `true`).
- Aviario: `name`, `number` positivo, `type` (`rearing`/`normal`); opcionais `box_identifiers`,
  `registration_date`, `timezone` (padrao `America/Sao_Paulo`) e `current_lot_id`.
- Camera: `raspberry_id`, `aviary_id`; opcionais `name`, `model`, `active` (padrao `true`).
- Lote: `name`; opcionais os tres campos de idade e `archived_at` (instante com fuso).
  Idade, data e origem devem estar todos preenchidos ou todos nulos.

PATCH altera somente campos enviados. `active=false` desativa; `archived_at=null` restaura
um lote arquivado. Uma nova referencia de idade pode ser enviada completa, ou atualizada
parcialmente se o registro final continuar consistente.
Entradas com campos desconhecidos, nomes vazios, boxes repetidos, fuso inexistente ou idade
negativa sao recusadas. Respostas: 201 criacao; 200 consulta/atualizacao; 401 autenticacao;
403 perfil; 404 inexistente; 409 duplicidade/referencia; 422 validacao; 503 indisponibilidade.
Erros usam `{error: {code, message, details?}}`, sem SQL ou credenciais.

## Conectar o no de borda

Mantenha o pipeline existente e aponte `RAIAR_SYNC_URL` para
`https://SEU_BACKEND/ingest-analyses`, usando o mesmo `RAIAR_SYNC_TOKEN` no no e no servidor.
O sincronizador exige HTTPS fora de localhost. `camera_id` deve corresponder ao ID numerico
de uma camera cadastrada. A chave de servico do Supabase nao vai para o no.

A resposta preserva `accepted_analysis_ids` e `rejected`. Itens invalidos sao isolados;
somente IDs persistidos sao confirmados. Reenvio identico nao duplica analise nem niveis;
mesmo ID com outro conteudo retorna `analise_id_conflitante`. Novas analises de uma camera
ou dispositivo desativado sao recusadas; reenvios identicos ja gravados continuam confirmados.
Os motivos incluem `item_invalido`, `camera_nao_cadastrada`, `camera_inativa` e `dispositivo_inativo`.

A Edge Function em `../../supabase/functions/` permanece como alternativa de entrada e usa
a mesma funcao SQL atualizada por `004`. A validacao completa de coerencia dos resultados
e feita nesta API; para utiliza-la, direcione o no ao backend.

## Limites desta entrega

O token de sincronizacao ainda e compartilhado entre os nos, sem autorizacao por camera.
A funcao SQL ainda associa ao lote atual no recebimento: antes de trocar lotes com fila
pendente, implementar o historico de ocupacao ou esvaziar e conferir a fila.
Esta entrega cobre os quatro cadastros aprovados, ingestao e consulta de resultados.
Configuracao remota de coleta, agregacao historica, telemetria, geracao de alertas e
retencao de imagens nao foram implementadas.
