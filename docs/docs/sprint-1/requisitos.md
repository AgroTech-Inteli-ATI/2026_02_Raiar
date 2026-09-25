---
title: Requisitos funcionais e não funcionais
sidebar_label: Requisitos
sidebar_position: 4
description: Primeira versão dos requisitos funcionais e não funcionais do sistema de acompanhamento da distribuição das aves no Jump Start.
---

# Requisitos funcionais e não funcionais

Esta entrega apresenta a primeira versão dos requisitos funcionais e não funcionais do sistema de acompanhamento da distribuição das aves entre os níveis da estrutura Jump Start. As tabelas registram o comportamento esperado, os critérios iniciais de aceitação e as metas de qualidade; os parágrafos explicam as decisões que delimitam os requisitos.

## Requisitos funcionais

Esta versão reúne dez requisitos funcionais, agrupando operações relacionadas em cada item. A tabela usa **ID, requisito funcional, ator e critério de aceitação**. As decisões de detalhamento aparecem após a tabela, sem alterar a redação dos requisitos.

| ID | Requisito funcional | Ator | Critério de aceitação |
| --- | --- | --- | --- |
| RF01 | O sistema deve controlar o acesso às funcionalidades conforme os perfis de gestor e operador técnico. | Gestor, operador e sistema | Após a autenticação, cada usuário consegue acessar somente as funcionalidades permitidas para seu perfil. |
| RF02 | O sistema deve permitir o gerenciamento de lotes e dispositivos, incluindo suas associações com os aviários. | Operador e gestor | É possível cadastrar um lote e um dispositivo, associá-los a um aviário e consultar a associação ativa. |
| RF03 | O sistema deve permitir a configuração da coleta de dados para cada câmera. | Operador | O operador consegue definir frequência de amostragem, janelas de coleta e zonas correspondentes aos níveis da estrutura. |
| RF04 | O dispositivo deve coletar e transmitir automaticamente imagens, telemetria e metadados para o sistema. | Dispositivo e sistema | Os dados coletados são enviados sem intervenção manual e ficam armazenados temporariamente quando não há conexão. |
| RF05 | O sistema deve processar automaticamente os quadros recebidos. | Sistema | Após o recebimento, os quadros entram na fila de processamento e geram resultados separados por câmera e período. |
| RF06 | O sistema deve calcular a distribuição das aves visíveis entre os níveis configurados. | Sistema | Para cada período analisado, o sistema apresenta contagem e percentual de aves visíveis por nível. |
| RF07 | O sistema deve armazenar o histórico das métricas visuais, da telemetria e dos metadados do lote. | Sistema | O histórico permite acompanhar a evolução do mesmo lote por data, horário, idade, nível e câmera. |
| RF08 | O sistema deve disponibilizar um dashboard para acompanhamento do lote e do funcionamento da solução. | Gestor e operador | O dashboard apresenta visão geral, evolução por nível, detalhamento do período, telemetria, filtros, qualidade das imagens e estado dos dispositivos. |
| RF09 | O sistema deve permitir a exportação e a revisão dos resultados. | Gestor e operador | O gestor consegue exportar os dados em CSV e consultar imagens representativas; resultados duvidosos podem ser sinalizados para análise técnica. |
| RF10 | O sistema deve aplicar políticas de retenção e gerenciamento do ciclo de vida dos dados. | Gestor e sistema | Dados são mantidos conforme sua categoria; lotes podem ser arquivados e restaurados; exclusões definitivas exigem confirmação e ficam registradas. |

Nos RF01 e RF02, gestor e operador técnico são perfis provisórios enquanto as [personas](./personas/index.mdx) são detalhadas. O cadastro trata o dispositivo completo, formado por Raspberry Pi 4 Model B de 4 GB de RAM, câmera e sensores padronizados, e o associa ao aviário e ao lote. O acompanhamento é feito por lote, sem identificar aves individualmente. O gestor consulta resultados e administra os dados; o operador configura a coleta e acompanha os dispositivos.

Nos RF03 a RF05, a câmera pode captar vídeo continuamente, mas salva quadros de forma periódica nas janelas configuradas pelo operador. Os níveis são delimitados manualmente sobre uma imagem de referência. Mudanças na posição da câmera ou na estrutura exigem uma nova versão das zonas, preservando a configuração associada aos resultados anteriores. No RF05, os quadros recebidos pelo módulo de processamento são analisados de forma assíncrona no dispositivo; a plataforma web concentra a consulta, o histórico e a exportação. Durante falhas de conexão, o dispositivo mantém os registros localmente e os sincroniza depois.

Nos RF06 a RF08, contagem e porcentagem se referem às **aves visíveis** em cada nível, câmera e período. Os resultados de câmeras diferentes não são somados em uma contagem global, pois seus campos de visão podem se sobrepor. O índice de densidade e estatísticas temporais adicionais são desejáveis, sujeitos à viabilidade dos dados. A evolução histórica compara períodos de um mesmo lote. A telemetria aparece junto às métricas visuais do período, sem atribuir automaticamente uma relação causal entre elas. Imagens inadequadas e períodos sem dados devem ser identificados para que não sejam confundidos com medições válidas. O dashboard oferece visão geral, evolução por nível, detalhamento do período e telemetria correspondente. O sistema não classifica o comportamento como adequado ou inadequado nem recomenda ações de manejo.

Nos RF09 e RF10, a exportação em CSV e a consulta de imagens representativas compõem o núcleo do MVP. A sinalização de resultados duvidosos e o reprocessamento são desejáveis; uma nova análise depende da existência dos quadros amostrados e deve preservar o resultado anterior. A retenção terá prazos diferentes para imagens, métricas, telemetria e metadados. O gestor poderá arquivar e restaurar lotes, enquanto a exclusão definitiva exigirá confirmação, justificativa e registro de auditoria.

## Requisitos não funcionais e forma de verificação

Os requisitos não funcionais abaixo registram os critérios de qualidade elaborados e sua relação com os requisitos funcionais. Alguns valores ainda são propostas e dependem de validação.

| ID | Critério de qualidade | RF relacionados |
| --- | --- | --- |
| RNF01 | Durante 24 horas sem conexão com a plataforma web, o dispositivo deve continuar capturando e processando as imagens previstas nas janelas configuradas. | RF04, RF05 |
| RNF02 | Em teste com rede estável e até 3 dispositivos ativos, pelo menos 95% dos carregamentos de páginas comuns devem terminar em até 3 segundos; para gráficos históricos, em até 5 segundos. As condições da rede e o volume de dados devem ser registrados no teste. | RF08, RF09 |
| RNF03 | Com 3 dispositivos operando simultaneamente por 24 horas, todas as imagens amostradas dentro da configuração homologada devem ser processadas, sem crescimento contínuo da fila de processamento. | RF04, RF05, RF06 |
| RNF04 | Após 24 horas de desconexão, todos os registros preservados localmente devem ser sincronizados uma única vez, mantendo data, hora e dispositivo de origem. O prazo preliminar para concluir o envio é de até 2 horas após a reconexão, em rede estável, sujeito à validação. | RF04, RF07 |
| RNF05 | A plataforma web deve estar acessível em pelo menos 95% das verificações realizadas ao longo de cada mês, excluídas as manutenções programadas e registradas. | RF08, RF09 |
| RNF06 | 100% das rotas protegidas devem negar acesso sem autenticação; os testes de permissão devem impedir que cada perfil execute ações fora de sua função. As senhas não podem ser armazenadas em texto puro e todo acesso web deve usar HTTPS. | RF01, RF02, RF10 |
| RNF07 | Os fluxos de consulta devem funcionar nas duas versões mais recentes de Chrome e Edge disponíveis na data do teste. | RF08, RF09 |
| RNF08 | Em uma base de teste anotada manualmente e separada da base de treinamento, medir o erro médio de contagem por imagem e o erro da porcentagem de aves por nível. As metas preliminares, sujeitas à validação, são erro de contagem de até 15% e diferença de até 10 pontos percentuais por nível, considerando apenas imagens classificadas como avaliáveis. | RF05, RF06 |
| RNF09 | Na inspeção da instalação, a case deve manter componentes e conexões fixos e inacessíveis às aves. Em teste de 24 horas no local previsto, o dispositivo deve operar sem falhas causadas pela montagem ou exposição dos componentes. | RF04 |
| RNF10 | Em testes que provoquem falhas de captura, processamento e sincronização, 100% das falhas testadas devem gerar um registro com data, hora, dispositivo e tipo de erro. 100% dos resultados devem identificar as versões do modelo e da configuração de zonas utilizadas. | RF03, RF04, RF05, RF09 |
| RNF11 | Na Raspberry Pi 4 Model B com 4 GB de RAM, com modelo, resolução e frequência de amostragem homologados, o processamento local completo de cada quadro deve terminar antes da próxima captura programada. O tempo de inferência do modelo não deve exceder 80% do intervalo entre quadros em pelo menos 95% das imagens avaliáveis. | RF03, RF05, RF06 |
| RNF12 | Em teste contínuo de 24 horas na Raspberry Pi 4 Model B com 4 GB de RAM, a utilização total de CPU, normalizada para 100% nos quatro núcleos, deve permanecer em até 80% na média de cada janela de 5 minutos. A memória disponível deve permanecer em pelo menos 20% da RAM reconhecida pelo sistema operacional (aproximadamente 0,8 GB da capacidade nominal), sem falhas por falta de memória ou redução de frequência por aquecimento. | RF04, RF05, RF06 |

As metas de 24 horas sem conexão, três dispositivos, carregamento em 3 e 5 segundos e disponibilidade de 95% já orientam o projeto, mas precisam ser verificadas. Outros detalhes numéricos presentes na tabela ainda exigem confirmação: 95% dos carregamentos no RNF02; duração do teste simultâneo no RNF03; prazo de 2 horas no RNF04; apuração mensal no RNF05; cobertura de 100% das rotas no RNF06; duas versões de navegador no RNF07; limites de erro no RNF08; teste de 24 horas da case no RNF09; cobertura de 100% no RNF10; e os limites de inferência, CPU e memória nos RNF11 e RNF12. Os limites de erro do modelo dependem especialmente de uma base anotada e dos primeiros testes. Backup e recuperação da plataforma central não são requisitos definidos nesta versão.

Para verificar os RNF11 e RNF12, o teste deve registrar a memória reconhecida e a versão do sistema operacional, a versão do modelo de visão computacional, a resolução das imagens, o menor intervalo de amostragem autorizado, a câmera, os sensores, a fonte de alimentação e as condições térmicas da case. O tempo de inferência deve ser medido por quadro; CPU e memória, ao longo de toda a execução. O [fabricante informa que o aquecimento pode reduzir a frequência do processador](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html). Os percentuais de 80%, 95% e 20% são metas iniciais deste projeto, sujeitas aos resultados dos testes no dispositivo escolhido.

## Conclusão

Esta versão consolida dez requisitos funcionais e doze não funcionais. Os RFs descrevem o fluxo desde a configuração e a coleta até o processamento, o cálculo da distribuição das aves visíveis, a consulta histórica e o gerenciamento dos dados. Os RNFs estabelecem condições de operação, desempenho na Raspberry Pi 4 de 4 GB, segurança, compatibilidade, qualidade da medição, proteção física e rastreabilidade, vinculadas às funcionalidades que afetam. Juntos, os requisitos oferecem uma base para orientar a implementação e verificar seus resultados.

Os critérios de aceitação e as metas de qualidade ainda dependem de validação com dados e hardware reais. As imagens, os metadados, a posição das câmeras, os níveis observáveis e a frequência viável de coleta fornecidos pelo parceiro permitirão construir uma base anotada, testar a contagem e a distribuição por nível e definir limites quantitativos para o modelo. Também deverão ser avaliadas a operação com três dispositivos, a continuidade local por 24 horas, a sincronização após a reconexão e os tempos e recursos consumidos na Pi 4. As permissões dos perfis, os prazos de retenção e os critérios ainda preliminares serão refinados com esses resultados; a comprovação do atendimento aos requisitos ocorrerá nos testes da solução.
