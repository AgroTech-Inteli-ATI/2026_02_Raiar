---
title: Dicionário de dados e coleta inicial
sidebar_position: 2
description: Dados necessários para validar e desenvolver o monitoramento das aves visíveis nos níveis do Jump Start.
---

# Dicionário de dados e coleta inicial

Este documento lista os dados necessários para a [proposta de solução](./proposta-de-solucao.md): contar as aves que aparecem em cada nível do Jump Start. Para uma explicação do sistema e dos termos técnicos, consulte o [glossário em linguagem simples](./glossario.md). O primeiro pedido à Raiar deve reunir **imagens originais, identificação do lote e da câmera, horários, idade das aves e uma imagem que ajude a identificar os níveis**. Leituras de sensores e informações sobre o manejo podem acrescentar contexto, se estiverem disponíveis.

As tabelas abaixo descrevem as informações previstas para o projeto; ainda não representam um banco de dados construído. Nomes, formatos e quantidades são propostas a confirmar com a equipe e com a Raiar. O envio, os prazos e o tempo de armazenamento das imagens também dependem de acordo.

## Dados iniciais a solicitar

**P0** é necessário para avaliar a medição e montar a base anotada. **P1** apoia contexto ou operação e pode ser obtido após a primeira inspeção. A identificação existente no parceiro pode ser convertida para os IDs internos pela equipe; não é necessário que a Raiar já possua este esquema.

| ID | Prioridade e dado | Origem e responsável pelo fornecimento | Forma inicial e frequência | Uso e critério de recebimento |
| --- | --- | --- | --- | --- |
| D01 | P0: imagens ou vídeos originais da recria | Raiar, contato a indicar | Arquivos e manifesto por remessa; amostragem proposta abaixo | Arquivos legíveis, sem edição destrutiva, vinculados a câmera, lote, data e horário |
| D02 | P0: identificação e idade do lote | Registros da Raiar | Planilha ou CSV por lote e correção | Idade em dias em uma data de referência; não inferir idade apenas da data de alojamento |
| D03 | P0: aviário, estrutura e níveis | Raiar e validação conjunta na visita | Croqui ou imagem de referência por instalação e alteração | Nomes e limites dos níveis reconhecidos pela equipe técnica; indicar partes ocultas |
| D04 | P0: câmera e condições de captura | Raiar e inspeção técnica AgroTech | Modelo, resolução, formato, conexão e acesso às gravações; por instalação | Confirmar campo de visão, câmera fixa ou móvel, relógio, fuso e possibilidade de exportação |
| D05 | P0: permissão e condições de uso | Raiar e responsáveis do projeto | Registro de acordo antes da transferência | Definir destinatários, armazenamento, retenção, restrições e tratamento de pessoas nas imagens |
| D06 | P1: horários de iluminação e mudanças de manejo | Equipe técnica da Raiar | Tabela de eventos com data e horário, por ocorrência | Distinguir evento registrado de interpretação; não presumir causalidade |
| D07 | P1: telemetria disponível | Raiar ou módulo do projeto, se existente | CSV com variável, unidade, horário e sensor; frequência a confirmar | Origem e posição conhecidas, relógio verificável e leituras ausentes identificadas |
| D08 | P0 para avaliar o modelo: contagens e rótulos | Equipe AgroTech; revisão zootécnica da Raiar | Anotações versionadas por quadro e nível | Protocolo comum, revisão de amostra e separação entre treino, validação e teste |

Os itens D01 a D05 são o pacote de entrada. D08 será produzido pela equipe após o recebimento, sem pressupor que a Raiar já tenha imagens anotadas. A falta de D07 não impede a primeira avaliação visual, mas impede validar a integração ambiental.

## Plano inicial de amostragem e envio

### Inspeção antes da coleta maior

O primeiro pacote proposto contém **30 quadros de uma câmera candidata**, distribuídos entre horários e condições de iluminação disponíveis, junto a D02 a D05. Esse número é uma proposta de triagem de esforço reduzido, sem garantia estatística. A análise por dois integrantes deverá verificar se as aves e os níveis são reconhecíveis, registrar ambiguidades e indicar se o enquadramento permite continuar. Esses quadros podem integrar a remessa posterior, sem contagem duplicada.

### Pacote piloto para exploração e anotação

Após a triagem, o pacote piloto proposto contém **270 quadros de rotina por câmera**, obtidos em três dias distintos, três janelas horárias por dia e 30 quadros por janela. Uma forma inicial de obter cada grupo é amostrar a cada 20 segundos em um trecho de dez minutos, nos instantes de 0 a 580 segundos. Os dias devem pertencer à janela de idade acordada. Os horários devem ser escolhidos com o parceiro, incluindo diferenças reais de iluminação e ocupação.

Complementar com **30 quadros de casos difíceis**, quando existirem, para totalizar 300: desfoque, oclusão, reflexos, pouca luz, nível aparentemente vazio e aves na fronteira entre zonas. Identificar a seleção dirigida para não usá-la como estimativa da frequência real desses eventos. Se algum cenário não existir ou não estiver acessível, registrar a lacuna em vez de produzir uma imagem artificial como evidência real.

Esse volume é um **mínimo operacional proposto para o piloto**, não uma amostra comprovadamente suficiente para treinar ou validar o modelo. A frequência de 20 segundos serve para organizar o pedido inicial; a frequência de produção depende dos testes de hardware. Três dias de um lote não demonstram uma curva de toda a recria nem generalização para outros lotes. Para estudar evolução por idade, solicitar novas remessas em idades distintas acordadas com a Raiar.

| Cobertura a conferir no manifesto | Regra de organização |
| --- | --- |
| Câmera, posição e níveis | Separar instalações e versões de zonas; registrar o que fica fora do campo de visão |
| Lote e idade | Manter origem explícita; não misturar lotes ou idades desconhecidas em uma curva |
| Dia, janela horária e iluminação | Registrar os estratos presentes e ausentes, sem inventar equivalência entre horários |
| Ocupação e oclusão | Incluir cenas vazias avaliáveis e cenas difíceis, diferenciadas por qualidade |
| Sessão de captura | Preservar a sessão de origem para evitar que quadros vizinhos apareçam no treino e no teste |

### Cronograma a pactuar

| Marco proposto | Responsabilidade | Prazo relativo proposto | Estado |
| --- | --- | --- | --- |
| Confirmar recorte, câmera, acesso e permissão | Grupo e Raiar | Na visita ou reunião de alinhamento | A agendar |
| Enviar pacote de triagem com metadados | Raiar, contato a indicar | Até dois dias úteis após o acordo de acesso | Não acordado |
| Inspecionar triagem e devolver lacunas | Equipe técnica do projeto | Até dois dias úteis após recebimento | Proposto |
| Enviar pacote piloto | Raiar, com seleção apoiada pela equipe | Antes da exploração de dados da Sprint 2; data a pactuar | Não acordado |
| Fechar protocolo, revisar anotações e lacunas | Equipe AgroTech e referência técnica da Raiar | Na Sprint 2, antes do treinamento | Proposto |

Após o acordo com a Raiar, os prazos relativos deverão ser substituídos por datas, com registro de responsável, quantidade recebida, quantidade utilizável e pendências por remessa. Nenhum envio foi confirmado até esta versão.

## Convenções do dicionário

- **Obrigatório (S):** necessário para um registro aceito. **Opcional (N):** pode ser `null`. **Condicional (C):** obrigatório na condição indicada. Campo ausente não deve virar zero.
- **ID:** texto estável e único, como `camera_01`; deve manter seu significado entre remessas. Referências precisam apontar para cadastros existentes.
- **Data:** `YYYY-MM-DD`. **Instante:** ISO 8601 com fuso, normalizado para UTC no armazenamento. Preservar o fuso do aviário para exibição, idade e agrupamento por dia local.
- **Coordenadas:** pixels da imagem original, origem no canto superior esquerdo, `x` crescente para a direita e `y` para baixo. Redimensionamento exige transformação documentada.
- **Número:** decimal com ponto no intercâmbio; unidades explícitas. Exemplos são fictícios e não representam medições da Raiar.
- Dados recebidos incompletos podem ficar em triagem com a causa da pendência; só entram na avaliação quando os campos obrigatórios estiverem resolvidos. Nunca inventar horário, lote ou idade para completar um registro.

## Cadastros e configuração

### Aviário e lote

**Granularidade:** um registro por aviário e um por lote. **Origem:** Raiar; normalização pela AgroTech. **Atualização:** cadastro inicial e correções rastreáveis. Não sobrescrever a origem de medições antigas se um lote mudar de aviário.

| Entidade.campo | Tipo e unidade | Obrig. | Significado e regra | Exemplo fictício |
| --- | --- | --- | --- | --- |
| `aviario.aviario_id` | Texto | S | Identificador do local | `aviario_01` |
| `aviario.nome` | Texto | S | Nome operacional ou código autorizado | `Recria A` |
| `aviario.fuso_horario` | Texto | S | Fuso IANA confirmado para o local | `America/Sao_Paulo` |
| `lote.lote_id` | Texto | S | Identificador estável do lote, sem identificar aves | `lote_01` |
| `lote.data_referencia_idade` | Data | S | Data local em que a idade foi informada | `2026-09-01` |
| `lote.idade_dias_referencia` | Inteiro, dias | S | Idade nessa data, não negativa; convenção do parceiro documentada | `1` |
| `lote.fonte_idade` | Texto | S | Registro ou informação de origem da idade | `registro de alojamento revisado` |
| `lote.quantidade_alojada` | Inteiro, aves | N | Contexto do lote, positivo quando conhecido; não é denominador da distribuição visual | `1000` |
| `lote.linhagem` | Texto | N | Contexto a usar apenas se fornecido | `null` |

### Instalação, coleta e zonas

**Granularidade:** uma instalação por associação vigente entre dispositivo, câmera, aviário e lote; uma configuração por versão; uma zona por nível visível nessa configuração. **Origem:** cadastro técnico, validado com a Raiar. **Atualização:** na instalação ou mudança, preservando versões anteriores.

| Campo | Tipo e unidade | Obrig. | Significado e regra |
| --- | --- | --- | --- |
| `instalacao_id` | Texto | S | Identifica uma associação histórica; mudança de lote ou posição gera novo registro |
| `dispositivo_id` | Texto | S | Identificador do conjunto que captura/processa; não confundir com ID da câmera |
| `camera_id` | Texto | S | Identificador da câmera de origem |
| `aviario_id`, `lote_id` | Texto, cada | S | Referências aos cadastros correspondentes |
| `vigente_desde`, `vigente_ate` | Instante, cada | S / N | Intervalo de validade `[início, fim)`; fim nulo significa associação ativa; não sobrepor associações da mesma câmera |
| `configuracao_versao` | Texto | S | Versão imutável da coleta; escopo único por instalação |
| `coleta_vigente_desde`, `coleta_vigente_ate` | Instante, cada | S / N | Vigência da versão de coleta, independente da instalação, sem sobreposição; fim nulo indica versão ativa |
| `intervalo_captura_s` | Decimal, segundos | S | Maior que zero; frequência efetiva a homologar no hardware |
| `janelas_coleta` | Lista de intervalos locais | S | Horários planejados e dias abrangidos, com fuso; janela que cruza meia-noite deve ser explícita |
| `zonas_versao` | Texto | S | Versão imutável do conjunto de zonas dessa instalação |
| `quadro_referencia_id` | Texto | S | Referência à imagem original usada para desenhar os níveis |
| `nivel_id`, `nivel_nome` | Texto, cada | S | Identificador e nome físico acordados com a Raiar; não presumir quantidade de níveis |
| `poligono_px` | Lista de pares `(x,y)`, pixels | S | Pelo menos três vértices distintos, dentro da imagem; interior sem autointerseção; zonas sem sobreposição |
| `regra_atribuicao_versao` | Texto | S | Versão da regra que associa uma ave à zona; deve ser comum à anotação e à avaliação |

A chave de uma zona é `(instalacao_id, zonas_versao, nivel_id)`. Mudanças de posição, resolução ou recorte exigem conferir os polígonos e criar nova versão antes de processar. A associação de câmera ao lote deve valer no momento da captura, não apenas no momento do envio. Alterações de frequência ou janelas encerram a vigência da configuração anterior e abrem uma nova versão; a previsão de quadros deve considerar os trechos de vigência de cada versão dentro do período consultado.

## Imagens e anotações

### Quadro e manifesto de recebimento

**Granularidade:** uma imagem capturada ou extraída de vídeo. **Origem:** Raiar ou dispositivo de captura. **Frequência:** por quadro amostrado; exportação por remessa. O manifesto é a tabela que relaciona cada arquivo aos seus metadados.

| Campo | Tipo e unidade | Obrig. | Significado e validação |
| --- | --- | --- | --- |
| `quadro_id` | Texto | S | Identificador único estável, preservado no reenvio |
| `remessa_id`, `sessao_id` | Texto, cada | S | Remessa de entrega e sessão de captura; uma sessão reúne um trecho contínuo na mesma instalação |
| `instalacao_id` | Texto | S | Referência à instalação vigente na captura |
| `capturado_em`, `recebido_em` | Instante, cada | S | Captura e ingestão distintas; atraso de envio não altera o horário observado |
| `configuracao_versao`, `zonas_versao` | Texto, cada | S | Referências às configurações usadas; preenchidas pela equipe na triagem de arquivos históricos |
| `arquivo_ref` | Texto | S | Referência ao armazenamento restrito; não usar URL pública ou segredo de acesso |
| `sha256` | Texto hexadecimal, 64 caracteres | S | Calculado pela ingestão para verificar integridade e detectar arquivos repetidos |
| `largura_px`, `altura_px` | Inteiro, pixels, cada | S | Dimensões positivas lidas do arquivo original |
| `video_origem_ref`, `offset_ms` | Texto / inteiro, milissegundos | C | Obrigatórios quando extraído de vídeo; posição não negativa; preservar a origem |
| `tipo_amostra` | Enumeração | S | `rotina`, `caso_dificil` ou `triagem`; permite separar seleção dirigida |
| `qualidade` | Enumeração | S | `pendente`, `avaliavel` ou `nao_avaliavel`, conforme protocolo |
| `motivo_qualidade` | Texto | C | Obrigatório em `nao_avaliavel`; ex.: níveis não distinguíveis, desfoque ou oclusão impeditiva |

JPEG e PNG são formatos propostos para quadros; vídeos devem preservar o arquivo e formato originais, cuja leitura será testada na triagem. Os horários eventualmente gravados sobre a imagem deverão ser comparados com o relógio informado. Horário desconhecido impede inclusão na série temporal, embora o arquivo possa ser útil para explorar qualidade visual.

### Anotação de referência

**Granularidade:** uma versão de anotação por quadro, com objetos marcados e totais revisados por nível. **Origem:** anotadores da AgroTech, com orientação da Raiar para os níveis. **Frequência:** por quadro selecionado e revisão. Esta é a referência manual usada para medir os erros do modelo.

| Campo | Tipo e unidade | Obrig. | Significado e validação |
| --- | --- | --- | --- |
| `anotacao_id`, `quadro_id` | Texto, cada | S | Identifica a anotação e seu quadro de origem |
| `protocolo_versao`, `zonas_versao` | Texto, cada | S | Regras e zonas utilizadas, preservadas na revisão |
| `anotador_id`, `anotado_em` | Texto / instante | S | Código interno do anotador e momento da anotação |
| `status_revisao` | Enumeração | S | `rascunho`, `revisada` ou `divergente`; teste final usa referências revisadas |
| `objetos` | Lista de objetos | S | Uma entrada por ave distinguível; lista vazia permitida somente em quadro avaliável sem aves |
| `objetos[].bbox_px` | Quatro decimais, pixels | S | `[x_min,y_min,x_max,y_max]`, limites dentro da imagem e área positiva |
| `objetos[].nivel_id` | Texto ou nulo | N | Nível atribuído; nulo quando indeterminado, sem forçar uma classe |
| `objetos[].motivo_indeterminado` | Texto | C | Obrigatório quando o nível for nulo |
| `contagens_por_nivel` | Mapa de nível para inteiro, aves | S | Total de objetos atribuídos a cada nível; incluir zeros dos níveis avaliáveis |
| `particao` | Enumeração | S | `treino`, `validacao` ou `teste`, definida por grupos de origem |

Como regra inicial a validar, usar o ponto central da borda inferior da caixa da ave para atribuir uma zona. Ponto exatamente na fronteira, fora das zonas ou sem correspondência inequívoca com o nível físico resulta em nível indeterminado. A caixa não substitui a avaliação da cena: se a perspectiva inviabilizar a regra, rever enquadramento, zonas e protocolo antes de rotular o restante.

A revisão inicial dos 30 quadros de triagem deverá envolver dois anotadores independentes. As divergências por nível deverão ser registradas e o protocolo ajustado antes da ampliação da base. Uma imagem é avaliável somente se todos os níveis incluídos na distribuição puderem ser anotados segundo o protocolo; a ocultação parcial exige regra explícita, sem inferir aves invisíveis.

A divisão dos dados deverá considerar sessões completas e agrupar trechos próximos do mesmo dia e câmera. Quadros vizinhos não devem ser distribuídos entre treino e teste. A divisão deverá ser fixada antes do ajuste do modelo, com grupos completos reservados para validação e teste. Na ausência de grupos suficientes ou de cobertura dos níveis em cada conjunto, serão necessários mais dados; até lá, a análise ficará limitada à exploração. Um teste de um único lote não comprova generalização para outros lotes.

## Resultados produzidos pelo sistema

### Contagem por quadro e nível

**Granularidade:** um resultado por quadro, execução de análise e nível configurado. **Origem:** modelo e cálculo da aplicação. **Frequência:** após processar cada quadro. Um reprocessamento cria nova análise e preserva a anterior.

| Campo | Tipo e unidade | Obrig. | Significado e validação |
| --- | --- | --- | --- |
| `analise_id`, `quadro_id` | Texto, cada | S | Identificador da execução e referência à imagem |
| `nivel_id` | Texto | S | Nível pertencente à versão de zonas da análise |
| `modelo_versao`, `zonas_versao`, `regra_atribuicao_versao` | Texto, cada | S | Versões imutáveis usadas na execução |
| `limiar_confianca` | Decimal, de 0 a 1 | S | Corte de detecção utilizado; não equivale à acurácia medida |
| `processado_em` | Instante | S | Horário de término do processamento |
| `status` | Enumeração | S | `valido`, `imagem_inadequada` ou `falha_processamento` |
| `quantidade_aves_visiveis` | Inteiro, aves, ou nulo | C | Não negativo em resultado válido; nulo em resultado inválido |
| `total_atribuido_quadro` | Inteiro, aves, ou nulo | C | Soma dos níveis da mesma análise; não inclui detecções indeterminadas |
| `quantidade_sem_nivel` | Inteiro, aves, ou nulo | C | Detecções sem atribuição; total do quadro, repetido nas linhas por nível e nunca somado entre elas |
| `percentual_nivel` | Decimal, %, ou nulo | C | De 0 a 100; calculado apenas com resultado válido e denominador positivo |
| `motivo_status` | Texto | C | Obrigatório se o resultado não for válido |

A chave única é `(analise_id, nivel_id)`. A análise referencia um único quadro e uma única configuração. Reenvio da mesma chave deve ser idempotente, isto é, não criar outra linha. Uma nova versão do modelo gera outro `analise_id`. Comparações temporais devem explicitar versões distintas.

### Fórmulas e agregação

Para um quadro avaliável, seja `n_k` a contagem no nível `k` e `N = soma(n_k)` nos níveis configurados:

```text
percentual_nivel_k = 100 × n_k / N, se N > 0
idade_dias = idade_dias_referencia
             + dias entre data_referencia_idade e data local da captura
```

Se `N = 0`, os percentuais são `null`, mesmo quando a contagem válida é zero. Imagem inadequada ou falha produz contagens e percentuais nulos. Quantidade sem nível permanece visível como limite da distribuição. O número de aves alojadas e detecções de outras câmeras não entram no denominador.

**Exemplo fictício:** 12 aves no nível A, 8 no B e 3 sem nível atribuído resultam em 60% no A e 40% no B, com 20 aves atribuídas e 3 indeterminadas. São percentuais condicionados à atribuição; não se pode afirmar que 60% do lote ocupa o nível A.

Para o histórico, a proposta inicial é calcular a **média dos percentuais por quadro** em intervalos de uma hora local, separando câmera, instalação, lote, configuração de coleta, zonas, regra, modelo e limiar de confiança. Para cada combinação, selecionar uma única análise por quadro: a execução concluída mais recente por `processado_em`, com desempate pelo `analise_id` em ordem lexical. Uma falha nessa execução deve aparecer como lacuna, sem reutilizar silenciosamente um resultado antigo. Preservar os IDs das análises selecionadas e o instante de geração do agregado para reproduzir a consulta.

Usar o mesmo conjunto de quadros válidos com `N > 0` para todos os níveis. Preservar início e fim do intervalo em UTC, quantidade de quadros previstos, recebidos, avaliáveis, com denominador positivo e horário da última captura. Contar cada `quadro_id` uma única vez nesses totais, independentemente do número de análises. A soma de detecções de vários quadros não representa aves únicas. Mudança de configuração dentro da hora produz segmentos separados, com a previsão calculada apenas para o trecho de vigência correspondente.

Quadros válidos vazios participam da cobertura da coleta, mas não da média percentual. Quadro faltante ou inválido não é preenchido com zero. Exibir a cobertura como `100 × quadros avaliáveis / quadros previstos`, com `null` quando nenhum quadro estiver previsto. Esse cálculo exige a configuração de coleta vigente e as janelas pactuadas. Agregações são derivadas; os registros por quadro continuam sendo a referência.

### Métricas para validar a medição

No conjunto de teste, comparar contagens previstas `pred` e referências manuais `ref` por quadro e nível, incluindo contagens manuais zero:

```text
MAE_contagem = soma(abs(pred - ref)) / quantidade de pares quadro-nível
erro_percentual_agregado = 100 × soma(abs(pred - ref)) / soma(ref)
erro_distribuicao_k_pp = média(abs(percentual_previsto_k - percentual_manual_k))
```

MAE é expresso em aves; o erro agregado, em porcentagem; a diferença de distribuição, em pontos percentuais. Se `soma(ref) = 0`, o erro percentual é indefinido: reportar MAE e falsos positivos. O erro de distribuição usa apenas quadros em que os totais previsto e manual sejam positivos; reportar também quantos quadros foram excluídos por total zero. Em particular, uma previsão vazia para um quadro manualmente positivo continua penalizada no erro de contagem.

O relatório de avaliação deverá apresentar cobertura, rejeições e falhas de processamento junto aos erros, para evitar a análise exclusiva dos melhores quadros. As metas preliminares do RNF08 devem ser pactuadas com essa definição antes do teste final, mantendo a fórmula definida previamente.

## Dados complementares e operação

### Telemetria e eventos de contexto

**Granularidade:** uma leitura por sensor, variável e instante; um evento por ocorrência informada. **Origem:** módulo de sensores ou registros do parceiro. **Frequência:** configurável por sensor; eventos por ocorrência.

| Entidade.campo | Tipo e unidade | Obrig. | Significado e regra |
| --- | --- | --- | --- |
| `leitura.leitura_id`, `leitura.sensor_id` | Texto, cada | S | Identificadores estáveis da leitura e sensor |
| `leitura.instalacao_id` | Texto | S | Vínculo espacial conhecido; não atribuir a todos os níveis sem evidência |
| `leitura.medido_em`, `leitura.recebido_em` | Instante, cada | S | Medição e ingestão separadas |
| `leitura.variavel`, `leitura.unidade` | Texto, cada | S | Vocabulário documentado, ex.: `temperatura` e `degC`; `pressao` e `hPa`, se disponíveis |
| `leitura.valor` | Decimal ou nulo | C | Valor na unidade declarada; nulo quando a leitura for inválida |
| `leitura.status` | Enumeração | S | `valida`, `ausente`, `fora_faixa` ou `erro_sensor`; limites conforme instrumento confirmado |
| `leitura.calibracao_ref` | Texto | N | Referência da verificação ou calibração disponível |
| `evento.evento_id`, `evento.instalacao_id` | Texto, cada | S | Identificador do evento e contexto espacial |
| `evento.ocorrido_em`, `evento.tipo` | Instante / texto | S | Momento e categoria, ex.: mudança de iluminação ou posição de câmera |
| `evento.descricao`, `evento.fonte_ref` | Texto, cada | S | Relato factual e origem do registro; sem inferir efeito comportamental |

Não há lista de sensores confirmada para o recorte da recria. O TAP original cita variáveis ambientais, mas sua presença nos arquivos ou no novo protótipo precisa ser verificada. A ausência de leitura não equivale a zero. A associação temporal entre imagem e telemetria deverá registrar a diferença entre os horários e usar uma tolerância definida após a verificação dos intervalos reais. Sem correspondência aceitável, a associação ficará vazia.

### Falhas, acesso e retenção

Registrar falhas com `evento_id` (texto único), `dispositivo_id` (texto), `ocorrido_em` (instante), `etapa` (`captura`, `processamento` ou `sincronizacao`) e `codigo_erro` (texto). Todos são obrigatórios. `quadro_id` é opcional quando a falha impedir a criação da imagem. A fila deve preservar os IDs originais e registrar confirmação de recebimento para testar reenvio sem duplicação.

O dicionário de domínio não inclui credenciais ou tokens. A política inicial prevê acesso às imagens apenas pela equipe autorizada; métricas, revisões e exportações seguem os perfis a validar nos requisitos. Imagens reais não deverão ser publicadas em Git, exemplos da documentação ou links públicos.

| Categoria | Uso | Retenção e condição pendente |
| --- | --- | --- |
| Imagens e vídeos | Anotação, revisão e eventual reprocessamento | Prazo e capacidade a acordar antes da coleta; retenção menor pode impedir reprocessamento |
| Rótulos e divisões do dataset | Reproduzir avaliação | Manter versão e vínculo aos dados permitidos; pactuar o período |
| Métricas e metadados | Histórico e rastreabilidade | Prazo próprio a definir; preservar significado mesmo após expirar a imagem |
| Telemetria e eventos | Contexto e investigação de falhas | Prazo conforme frequência, utilidade e capacidade |
| Registro de exclusão | Auditoria do ciclo de vida | Identificar responsável, horário, motivo e categorias afetadas, sem manter cópia oculta do conteúdo excluído |

Arquivar um lote não significa excluir seus dados. Exclusões definitivas e a conservação de referências devem seguir a política pactuada com o parceiro. Na expiração de uma imagem, o painel deve informar que o arquivo não está mais disponível, preservando apenas os metadados autorizados. Remessas com pessoas identificáveis exigem tratamento e acesso acordados antes do uso.

## Perguntas para a visita

1. Qual lote, faixa de idade e parte do Jump Start devem ser acompanhados primeiro? Quais são os nomes físicos dos níveis?
2. Quais níveis podem ser distinguidos nas câmeras existentes? Há obstáculos, movimento de câmera ou áreas fora da imagem?
3. Qual é o modelo da câmera, resolução original, ângulo, formato, conexão e forma de exportação? Há câmeras de 180° ou 360° e conexão USB-A, conforme os itens ainda abertos da seção 17 do TAP?
4. O horário das gravações está correto? Qual fuso usa? Há interrupções ou mudanças de iluminação programadas?
5. Como a idade do lote é registrada? Existem períodos em que mais de um lote aparece no campo de visão?
6. Que registros e indicadores já são usados para avaliar a ocupação? Qual decisão um histórico por nível ajudaria a tomar?
7. Quem poderá fornecer as imagens, revisar as zonas e esclarecer ambiguidades? Quais datas de envio são viáveis?
8. Há sensores e histórico ambiental? Quais variáveis, unidades, posições e frequências estão disponíveis?
9. Onde os arquivos podem ser armazenados, quem pode acessá-los e por quanto tempo? Há pessoas ou informações restritas nas gravações?
10. Qual erro de contagem ainda permite usar a informação? A equipe aceita validar primeiro a medição sem classificar comportamento ou recomendar manejo?

## Critérios de aceite desta definição

A documentação da Sprint 1 estará pronta para orientar a coleta quando cada dado P0 tiver finalidade, origem e regra de validação; a proposta e os requisitos usarem a mesma unidade de medição; e as pendências de acesso, qualidade, idade e cronograma estiverem identificadas. O **aceite do pacote real** exigirá executar o seguinte roteiro, ainda pendente de recebimento:

| Verificação | Sinal observável | Decisão em caso de falha |
| --- | --- | --- |
| Abrir arquivos e comparar manifesto | Arquivos legíveis, dimensões e hashes conferidos, IDs únicos | Quarentenar arquivos e solicitar correção da remessa |
| Conferir origem e tempo | Cada quadro ligado à instalação vigente, lote, horário e idade | Manter fora da série temporal até esclarecer |
| Revisar níveis e qualidade | Dois anotadores conseguem aplicar a mesma regra aos quadros de triagem | Revisar enquadramento e protocolo antes de anotar em escala |
| Inspecionar cobertura e divisão | Dias, horários e casos documentados; grupos de origem separados | Solicitar complementação ou limitar o alcance do experimento |
| Conferir cálculos com exemplo conhecido | Caso 12/8 gera 60%/40%; vazio e inválido mantêm semânticas distintas | Corrigir cálculo antes da avaliação do modelo |
| Conferir autorização e armazenamento | Destino restrito, responsáveis e política de retenção registrados | Resolver condições antes de transferir ou utilizar arquivos reais |

O registro de cada remessa deverá incluir quantidades recebidas, aceitas e rejeitadas, motivos, responsáveis e próximo pedido. Esse roteiro verifica a preparação dos dados; não comprova desempenho do modelo, do hardware ou utilidade operacional. As fontes de contexto e a relação com os RF/RNF estão na [proposta de solução](./proposta-de-solucao.md#fontes-e-estado-de-validação).
