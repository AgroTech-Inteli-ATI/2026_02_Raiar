---
title: Falhas e do teste para a produção
sidebar_label: Falhas e produção
sidebar_position: 6
description: Guia para quem baixa o projeto pela primeira vez, com o mapa de falhas e a lista do que muda do ambiente de teste para a produção.
---

# Falhas e do teste para a produção

Esta página é para quem baixa o projeto pela primeira vez e precisa de três coisas: colocá-lo para funcionar no ambiente de teste, saber onde olhar quando algo der errado e saber exatamente o que trocar para ir ao aviário. Para entender a simulação do DVR com uma analogia simples, leia antes [DVR simulado e teste na prática](./dvr-simulado-e-teste-na-pratica.md). Os termos técnicos estão no [glossário](../sprint-1/glossario.md).

## Do clone à primeira análise

1. **Instalar o necessário.** Docker com Compose para rodar o sistema. Para rodar os testes do código, Python de 3.11 a 3.13 e o `uv`, como indica o [README](https://github.com/AgroTech-Inteli-ATI/2026_02_Raiar#readme).
2. **Rodar os testes do código** na raiz do repositório. Eles não precisam de câmera nem de banco:

   ```bash
   uv sync --frozen
   uv run --frozen pytest
   ```

3. **Subir a simulação do DVR**, seguindo [Como repetir a simulação](./dvr-simulado-e-teste-na-pratica.md#como-repetir-a-simulação). Ao fim, o log do `vision` mostra uma linha `camera=1 status=valido` a cada 5 s.
4. **Preparar o banco**, se quiser testar o envio. Em um Postgres vazio, aplique `src/database/schema.sql` e `src/database/migrations/002_analises.sql`, cadastre um Raspberry Pi, um aviário e uma câmera, e use o `camera.id` em `RAIAR_CAMERA_ID`. O passo a passo no Supabase está em [Integração do nó de borda com o banco de dados](./integracao-no-banco.md#como-colocar-no-ar).

## Como ver o que está acontecendo

Estes comandos mostram o estado do sistema sem alterar nada. Rode-os na pasta do repositório; troque `/opt/raiar/data` pelo valor de `RAIAR_DATA`, se for outro.

**Tabela 1 – Comandos de diagnóstico**

| O que você quer saber | Comando |
| --- | --- |
| Os containers estão de pé? | `docker compose --profile captura ps -a` |
| O vigia está capturando? | `docker compose --profile captura logs --tail 30 vision` |
| O entregador está enviando? | `docker compose --profile captura logs --tail 30 sync` |
| Quais quedas de câmera foram registradas? | Comando abaixo, que lista os eventos do histórico |
| Quantas análises estão pendentes, por câmera? | Segundo comando abaixo |
| O cartão SD está enchendo? | `df -h /opt/raiar/data && du -sh /opt/raiar/data/*` |
| A função do Supabase responde? | `curl -i -X POST "$RAIAR_SYNC_URL" -H "Authorization: Bearer $RAIAR_SYNC_TOKEN" -H "Content-Type: application/json" -d '{"schema_version":1,"analyses":[]}'` (deve devolver `200`) |

Fonte: elaborado pelos autores (2026).

Eventos do histórico (tipos `captura_iniciada`, `camera_queda`, `camera_recuperada`, `falha_captura`):

```bash
docker run --rm --entrypoint python -v /opt/raiar/data:/d:ro raiar/vision:0.1.0 -c "
import sqlite3
c = sqlite3.connect('file:/d/results.sqlite3?mode=ro', uri=True)
for row in c.execute('SELECT occurred_at, type, payload FROM events ORDER BY occurred_at DESC LIMIT 20'):
    print(row)"
```

Análises ainda não aceitas pelo banco, por câmera:

```bash
docker run --rm --entrypoint python -v /opt/raiar/data:/d:ro raiar/vision:0.1.0 -c "
import sqlite3
c = sqlite3.connect('file:/d/results.sqlite3?mode=ro', uri=True)
for row in c.execute('SELECT json_extract(a.payload, \"\$.camera_id\") AS camera, count(*) FROM analyses a LEFT JOIN sync_receipts s ON a.analise_id = s.analise_id WHERE s.analise_id IS NULL GROUP BY 1'):
    print(row)"
```

## Mapa de falhas {#mapa-de-falhas}

Cada linha traz a mensagem como ela aparece, a causa mais provável e o lugar onde corrigir. As mensagens do `vision` aparecem nos logs do container e as do `sync`, nos logs do serviço `sync`.

**Tabela 2 – Falhas do vigia (`vision`)**

| Mensagem ou sintoma | Causa provável | Onde corrigir |
| --- | --- | --- |
| `camera=X queda: tentativa N: Fonte de vídeo não abriu: URL` | URL, usuário, senha ou canal errados; DVR desligado; rede fora; RTSP desabilitado no DVR. A senha não aparece na mensagem | `RAIAR_CAMERA_SOURCE` no `.env` ou `source` no `cameras.yaml`. Teste a URL com o `ffprobe` da página [DVR simulado](./dvr-simulado-e-teste-na-pratica.md) |
| `camera=X queda: ... Leitura falhou ou o stream terminou` | O stream abriu e depois caiu: rede instável ou DVR reiniciou | Rede e DVR. O vigia reconecta sozinho, com espera crescente de 1 s até 60 s |
| `camera=X recuperada: voltou a entregar quadros` | Não é falha: a câmera voltou | Nada |
| Container "Up", sem nenhuma linha `camera=` e sem `queda` | O modelo ainda está carregando (alguns segundos na partida) ou a câmera abriu, mas não entrega quadros novos | Aguarde; se persistir, `docker compose logs vision` e o teste com `ffprobe` |
| Container reiniciando em loop, com `Erro:` nos logs | Erro de configuração, listado abaixo | O item da mensagem |
| `Erro: Informe --cameras ou defina RAIAR_CAMERA_SOURCE.` | Não há `config/cameras.yaml` nem `RAIAR_CAMERA_SOURCE` | `.env` ou `/opt/raiar/config/cameras.yaml` |
| `Erro: Câmera X: intervalo mínimo é 5 s` | `interval_seconds` ou `RAIAR_INTERVAL_SECONDS` menor que 5 | O valor do intervalo. O nó não acompanha menos que isso |
| `Erro: Câmera repetida: X` / `Cada câmera precisa de 'id' e 'source'` / `cameras.yaml deve ter a lista 'cameras'...` | Erro de formato no `cameras.yaml` | Compare com o exemplo da página [DVR simulado](./dvr-simulado-e-teste-na-pratica.md#escolher-quais-câmeras-o-raspberry-pi-usa) |
| `Erro: Modelo não preparado. Execute: chicken-yolo prepare-model poultryvision` | `MODELO` é diferente do modelo com que a imagem foi construída | `MODELO` no `.env` e reconstrução com `--build-arg MODELO=...` |
| Análises com `status=imagem_inadequada` e motivo `A câmera do quadro não corresponde à calibração das zonas.` | O `camera_id` do arquivo de zonas é diferente do `id` da câmera | `camera_id` dentro do arquivo de zonas |
| `imagem_inadequada` com `Proporção da imagem diferente da referência das zonas.` | O DVR mudou a resolução ou o canal (por exemplo, trocou o *substream*) | Recalibrar as zonas para a imagem atual |
| `Erro: Zonas são um exemplo ou ainda não foram calibradas.` | O arquivo de zonas não tem `calibrated: true` | Arquivo de zonas |
| `status=imagem_inadequada` com motivo de brilho ou nitidez | Câmera escura, estourada ou fora de foco | Câmera e `quality` em `inference.yaml` |

Fonte: elaborado pelos autores (2026), a partir de `src/chicken_yolo/live.py`, `zones.py` e `cli.py`.

**Tabela 3 – Falhas do entregador (`sync`) e do banco**

| Mensagem ou sintoma | Causa provável | Onde corrigir |
| --- | --- | --- |
| `Erro: Endpoint deve usar HTTPS; HTTP é permitido apenas em localhost.` | `RAIAR_SYNC_URL` com `http://` fora de `localhost` | `RAIAR_SYNC_URL` |
| `Erro: ... Connection ...` | Sem internet ou URL errada. Nada se perde: tudo fica pendente e vai quando a rede volta | Rede e `RAIAR_SYNC_URL` |
| `401 Client Error` | O token do nó é diferente do segredo da função | `RAIAR_SYNC_TOKEN` no `.env` e `supabase secrets set RAIAR_SYNC_TOKEN=...` |
| `401` com `Invalid JWT` no corpo da resposta | A função foi publicada sem `--no-verify-jwt`, e o gateway do Supabase recusa um token que não é JWT | Republicar com `supabase functions deploy ingest-analyses --no-verify-jwt` |
| `500 Server Error` | O segredo `RAIAR_SYNC_TOKEN` não foi definido na função (a resposta é `token_not_configured`) | `supabase secrets set` e nova publicação. Use o `curl` da Tabela 1 para ver o corpo da resposta |
| `502 Server Error` | O banco recusou a chamada: migração `002` não aplicada, tabela ausente ou erro de permissão. O detalhe fica só nos logs da função | Aplicar `002_analises.sql`; logs da função no painel do Supabase |
| `400 Client Error` | Lote malformado ou com mais de 500 análises | Versão do nó e da função |
| `sync` com `"pending"` maior que zero e lista `"rejected"` com `camera_nao_cadastrada` | O `camera_id` das análises não existe na tabela `camera` | Cadastrar a câmera no banco, ou corrigir `RAIAR_CAMERA_ID`. As pendentes são aceitas no ciclo seguinte |
| `rejected` com `invalid input syntax for type integer: "camera-1"` | `RAIAR_CAMERA_ID` não é um número | `RAIAR_CAMERA_ID` ou o `id` no `cameras.yaml` |
| `rejected` com erro de chave estrangeira ou `uuid` | Versão do esquema diferente da esperada | Aplicar `schema.sql` e `002` na mesma versão do repositório |
| `Erro: Servidor deve confirmar apenas IDs presentes no lote enviado.` | A função devolveu um identificador que o nó não enviou | `ingest_analyses` no banco. Não deve acontecer com a versão do repositório |

Fonte: elaborado pelos autores (2026), a partir de `src/chicken_yolo/sync.py`, `supabase/functions/ingest-analyses/handler.ts` e `src/database/migrations/002_analises.sql`.

Quando um lote traz mais de 10 recusas, o `sync` mostra os motivos das 10 primeiras e o total em `rejected_count`.

## Do teste para a produção

A lista abaixo reúne tudo o que muda ao sair do notebook com o DVR simulado para o Raspberry Pi no aviário. Quem não trocar um item continua em modo de teste sem perceber.

**Tabela 4 – O que trocar para ir à produção**

| Item | No teste | Na produção | Onde mudar |
| --- | --- | --- | --- |
| Fonte de vídeo | `rtsp://dvr-sim:8554/camera1` | `rtsp://USUARIO:SENHA@IP_DO_DVR:554/CAMINHO` | `RAIAR_CAMERA_SOURCE` no `.env`, ou `source` no `cameras.yaml` |
| DVR simulado | Perfis `captura` e `simulacao` | Só o perfil `captura` | Comando `docker compose ... up -d` |
| Vários canais | Uma câmera pelo `.env` | `cameras.yaml` com uma entrada por canal | `/opt/raiar/config/cameras.yaml` |
| ID da câmera | `1` | O `camera.id` cadastrado no banco, um número | `RAIAR_CAMERA_ID` ou `id` no `cameras.yaml` |
| Intervalo | 5 s | 5 s ou mais, conforme o número de câmeras | `RAIAR_INTERVAL_SECONDS` ou `interval_seconds` |
| Modelo | `coco`, só para validar a infraestrutura | `poultryvision`; o consumo de memória no Raspberry Pi ainda não foi medido | `MODELO` no `.env` e reconstrução da imagem com `--build-arg MODELO=poultryvision` |
| Zonas dos níveis | Nenhuma: as contagens por nível saem vazias | Um arquivo calibrado por câmera | `zones` no `cameras.yaml` ou `RAIAR_ZONES`, com o arquivo em `/opt/raiar/config` |
| Endereço do banco | Servidor local ou valor de exemplo | `https://PROJECT_REF.supabase.co/functions/v1/ingest-analyses` | `RAIAR_SYNC_URL` |
| Token | Qualquer valor | Segredo forte, igual ao da função, com o `.env` em permissão `600` | `RAIAR_SYNC_TOKEN` e `supabase secrets` |
| Banco | Postgres de teste | Supabase com `schema.sql`, `002_analises.sql`, Raspberry Pi, aviário e câmeras cadastrados | Painel ou SQL do Supabase |
| Função de ingestão | Servidor de teste | Publicada com `--no-verify-jwt` | `supabase functions deploy` |
| Pasta de dados | Qualquer pasta | `/opt/raiar/data`, de propriedade do usuário 1000, no cartão SD | `RAIAR_DATA` |
| Arquitetura da imagem | `x86_64` do notebook | `arm64`, construída no próprio Raspberry Pi | [Entrega e atualização](./integracao-containers-no-no-de-borda.md#entrega-e-atualização) |
| Câmera USB | Não usada | `/dev/video0` com `compose.usb.yaml` e `VIDEO_GID` | `.env` e o segundo arquivo do Compose |
| Lote | Vazio | Opcional: o banco usa o lote atual do aviário | `RAIAR_LOTE_ID` |

Fonte: elaborado pelos autores (2026), a partir de `compose.yaml`, `.env.exemplo` e das páginas da Sprint 3.

Depois de trocar os itens, repita os passos da seção "Como testar na prática com o DVR de verdade" da página [DVR simulado](./dvr-simulado-e-teste-na-pratica.md#como-testar-na-prática-com-o-dvr-de-verdade), começando com um único canal.

## Limites conhecidos

Estes pontos não são erros que aparecem em mensagem. Quem opera o sistema precisa conhecê-los.

- **O histórico local não tem limite.** Os arquivos `results.jsonl` e `counts.csv` e o SQLite crescem a cada análise e nada os apaga. O ritmo de crescimento por dia não foi medido, e o cartão SD tem 29 GB. Confira o espaço periodicamente com o comando da Tabela 1.
- **O relógio do Raspberry Pi não tem bateria.** Depois de um reinício sem rede, `capturado_em` pode sair com a hora errada até a rede voltar.
- **Recusas não expiram.** Uma análise de uma câmera que nunca for cadastrada fica pendente para sempre, e muitas delas podem ocupar o lote de 100 e atrasar as demais.
- **A lista de câmeras só é lida na partida.** Mudou o `cameras.yaml`? Reinicie o `vision`.
- **O lote da análise é o lote atual do aviário no momento do recebimento**, e não o de quando a imagem foi feita.
- **As quedas de stream ficam no histórico, mas os eventos não são enviados ao banco.** Quem quiser vê-las precisa consultar o nó.
- **O `raiarnet` não faz parte desta integração**, pelos motivos descritos em [Containers no nó de borda](./integracao-containers-no-no-de-borda.md#limitações-do-raiarnet).
