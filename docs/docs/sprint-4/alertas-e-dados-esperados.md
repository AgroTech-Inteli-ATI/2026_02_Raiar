---
title: Alertas e dados esperados
sidebar_label: Alertas e dados
sidebar_position: 2
description: Campos de alerta disponíveis e contrato proposto para alimentar o painel.
---

# Alertas e dados esperados

## Campos disponíveis

A tabela `public.alerts` define os campos `id`, `camera_id`, `aviary_id`, `datetime` e `alarm_type`. As relações permitem identificar a câmera e o aviário. A tela usa esses dados e não atribui severidade, estado de tratamento ou confirmação ao alerta, porque esses conceitos não estão no esquema atual [1].

O schema mantém `public.alerts`, mas o backend integrado não registra uma rota `/alerts` nem popula essa tabela durante a ingestão. A API recebe e consulta análises, e o README do backend identifica a geração de alertas como trabalho pendente [2]. Portanto, o formato da tabela, sozinho, não representa ainda um fluxo de alertas disponível para o painel.

## API disponível e diferença para o painel

O backend atual oferece `GET /analyses`, que exige `Authorization: Bearer ...`, aceita `camera_id`, `aviary_id`, `lot_id`, `status`, `lot_association_status`, `from`, `to`, `limit` e `offset`, e devolve `{ "data": [...], "pagination": { "limit", "offset", "has_more" } }`. Cada análise contém `id`, `camera_id`, `aviary_id`, `captured_at`, `processed_at`, `status`, contagens e uma lista `levels` com `level_id`, `bird_count` e `percent` [2]. Essa rota consulta análises, não alertas.

O adaptador do dashboard ainda espera `GET {VITE_API_BASE_URL}/alerts` com `{ "alerts": [...] }`. Esse contrato não corresponde a nenhuma rota implementada. Não configure `VITE_API_BASE_URL` para o backend atual esperando que os alertas apareçam: a requisição falhará. O frontend mantém os registros demonstrativos quando a variável está vazia. A integração real depende de o backend definir como uma análise vira alerta, incluir os campos necessários à tela e disponibilizar uma rota autenticada.

Se a decisão for exibir análises em vez de alertas, isso exige uma mudança explícita de produto e um adaptador para `/analyses`; não se deve tratar automaticamente cada análise como um alerta.

## Cadastros que podem alimentar filtros

`GET /cameras` retorna `{data, pagination}` com `id`, `name`, `raspberry_id`, `model`, `aviary_id` e `active`; permite filtros `raspberry_id`, `aviary_id`, `active`, `limit` e `offset`. `GET /aviaries` fornece os aviários cadastrados. Com a API local configurada, o frontend percorre todas as páginas e usa esses cadastros para os filtros e rótulos. Sem a API ou se a consulta falhar, os filtros de câmera usam valores demonstrativos.

## Contrato futuro sugerido para alertas

Antes da integração, combinar a regra de geração do alerta, os filtros e a paginação. Uma proposta compatível com o desenho existente da tabela é:

```json
{
  "alerts": [
    {
      "id": 42,
      "camera_id": 3,
      "aviary_id": 1,
      "datetime": "2026-11-12T09:42:00-03:00",
      "alarm_type": "valor registrado pelo backend"
    }
  ]
}
```

Os cinco campos correspondem à tabela atual. O exemplo é uma proposta, não uma rota existente. O backend pode incluir rótulos de câmera e aviário obtidos por consulta às tabelas relacionadas, mas seus formatos precisam ser acordados.

### Imagem associada

A tela possui um componente opcional para imagem com uma região destacada. Nem a tabela de alertas atual nem o contrato encontrado no repositório definem imagem ou caixa delimitadora. Para habilitar esse recurso, o backend precisará informar uma URL acessível ao dashboard, o texto alternativo e a caixa da região em coordenadas normalizadas entre `0` e `1` (`x`, `y`, `width`, `height`). A forma de armazenamento, retenção e autorização dessa imagem permanece em aberto.

## Autenticação e origem

Todas as rotas exceto `GET /health` exigem bearer token. O backend aceita a credencial de serviço `RAIAR_API_TOKEN` ou, quando configurado, JWT de usuário do Supabase Auth cujo `app_metadata.role` seja `gestor` ou `operador`. No desenvolvimento local, o frontend usa o proxy do Vite: `RAIAR_DEV_API_TOKEN` é lido pelo processo Node e enviado no cabeçalho da requisição encaminhada. O cliente do navegador usa somente o caminho relativo `/api`; não recebe o token. Nenhuma credencial deve usar prefixo `VITE_` ou entrar no bundle. O frontend não implementa login. Em produção, o proxy de desenvolvimento não existe; o acesso requer autenticação de usuário e proxy reverso de mesma origem.

O backend não configura CORS. Em desenvolvimento, o proxy local do Vite evita chamadas entre origens diferentes. Em produção, será necessário HTTPS com proxy reverso de mesma origem e autenticação de usuário; CORS irrestrito não deve ser habilitado.

## Comportamento da demonstração

Enquanto a rota não está disponível, a interface lê três registros fictícios por meio do adaptador `src/frontend/src/services/alertsRepository.ts`. Um aviso visível deixa claro que são exemplos, inclusive quando a API fornece câmeras reais. Se a rota de alertas responder 404, a tela informa que os avisos ainda não estão disponíveis neste ambiente e mantém os exemplos. Erros de rede, autenticação ou serviço aparecem com uma mensagem e uma opção para tentar novamente.

## Referências {#referencias}

[1] AGROTECH INTELI. **Banco de dados: primeira versão**. `src/database/schema.sql` e [documentação do esquema](../sprint-3/banco-de-dados.md). Disponível em: repositório do projeto Raiar. Acesso em: 15 nov. 2026.

[2] AGROTECH INTELI. **Backend e integração com o banco de dados**. [Documentação do backend](./backend.md), seções de autenticação, rotas e lacunas conhecidas. Disponível em: repositório do projeto Raiar. Acesso em: 16 nov. 2026.
