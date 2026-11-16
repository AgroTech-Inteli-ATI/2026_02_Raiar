---
title: Alertas e dados esperados
sidebar_label: Alertas e dados
sidebar_position: 1
description: Campos de alerta disponíveis e contrato proposto para alimentar o painel.
---

# Alertas e dados esperados

## Campos disponíveis

A tabela `public.alerts` define os campos `id`, `camera_id`, `aviary_id`, `datetime` e `alarm_type`. As relações permitem identificar a câmera e o aviário. A tela usa esses dados e não atribui severidade, estado de tratamento ou confirmação ao alerta, porque esses conceitos não estão no esquema atual [1].

Na branch verificada para esta entrega, não foi encontrada uma rota de leitura de alertas no backend. A tabela existe, mas a [documentação da integração com o banco](../sprint-3/integracao-no-banco.md) registra que a ingestão atual salva análises e ainda não gera linhas de alerta [2].

## Contrato de leitura proposto

Para substituir os dados de demonstração, o frontend precisa de uma rota autenticada de leitura. A proposta inicial é `GET /alerts`, com filtros opcionais `camera_id`, `date_from` e `date_to`, além de paginação (`limit` e `offset`) se o histórico puder crescer. Os nomes e a paginação devem ser confirmados com quem mantém o backend antes da integração.

Resposta mínima sugerida:

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

Os cinco campos correspondem à tabela atual. O backend pode incluir rótulos de câmera e aviário obtidos por consulta às tabelas relacionadas, mas seus formatos precisam ser acordados.

### Imagem associada

A tela possui um componente opcional para imagem com uma região destacada. Nem a tabela de alertas atual nem o contrato encontrado no repositório definem imagem ou caixa delimitadora. Para habilitar esse recurso, o backend precisará informar uma URL acessível ao dashboard e, quando aplicável, uma caixa em coordenadas normalizadas entre `0` e `1` (`x`, `y`, `width`, `height`). A forma de armazenamento, retenção e autorização dessa imagem permanece em aberto.

O navegador deve usar a autenticação de usuário prevista pelo backend. A chave de serviço do banco ou do Supabase nunca deve ser incluída no bundle do dashboard.

## Comportamento da demonstração

Enquanto a rota não está disponível, a interface lê três registros fictícios por meio do adaptador `docs/src/services/alertsRepository.ts`. Um aviso visível deixa claro que são exemplos. O adaptador mantém a fronteira entre a tela e os dados para facilitar a troca pela API sem misturar o mock com os componentes.

## Referências {#referencias}

[1] AGROTECH INTELI. **Banco de dados: primeira versão**. `src/database/schema.sql` e [documentação do esquema](../sprint-3/banco-de-dados.md). Disponível em: repositório do projeto Raiar. Acesso em: 15 nov. 2026.

[2] AGROTECH INTELI. **Integração do nó de borda com o banco de dados**. [Documentação da integração](../sprint-3/integracao-no-banco.md). Disponível em: repositório do projeto Raiar. Acesso em: 15 nov. 2026.
