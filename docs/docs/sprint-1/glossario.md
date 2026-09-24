---
title: Glossário em linguagem simples
sidebar_position: 3
sidebar_label: Glossário em linguagem simples
description: Explicação dos termos usados na proposta de solução e no dicionário de dados da Sprint 1.
---

# Glossário em linguagem simples

Este glossário explica os termos usados na [proposta de solução](./proposta-de-solucao.md) e no [dicionário de dados](./dicionario-de-dados.md). Quando aparece um nome técnico, a ideia é dizer o que ele significa para este projeto.

## Aviário e criação

**Aviário:** o galpão onde as aves vivem. Neste projeto, usamos “aviário” para falar do edifício e de sua localização. O equipamento Jump Start fica dentro do aviário.

**Jump Start:** nome de um sistema de recria de aves da Vencomatic. O sistema tem linhas de alimentação e água e plataformas reguláveis. Essas plataformas ajudam as aves jovens a aprender a subir e se movimentar entre os níveis e poleiros. Para nós, “Jump Start” significa a estrutura específica onde se pretende acompanhar as aves, não um nome genérico para qualquer galpão. Consulte a [descrição do fabricante](https://www.vencomaticgroup.com/layers/jump-start).

**Recria:** período em que as aves jovens crescem e aprendem a se movimentar na estrutura antes de serem transferidas para o local de produção de ovos. A idade exata a observar no projeto ainda precisa ser combinada com a Raiar.

**Lote:** grupo de aves criado junto e identificado pela Raiar. O sistema registra qual lote aparece na imagem; a proposta não pretende reconhecer cada ave individualmente.

**Nível:** uma plataforma ou parte da estrutura que o parceiro identifica como posição distinta para as aves. Os nomes e limites dos níveis serão confirmados na visita.

**Poleiro:** barra ou apoio onde as aves podem pousar e descansar.

## Imagens e contagens

**Visão computacional:** uso de programas de computador para extrair informações de imagens. Aqui, a tarefa proposta é contar aves que aparecem em cada nível visível.

**Câmera:** aparelho que grava ou captura imagens. O ângulo e o que aparece na imagem determinam quais aves e níveis podem ser avaliados.

**Campo de visão:** a parte do aviário que aparece na imagem de uma câmera. Uma câmera não mostra necessariamente todos os níveis nem todas as aves.

**Quadro:** uma única imagem retirada de uma gravação de vídeo. Medir quadros separados permite acompanhar vários momentos, mas não significa que sejam sempre as mesmas aves.

**Aves visíveis:** somente as aves que podem ser observadas no quadro. As contagens e porcentagens propostas referem-se a elas, não ao total de aves do lote.

**Zona:** área marcada sobre a imagem para indicar um nível. A equipe desenha e identifica essas áreas a partir de uma imagem de referência; uma zona pode não corresponder perfeitamente a um nível se o ângulo ou a estrutura mudar.

**Oclusão:** quando um objeto, outra ave ou uma parte da estrutura esconde uma ave na imagem. O sistema não consegue contar com segurança o que não aparece.

**Anotação:** registro feito por uma pessoa para indicar quantas aves aparecem e a que nível pertencem. Essas contagens manuais servem para conferir as estimativas automáticas.

**Modelo:** neste projeto, um programa treinado com exemplos de imagens para localizar e contar aves. A contagem do programa precisa ser comparada com contagens humanas antes de ser considerada útil.

**Limiar de confiança:** valor mínimo escolhido pelo projeto para aceitar uma identificação feita pelo modelo. Mudar esse valor pode alterar a quantidade de aves identificadas; por isso ele deve ficar registrado em cada resultado.

## Dados e medidas

**Metadados:** informações que explicam uma imagem, por exemplo a câmera, o horário, o aviário e o lote. Sem elas, pode ser difícil entender de onde veio uma contagem.

**Frequência de captura:** quantas vezes o sistema guarda uma imagem e quanto tempo há entre uma imagem e a seguinte. O intervalo de 20 segundos citado no plano é apenas uma sugestão para a primeira amostra.

**Base de dados:** conjunto organizado de imagens, identificações e contagens do projeto. A base para treinar ou conferir o programa ainda será montada; não recebemos as imagens nesta etapa.

**Contagem por nível:** quantidade de aves visíveis atribuídas a cada zona em um quadro.

**Percentual por nível:** a parte das aves que receberam um nível identificável e aparecem em cada nível. Se há 12 aves no nível A e 8 no B, das 20 atribuídas, os percentuais são 60% e 40%. Aves ocultas, sem nível atribuído ou fora da imagem não fazem parte dessa conta.

**Ponto percentual:** diferença direta entre dois percentuais. Se uma medida vai de 40% para 50%, aumenta 10 pontos percentuais. Isso não significa um aumento de 10%.

**Telemetria:** medidas registradas por aparelhos ao longo do tempo, como leituras de sensores. Temperatura ou pressão, se disponíveis, são exemplos. Uma mudança ao mesmo tempo que outra não prova que uma causou a outra.

**Histórico ou série temporal:** registros organizados por horário. Neste projeto, permitem consultar contagens de diferentes momentos, sem somar aves filmadas em quadros distintos como se fossem animais diferentes.

**Agregação:** resumo de várias medidas de um período, por exemplo a média de percentuais de vários quadros durante uma hora. Os quadros e o horário incluídos no resumo devem ser identificáveis.

## Software, identificação e validação

**MVP, ou produto mínimo viável:** a menor versão funcional do projeto que permite verificar se a medição funciona e se tem utilidade para quem vai consultá-la. Não significa que o sistema já esteja pronto para instalação na Raiar.

**Processamento local ou edge:** análise feita perto da câmera, por exemplo num pequeno computador instalado com o equipamento. Pode continuar a funcionar mesmo quando não há comunicação com uma plataforma central.

**Dispositivo:** aparelho que participa da captura, análise ou envio dos dados. A câmera, o computador de processamento e o sensor podem ser equipamentos diferentes.

**Sincronização:** envio posterior dos dados que ficaram guardados no equipamento local quando a conexão à plataforma estava indisponível.

**Retenção:** período pelo qual imagens e outros dados são guardados. O prazo ainda precisa ser combinado com a Raiar.

**ID, ou identificador:** código usado para distinguir um aviário, lote, câmera, quadro ou outro registro. IDs ajudam a relacionar informações sem depender de nomes digitados de formas diferentes.

**Versão:** registro de qual configuração, desenho das zonas ou modelo foi usado numa análise. Guardar versões permite entender como o resultado foi produzido.

**Data e horário com fuso:** registrar também a diferença em relação ao horário universal. Por exemplo, `2026-09-24T14:30:00-03:00` indica 14h30 num local três horas atrás do UTC. Isso evita relacionar uma imagem ao dia ou à leitura errados quando os aparelhos têm horários diferentes.

**UTC:** sigla do horário universal usado como referência comum no armazenamento. Os horários continuam a poder ser mostrados na hora local do aviário.

**Formato ISO 8601:** padrão escrito para datas e horários. A exemplo acima mostra a data, a hora e a diferença do fuso num só texto.

**Fuso horário IANA:** nome padronizado de uma região, como `America/Sao_Paulo`. Ajuda o sistema a aplicar regras locais de horário.

**CSV:** formato simples de planilha em texto, com as informações separadas em colunas. Pode ser aberto em programas de planilha.

**SHA-256:** cálculo que gera uma impressão digital curta do conteúdo de um arquivo. Permite perceber se dois arquivos são iguais ou se um foi alterado. Não revela o conteúdo nem substitui uma cópia de segurança.

**Nulo (`null`):** campo sem valor informado ou sem medida disponível. Diferente de zero: zero significa que a contagem válida foi zero; nulo significa que não há uma contagem válida.

**P0 e P1:** marcadores da prioridade no pedido de dados. P0 significa necessário para iniciar a avaliação. P1 significa complementar, que pode ser obtido depois.

**Métrica:** medida usada para avaliar um resultado. Neste projeto, o erro de contagem compara o número estimado pelo programa com o número contado pelas pessoas.

**MAE, erro absoluto médio:** média do tamanho da diferença entre a contagem automática e a contagem feita por pessoas, expressa em aves. Um MAE de 2 significaria uma diferença média de 2 aves por comparação.

**Erro percentual:** diferença entre as contagens expressa como proporção de uma contagem de referência. Não tem um resultado definido quando a referência contém zero aves.

**Conjunto de teste:** grupo de imagens reservado para conferir o modelo depois que ele foi desenvolvido. Separá-lo das imagens de treino ajuda a verificar seu desempenho em imagens que não foram usadas para ajustá-lo.

**Treino, validação e teste:** três usos diferentes para os exemplos. Treino ensina o programa; validação ajuda a escolher seus ajustes; teste mede o resultado final com exemplos reservados. Imagens quase iguais do mesmo vídeo devem ficar juntas para não facilitar artificialmente o teste.

**Cobertura da coleta:** proporção de imagens esperadas que foram recebidas e puderam ser avaliadas. Uma imagem em falta ou inadequada deve ser marcada como lacuna, não contada como se não houvesse aves.

**Bbox ou caixa delimitadora:** retângulo desenhado ao redor de uma ave na imagem para registrar a posição do animal. As letras `px` significam pixels, os pequenos pontos que compõem a imagem digital.

**RF e RNF:** abreviações de requisito funcional e requisito não funcional. RF descreve uma tarefa que o sistema deve realizar. RNF descreve uma condição de qualidade, por exemplo o tempo de resposta ou o que acontece quando a conexão cai. Os requisitos associados a esta proposta ainda são uma versão inicial.

