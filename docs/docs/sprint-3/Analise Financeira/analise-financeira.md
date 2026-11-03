---
title: Análise financeira
sidebar_position: 1
description: Premissas, investimentos, custos operacionais e critérios de retorno dos cenários de PoC e implementação da Raiar.
---

# Análise financeira

A análise financeira estima os recursos necessários para validar a solução da Raiar e, posteriormente, colocá-la em operação. Foram construídos dois cenários: uma **prova de conceito (PoC) com Raspberry Pi** e uma **implementação em campo com equipamentos industriais e câmeras IP**. Em ambos, o objetivo é entender o investimento inicial, o custo de manter a aplicação e o benefício financeiro necessário para recuperar esse investimento.

**Planilha de referência:** [Raiar — Análise financeira: PoC e implementação](https://docs.google.com/spreadsheets/d/19NS9ZBeKlsNQt2Qj5Ss9R78Q0CK5ok3N-m-VpRwFQYQ/edit).

## Como usar a planilha

A planilha reúne os cenários, as premissas e as fontes utilizadas na análise.

| Aba | O que encontrar | Como usar |
| --- | --- | --- |
| **Resumo** | PoC e implementação lado a lado; investimento, CAPEX, OPEX fixo/variável, benefício, ROI e payback | Comece aqui. As colunas D e E explicam cada indicador e sua origem. |
| **Premissas** | Referências, campos do usuário e valores efetivamente usados | Preencha as colunas C para PoC e F para implementação. As células amarelas são os campos de entrada. |
| **Custos e fontes** | Preços dos ovos, cálculo do retorno, materiais, serviços, quantidades e fontes | Consulte as linhas 5–11 para preços dos ovos, 20–48 para retorno, 60–109 para custos da PoC, 114–172 para implementação e 178–281 para parâmetros técnicos. |

Em **Premissas**, B/E preservam as referências; C/F recebem os valores próprios; D/G mostram o que o cálculo usa. **Campo vazio mantém a referência; zero informado substitui a referência por zero.** As referências podem ser preços pesquisados, hipóteses de orçamento ou hipóteses ilustrativas de benefício, conforme a explicação de cada linha.

No **Resumo**, parênteses indicam valores negativos, o traço representa zero e `n.a.` indica um resultado indisponível ou um payback sem prazo finito.

## Objetivo e construção da análise

O escopo parte da [proposta de solução](../../sprint-1/proposta-de-solucao.md): acompanhar a distribuição das aves visíveis entre os níveis do Jump Start, mantendo um histórico para interpretação pela equipe técnica. A análise financeira não pressupõe que uma câmera observe todo o aviário, nem que a aplicação já tenha demonstrado redução de perdas.

O trabalho foi organizado da seguinte forma:

1. Definir o escopo físico e o prazo de cada cenário.
2. Levantar preços de referência para os equipamentos já discutidos e separar preços anunciados de estimativas de planejamento.
3. Dimensionar quantidades, horas de trabalho, consumo elétrico e serviços de nuvem.
4. Separar CAPEX físico, gastos iniciais adicionais, contingência e OPEX mensal.
5. Relacionar o retorno a ovos orgânicos que deixam de ser perdidos, distinguindo preços pesquisados de hipóteses de ganho ainda não medido.
6. Calcular o retorno considerando o prazo, as licenças e o início dos benefícios.

Foram utilizadas referências de fornecedores como RoboCore, Portwell, Intelbras e seus revendedores, além das tabelas da DigitalOcean. As fontes de cada item permanecem na planilha. Cabos, fixação, adequações, horas de trabalho e outros valores sem proposta comercial foram identificados como estimativas. Os preços não representam pedidos de compra ou orçamento aprovado; alguns anúncios estavam sem estoque ou sujeitos a consulta.

## Premissas dos cenários

| Premissa | PoC | Implementação |
| --- | --- | --- |
| Finalidade | Validar captura, processamento e utilidade dos resultados | Planejar a operação contínua em campo |
| Escopo inicial | 1 aviário, 1 câmera e 1 Raspberry Pi | 1 aviário, 4 câmeras e 1 PC industrial |
| Prazo de análise | 3 meses | 36 meses |
| Processamento das imagens | Local, no Raspberry Pi | Local, no PC industrial |
| Papel da nuvem | Backend, histórico, armazenamento e consulta | Backend, histórico, armazenamento e consulta |
| Aquisição de hardware | 100% dos materiais previstos | 100% dos materiais previstos |
| Desenvolvimento e trabalho técnico | Contribuição acadêmica sem remuneração na base de desembolso | Remuneração integral prevista |
| Frete estimado | 5% do hardware comprado | 5% do hardware comprado |
| Contingência inicial | 10% | 15% |

A capacidade de quatro câmeras por PC industrial é uma **hipótese de dimensionamento**, ainda dependente de testes de desempenho. Na implementação, a escolha de materiais mais caros considera proteção, alimentação elétrica, montagem, rede e manutenção. Isso não significa que todos os componentes estejam homologados para o ambiente do aviário: proteção IP65/IP67, por exemplo, não comprova resistência à amônia ou adequação às rotinas de lavagem.

Os prazos e escopos são diferentes. Portanto, o custo total de três meses da PoC não deve ser interpretado como alternativa equivalente ao custo de 36 meses da implementação.

## Principais resultados

Os valores abaixo seguem a **base de desembolsos e reservas**, sem licenças ainda não cotadas.

| Indicador | PoC | Implementação |
| --- | ---: | ---: |
| CAPEX físico, antes da contingência | R$ 1.989,12 | R$ 21.298,50 |
| Gastos iniciais adicionais | R$ 200,00 | R$ 54.400,00 |
| Contingência inicial | R$ 218,91 | R$ 11.354,77 |
| **Investimento inicial-base** | **R$ 2.408,03** | **R$ 87.053,27** |
| OPEX fixo mensal | R$ 123,74 | R$ 964,68 |
| OPEX variável mensal, incluindo reservas | R$ 15,35 | R$ 188,84 |
| **OPEX mensal-base** | **R$ 139,08** | **R$ 1.153,52** |
| **Custo-base no prazo de análise** | **R$ 2.825,28 em 3 meses** | **R$ 128.580,11 em 36 meses** |
| Benefício mensal mínimo para recuperar o investimento no prazo | R$ 941,76 | R$ 3.571,67 |
| Custo integral inicial, incluindo trabalho não remunerado | R$ 33.923,03 | R$ 87.053,27 |
| Benefício mensal ilustrativo | R$ 0,00 | R$ 2.841,75 |
| Saldo mensal após OPEX | −R$ 139,08 | R$ 1.688,23 |
| **ROI acumulado no prazo** | **−117,33% em 3 meses** | **−30,19% em 36 meses** |
| **Payback simples** | **Sem prazo finito na hipótese de benefício zero** | **51,56 meses** |

Os cálculos utilizam a precisão completa dos valores; o arredondamento para centavos ocorre na apresentação. Por isso, a soma de parcelas já arredondadas pode diferir em um centavo do total.

### Desembolso e custo integral

O desembolso da PoC é reduzido porque desenvolvimento, instalação, treinamento e suporte foram tratados como trabalho acadêmico não remunerado. **Isso não torna esse trabalho gratuito em termos econômicos.** A coluna de custo integral atribui valor às horas utilizadas e permite avaliar quanto custaria substituir essa contribuição por trabalho contratado.

Por essa razão, a PoC apresenta investimento inicial-base de **R$ 2.408,03**, mas custo integral inicial de **R$ 33.923,03**, ambos incluindo suas respectivas reservas de contingência. Seu OPEX mensal integral seria **R$ 446,58**, frente aos **R$ 139,08** da base de desembolsos e reservas. Na implementação, os valores já consideram remuneração integral da equipe.

## CAPEX e investimento inicial

O **CAPEX físico** reúne equipamentos, infraestrutura e instalação inicial. O **investimento inicial do projeto** é mais amplo: soma esse CAPEX aos gastos iniciais adicionais e à reserva de contingência.

Desenvolvimento, anotação de imagens, testes e treinamento foram apresentados separadamente para não tratar automaticamente todo gasto inicial como um ativo. O reconhecimento de desenvolvimento como ativo intangível depende de critérios específicos; pesquisa e treinamento não são automaticamente capitalizáveis. Essa distinção segue a referência do [CPC 04 (R1), especialmente os itens 54–57 e 69](https://www.cpc.org.br/Arquivos/Documentos/187_CPC_04_R1_rev%2021.pdf). A planilha é um orçamento gerencial, não uma classificação contábil definitiva.

### PoC: materiais para validação

| Item | Função | Quantidade | Total |
| --- | --- | ---: | ---: |
| Raspberry Pi 4 Model B, 4 GB | Capturar imagens e executar o processamento local | 1 | R$ 1.436,90 |
| Fonte USB-C oficial | Alimentar o Raspberry Pi | 1 | R$ 85,40 |
| microSD de 32 GB A2 | Armazenar sistema, aplicação e fila local | 1 | R$ 85,40 |
| Case | Proteger fisicamente a placa durante os testes | 1 | R$ 47,40 |
| Cooler e dissipador | Auxiliar no controle da temperatura | 1 | R$ 41,90 |
| Câmera CSI de 5 MP | Capturar imagens por conexão direta ao Raspberry | 1 | R$ 47,40 |
| Fixação e cabos curtos | Montar o ponto experimental | 1 conjunto | R$ 150,00 |
| **Equipamentos e materiais** | | | **R$ 1.894,40** |

O frete estimado acrescenta **R$ 94,72**, resultando em **R$ 1.989,12 de CAPEX físico na base de desembolso**. As cinco horas de instalação têm custo integral de R$ 450,00, mas não geram pagamento na premissa acadêmica.

Além do CAPEX, foram previstos **R$ 200,00 de computação para treinamento do modelo**. A contingência de 10% sobre o subtotal inicial acrescenta R$ 218,91, chegando ao investimento inicial-base de **R$ 2.408,03**.

### Implementação: materiais para operação em campo

| Item | Função | Quantidade | Total |
| --- | --- | ---: | ---: |
| PC industrial i5, 8 GB, SSD de 240 GB | Processamento local; fonte de 19 V incluída | 1 | R$ 9.978,49 |
| Câmera IP Intelbras VIP 3260 Z IA | Captura com lente ajustável e alimentação pela rede PoE | 4 | R$ 4.257,52 |
| Switch PoE industrial PUSR | Conectar e alimentar as quatro câmeras | 1 | R$ 690,00 |
| Fonte Mean Well HDR-60-48 | Alimentar o switch em 48 V | 1 | R$ 291,45 |
| Quadro metálico IP65 | Organizar e proteger os componentes | 1 | R$ 470,00 |
| Cabeamento e fixação das câmeras | Instalar os pontos de captura | 4 conjuntos | R$ 1.000,00 |
| Proteção elétrica e conexões | Preparar as ligações elétricas | 1 conjunto | R$ 350,00 |
| Adequação térmica e vedação | Adaptar a montagem ao ambiente | 1 conjunto | R$ 400,00 |
| Ligação à rede da propriedade | Conectar o aviário à infraestrutura existente | 1 conjunto | R$ 900,00 |
| Nobreak ATTIV 600 VA | Oferecer reserva de energia em local protegido | 1 | R$ 519,88 |
| **Equipamentos e materiais** | | | **R$ 18.857,34** |

Somam-se aos materiais **R$ 942,87 de frete**, **R$ 58,29 de reserva de tributos da fonte** anunciada sem impostos e **R$ 1.440,00 de instalação**, correspondentes a 16 horas a R$ 90,00. O CAPEX físico estimado chega a **R$ 21.298,50**. O adicional de 20% sobre a fonte é uma reserva de planejamento, não uma alíquota tributária confirmada.

### Desenvolvimento e adoção da solução

| Componente inicial | PoC: desembolso | Implementação: desembolso |
| --- | ---: | ---: |
| Desenvolvimento e dados | R$ 0,00 | R$ 53.000,00 |
| Computação para treinamento do modelo | R$ 200,00 | R$ 600,00 |
| Treinamento dos usuários | R$ 0,00 | R$ 800,00 |
| **Gastos iniciais adicionais** | **R$ 200,00** | **R$ 54.400,00** |

Desenvolvimento e dados abrangem captura e integração, painel, histórico, anotação de imagens, validação e documentação. A implementação acrescenta adaptação para falhas e operação offline, novas anotações e homologação em campo. As estimativas consideram R$ 100,00 por hora de desenvolvimento e validação e R$ 35,00 por hora de anotação. Na PoC, esse bloco tem custo integral de **R$ 27.800,00**, embora não haja desembolso previsto.

O orçamento completo considera a construção da solução. A planilha também apresenta um investimento adicional de **R$ 56.003,27 após a PoC**, considerando o reaproveitamento do trabalho inicial. Essa alternativa depende de validação técnica e não foi usada nos indicadores da tabela principal.

## OPEX: custos de operação

O **OPEX** representa os recursos necessários para manter a aplicação funcionando. Os custos fixos permanecem na escala contratada; podem aumentar quando for necessário adicionar servidores ou ampliar a equipe. Os variáveis dependem de consumo ou manutenção. As reservas para peças e bateria foram agrupadas com os variáveis estimados, mas são provisões orçamentárias, não pagamentos efetivos em todos os meses.

| Categoria | Item | PoC por mês | Implementação por mês |
| --- | --- | ---: | ---: |
| Fixo | Servidor virtual: backend e banco de dados | R$ 66,74 | R$ 133,49 |
| Fixo | Backup do servidor | R$ 13,35 | R$ 40,05 |
| Fixo | Pacote de armazenamento de imagens | R$ 27,81 | R$ 27,81 |
| Fixo | Domínio, com custo anual rateado | R$ 3,33 | R$ 3,33 |
| Fixo | Conectividade adicional | R$ 0,00 | R$ 0,00 |
| Fixo | Suporte recorrente | R$ 0,00 | R$ 600,00 |
| Fixo | Visitas programadas, com custo anual rateado | R$ 12,50 | R$ 160,00 |
| **Subtotal fixo** | | **R$ 123,74** | **R$ 964,68** |
| Variável | Energia elétrica | R$ 7,45 | R$ 61,27 |
| Variável | Armazenamento e tráfego acima das franquias | R$ 0,00 | R$ 0,00 |
| Variável estimado | Reserva para peças | R$ 7,89 | R$ 122,25 |
| Variável estimado | Reserva para bateria do nobreak | Não aplicável | R$ 5,32 |
| **Subtotal variável** | | **R$ 15,35** | **R$ 188,84** |
| **OPEX mensal-base** | | **R$ 139,08** | **R$ 1.153,52** |

Os serviços em dólar utilizam a referência cambial de **R$ 5,0564 por USD**, registrada na pesquisa de 19/10/2026, acrescida de 10% de reserva. A energia utiliza a hipótese de **R$ 1,00/kWh**, com dispositivos energizados 24 horas por dia e mês de 30 dias. Esses parâmetros devem ser substituídos pelas condições efetivas de contratação e consumo.

O orçamento considera o uso da rede existente e que os volumes estimados cabem nas franquias de nuvem.

A manutenção considera uma reserva anual de 5% do hardware da PoC e 8% na implementação, excluindo o nobreak. Para a bateria do nobreak, o preço de **R$ 127,74** foi distribuído ao longo de **24 meses**, resultando em uma reserva mensal de R$ 5,32.

## Benefício escolhido: evitar perdas de ovos orgânicos

O benefício econômico escolhido é preservar ovos orgânicos que, sem a solução e as ações de manejo apoiadas por ela, seriam perdidos. A aplicação acompanha aves na **recria**, antes da produção de ovos. Portanto, a ligação entre os indicadores, a intervenção no manejo e a redução futura de perdas ainda precisa ser demonstrada. Não se atribui ganho imediato à PoC.

O cálculo usa o **valor líquido incremental recuperável por ovo**, depois dos custos adicionais de produção e venda, antes do OPEX da aplicação. Preço de varejo, receita bruta e lucro não são equivalentes.

### Preço de mercado usado como referência

Foram consideradas duas ofertas comparáveis de **ovos orgânicos grandes Raiar, embalagem de 10 unidades**, consultadas em **01/11/2026**:

| Fonte | Preço da embalagem | Preço por ovo |
| --- | ---: | ---: |
| [Supernosso — catálogo Raiar](https://www.supernosso.com/raiar) | R$ 16,99 | R$ 1,6990 |
| [Raízs — ovos orgânicos vermelhos grandes Raiar](https://www.raizs.com.br/ovos-organicos-vermelhos-grandes-raiar/p) | R$ 20,90 | R$ 2,0900 |
| **Média simples da amostra** | **R$ 18,945** | **R$ 1,8945** |

A expressão “preço médio de mercado” nesta análise significa **média amostral de duas ofertas de varejo**, não média nacional, preço de venda do produtor ou valor efetivamente recebido pela Raiar. Preços, região, estoque e promoções podem variar. A escolha de mesma marca, classificação e tamanho de embalagem busca reduzir diferenças entre os produtos comparados.

A planilha calcula a média em **Custos e fontes!D9**, a partir dos preços e quantidades nas linhas 7 e 8, mantendo a precisão completa.

### Hipóteses ilustrativas do retorno

| Premissa | Valor inicial | Natureza |
| --- | ---: | --- |
| Ovos preservados por mês na implementação | 3.000 | Hipótese ilustrativa aprovada, sem medição do cliente |
| Parcela líquida do preço de varejo | 50% | Hipótese arbitrária para demonstrar o cálculo; não é margem pesquisada |
| Valor líquido recuperável por ovo | R$ 0,94725 | R$ 1,8945 × 50% |
| Prazo de avaliação da implementação | 36 meses | Horizonte de planejamento |
| Primeiro mês com benefício | 1 | Hipótese imediata; ajustar se o efeito ocorrer após a recria |
| Ovos preservados por mês na PoC | 0 | Não se assume retorno comercial durante a validação |

Os **3.000 ovos por mês e a parcela líquida de 50%** são hipóteses usadas na simulação. O valor líquido real deve ser informado pela Raiar.

O volume refere-se ao escopo atendido pelo projeto. Aumentar aviários ou câmeras recalcula os custos, mas **não multiplica automaticamente os ovos preservados**. O benefício exige uma estimativa própria, sem extrapolar a eficácia para toda a propriedade.

## Como substituir a simulação pelos dados da Raiar

Na aba **Premissas**, utilize a coluna **F** para implementação e **C** para PoC. Não apague as fórmulas das colunas D/G nem sobrescreva as referências de B/E para inserir dados do cliente.

| Linha | Campo | O que preencher |
| --- | --- | --- |
| 6 | Prazo de análise | Número de meses de avaliação |
| 7 | Primeiro mês com benefício | 1 para efeito imediato; 4 para três meses sem benefício, por exemplo |
| 8 | Ovos preservados por mês | Volume mensal incremental no método **Volume direto** |
| 9 | Método do volume | **Volume direto** ou **Produção e perdas** |
| 10 | Produção potencial | Ovos por mês antes das perdas, apenas da área atendida |
| 11 | Perda antes | Taxa anterior à intervenção, digitada como percentual |
| 12 | Perda após | Taxa esperada ou medida com a intervenção |
| 13 | Valor líquido por ovo | Receita incremental menos custos adicionais, ou custo efetivamente evitado por ovo |
| 14–15 | Licença inicial e mensal | Valores cotados; zero apenas se confirmado |
| 16–18 | Aviários e câmeras | Escopo e capacidade por processador, sujeitos a testes |
| 24–30 | Premissas financeiras | Compra de hardware, trabalho pago, frete, contingência, câmbio e reserva cambial |

Para uma atualização rápida da implementação, mantenha **Volume direto** em F9, informe os ovos preservados em **F8** e o valor líquido em **F13**. Os indicadores recalculam automaticamente.

Para usar produção e taxas, selecione **Produção e perdas** em **F9** e preencha **F10:F12**. Nesse modo, o volume direto de F8 é ignorado. Se faltar qualquer um dos três valores, os indicadores dependentes ficam como `n.a.`, sem tratar a ausência como zero. Por exemplo, 100.000 ovos/mês, perda anterior de 5% e posterior de 2% resultam em 3.000 ovos/mês preservados. Esse exemplo também não é dado real da Raiar.

Se a perda posterior superar a anterior, o benefício fica negativo: o modelo evidencia piora, sem limitar artificialmente a diferença a zero.

Para recuperar a referência inicial, limpe a célula da coluna “Seu valor”. Um **zero permanece zero** e não reativa o valor de referência. Preencher apenas alguns campos ainda deixa os demais baseados nas hipóteses; isso não transforma toda a análise em orçamento validado pelo cliente.

Preços de materiais, horas e parâmetros técnicos podem ser revistos em **Custos e fontes**. A parcela líquida ilustrativa está em **D10** dessa aba; para usar um valor líquido real, prefira informar diretamente F13/C13 em Premissas. Assim, a referência de mercado permanece registrada.

## Lógica dos cálculos

O retorno usa o **investimento inicial total**, incluindo os gastos adicionais e a contingência, não apenas o CAPEX físico.

```text
Ovos preservados = volume direto informado
OU
Ovos preservados = produção potencial × (perda antes − perda após)

Benefício mensal = ovos preservados × valor líquido recuperável por ovo

Investimento inicial = CAPEX físico + gastos iniciais adicionais
                     + contingência + licença inicial informada

OPEX mensal = OPEX fixo + OPEX variável + licença mensal informada

Meses com benefício = máximo(0; prazo − primeiro mês com benefício + 1)
Custo no horizonte = investimento inicial + OPEX mensal × prazo
Benefício acumulado = benefício mensal × meses com benefício
Resultado no horizonte = benefício acumulado − custo no horizonte
ROI acumulado = resultado no horizonte ÷ investimento inicial
Saldo mensal = benefício mensal − OPEX mensal
```

O OPEX começa no mês 1, mesmo se o benefício surgir depois. Com benefício desde o primeiro mês:

```text
Payback simples = investimento inicial ÷ saldo mensal
```

Se houver atraso de `d = primeiro mês com benefício − 1`:

```text
Payback = d + (investimento inicial + OPEX mensal × d) ÷ saldo mensal
```

O payback só tem prazo finito quando o saldo mensal é positivo. Ele supõe benefício e OPEX constantes após o início dos ganhos, inclusive além do horizonte se o prazo calculado o ultrapassar. O ROI não é anualizado. Não se aplicam desconto financeiro ou inflação.

### Resultado inicial da implementação

```text
Benefício mensal = 3.000 × R$ 0,94725 = R$ 2.841,75
Saldo mensal = R$ 2.841,75 − R$ 1.153,523414… = R$ 1.688,226585…

Custo em 36 meses = R$ 87.053,27155 + 36 × R$ 1.153,523414…
                  = R$ 128.580,114478
Benefício em 36 meses = R$ 2.841,75 × 36 = R$ 102.303,00
Resultado em 36 meses = −R$ 26.277,114478

ROI = −R$ 26.277,114478 ÷ R$ 87.053,27155 = −30,19%
Payback = R$ 87.053,27155 ÷ R$ 1.688,226585… = 51,56 meses
```

**A implementação não recupera o investimento nos 36 meses da simulação.** O payback de aproximadamente 51,6 meses pressupõe continuidade dos mesmos ganhos e custos depois desse período. Um atraso entre recria e produção aumenta o prazo de retorno e reduz o ROI.

Na PoC, o benefício inicial é zero: o ROI de **−117,33% em três meses** representa o investimento e a operação sem retorno monetário assumido. O valor abaixo de −100% ocorre porque, além do investimento inicial, existem despesas operacionais. Isso não avalia o valor técnico do aprendizado produzido pela PoC.

### Benefício mínimo para recuperar o investimento

```text
Benefício mensal mínimo = custo no horizonte ÷ meses com benefício
Ovos/mês para se pagar = benefício mensal mínimo ÷ valor líquido por ovo
```

Na implementação, com benefício desde o mês 1, o ganho mínimo é **R$ 3.571,67/mês**. Ao valor líquido ilustrativo de R$ 0,94725, são necessários **3.771 ovos/mês**, arredondados para cima. Na PoC, a meta orçamentária equivalente é R$ 941,76/mês, ou 995 ovos/mês sob o mesmo valor unitário; não se presume que essa recuperação ocorra durante a validação.

Esses limites representam equilíbrio financeiro do orçamento adotado, não previsão de eficácia da solução.

## Limites e validação

- **Licenças:** ainda não cotadas. O único conjunto de indicadores incorpora qualquer valor informado e exclui os campos vazios, mantendo o aviso. Preencher ambos, inclusive zero confirmado, muda o status para “Informadas”. A licença inicial é somada sem outra contingência sobre ela; a mensal compõe o OPEX fixo.
- **Origem dos valores:** preços dos ovos são referências de varejo; volume recuperado, parcela líquida, horas, frete e contingência são hipóteses de planejamento. Não representam economia comprovada, cotação final ou dados reais do cliente.
- **Escopo e tempo:** a solução atua na recria. É necessário medir a relação entre os indicadores, as decisões de manejo e as perdas posteriores, considerando lotes e períodos comparáveis e evitando dupla contagem.
- **Custos constantes:** não foram incluídos inflação, financiamento, desconto financeiro, tributação do resultado, depreciação ou valor residual. Obras civis, novas rotas de fibra, GPU dedicada e integrações corporativas continuam fora do orçamento.
- **Leitura gerencial:** reservas para manutenção e contingência são provisões orçamentárias. Não equivalem a desembolsos efetivos em cada mês.

Antes de uma decisão de implantação, devem ser confirmados inventário, cotações, capacidade de processamento, consumo, licenças e valor líquido por ovo. A medição da redução de perdas permitirá substituir a hipótese ilustrativa por evidência do cliente.
