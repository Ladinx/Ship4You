# Pesquisa Operacional

## Integrantes

- Arthur Soares Padia
- Rebecca Beccari Fagundes
- João Gabriel Bender Martins
- Matheus Silva dos Santos

## A) Trilha Algorítmica Selecionada

**2. Transporte / Designação (Húngaro/Vogel)**

## B) Problema e dataset

O problema que escolhemos é reduzir o custo de frete do e-commerce brasileiro. Para isso, imaginamos a **Ship4You**, uma empresa fictícia de logística que avalia criar centros de distribuição pelo país, com o intuito de baratear o frete.

Os dados vêm do [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), disponível no Kaggle, com cerca de 100 mil pedidos reais. Escolhemos essa base porque ela mostra de onde cada item saiu, para onde foi e quanto custou o frete.

| Tabela | Colunas usadas | Uso |
|---|---|---|
| `order_items` | `order_id`, `seller_id`, `freight_value` | valor do frete e vendedor |
| `orders` | `order_id`, `customer_id`, `order_status` | filtrar apenas os pedidos entregues |
| `customers` | `customer_id`, `customer_state` | estado de destino |
| `sellers` | `seller_id`, `seller_state` | estado de origem |
| `geolocation` | `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng` | coordenadas dos CEPs |

Após o tratamento, a base tem **110.197 itens entregues**, com **22 estados vendedores** e **27 estados compradores**. O frete médio é de **19,95 reais por item**, o que representa **16,63%** do valor dos produtos. O frete pesa bastante no preço final, então reduzi-lo tem impacto direto no custo do e-commerce.

## C) Por que o Método de Vogel é o mais adequado

O nosso problema é, por natureza, um **problema de transporte**: estados que vendem uma quantidade limitada de itens, estados que compram e um custo de frete diferente para cada rota, com o objetivo de decidir quanto enviar de cada origem para cada destino gastando o mínimo.

O dataset, agregado por estado, fornece as três entradas do método: **oferta** (itens enviados por cada estado vendedor), **demanda** (itens recebidos por cada estado comprador) e **matriz de custo** (frete médio por item em cada rota).

Como essa matriz tem rotas com custos bem diferentes entre si, o Vogel é uma boa escolha: ele leva em conta o que se perde ao deixar de usar as rotas mais baratas, e pode ser mostrado passo a passo.

Na prática, cada parâmetro vem de uma agregação do dataset:
- **Oferta** $o_i$: contagem de itens por `seller_state`
- **Demanda** $d_j$: contagem de itens por `customer_state`
- **Custo** $c_{ij}$: média de `freight_value` por par (`seller_state`, `customer_state`)

A matriz de custo tem dimensão 22 × 27 (594 rotas), das quais 182 não possuem pedidos.

Comparando, o Húngaro serve para pareamento 1:1, mas aqui cada estado envia volumes diferentes a vários destinos, o que caracteriza um problema de transporte e justifica o Vogel (VAM).

## D) Rascunho da Modelagem Formal

### Conjuntos

$i \in I$ = estados vendedores (origens) e $j \in J$ = estados compradores (destinos).

### Variável de decisão

$x_{ij}$ = quantidade de itens enviados do estado vendedor $i$ (origem) para o estado comprador $j$ (destino).

### Parâmetros

| Símbolo | Significado | Unidade |
|---|---|---|
| $c_{ij}$ | frete médio por item da rota $i \to j$ | reais por item |
| $o_i$ | oferta da origem $i$ | itens |
| $d_j$ | demanda do destino $j$ | itens |

### Função objetivo

Minimizar o custo total de frete (em reais):
```math
\Large \boxed{\min Z = \sum_{i} \sum_{j} c_{ij} x_{ij}}
```
### Restrições

Oferta de cada origem:
```math
\Large \sum_{j} x_{ij} = o_i \quad \forall i
```
Demanda de cada destino:
```math
\Large \sum_{i} x_{ij} = d_j \quad \forall j
```
Domínio (itens indivisíveis, o que já garante a não-negatividade):
```math
\Large x_{ij} \in \mathbb{Z}_{\ge 0} \quad \forall i, j
```

### Centros de distribuição

O envio pode passar por um CD $h$ quando isso sai mais barato que o envio direto. O custo da rota $i \to j$ passa a ser:

```math
\Large c'_{ij} = \min \left( c_{ij}, \; \min_{h} \left[ \alpha \, c_{ih} + c_{hj} \right] \right)
```

onde $`\alpha`$ é o desconto de consolidação no trecho até o CD. A função objetivo usa $`c'_{ij}`$ no lugar de $`c_{ij}`$.

**Premissas:** $\alpha$ (desconto de consolidação) e os CDs candidatos serão definidos na implementação. Testaremos mais de um valor de $\alpha$ para medir o quanto a economia depende dele.

Como cada item entregue tem exatamente um estado de origem e um de destino, a oferta total e a demanda total são iguais (110.197 itens), então o problema já é balanceado.

Rotas sem pedidos usam só o caminho via CD.

### Condição de equilíbrio
```math
\Large \sum_{i} o_i = \sum_{j} d_j
```

## E) Como instalar e executar

### 1. Instalação

Requisitos: Python 3.10 ou superior.

```bash
cd Ship4You
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # pandas, numpy, matplotlib
```

Os CSVs tratados já estão em `dados/`, então não é preciso rodar a limpeza
(`src/limpeza_olist.py`) de novo. Os CSVs originais do Kaggle (~120 MB) não ficam
no repositório; se precisar refazer o tratamento, rode
`python3 src/limpeza_olist.py --brutos /caminho/dos/csvs-brutos`.

### 2. Rodar o projeto inteiro com um comando

```bash
python3 src/main.py
```

O programa é **interativo**: abre um menu e depois faz as perguntas do cenário.
Basta apertar **Enter** para aceitar o padrão (base completa, `alpha = 0,70`,
gráficos ligados). Não é preciso decorar argumento nenhum.

```
O que você quer fazer?
  [1] Rodar a otimização (matriz -> Vogel -> gráficos)   <- padrão
  [2] Rodar o exemplo pequeno (teste rápido, sem os dados)
  [3] Ver as categorias de produto e o período da base
```

Depois o `src/main.py` executa as três partes na ordem certa:

| Ordem | Arquivo | Responsável | O que faz |
|---|---|---|---|
| 1 | `src/matriz_transporte.py` | Matheus | monta `custos`, `oferta` e `demanda` a partir do dataset |
| 2 | `src/vogel.py` | Rebecca | resolve o transporte pelo Vogel e devolve `alocacao` e `custo_total` |
| 3 | `src/analise_resultados.py` | Bender | compara com o frete real e gera os gráficos |

Arquivos gerados em `saidas/`:

| Arquivo | Conteúdo |
|---|---|
| `graficos/mapa_calor_rotas.png` | mapa de calor das rotas mais usadas |
| `graficos/custo_real_vs_vogel.png` | barras Custo Real x Custo Vogel |
| `graficos/rotas_sobrecarregadas.png` | rotas mais carregadas |
| `graficos/sensibilidade_alpha.png` | curva custo x desconto do CD (só se ligar a análise de sensibilidade) |
| `alocacao.csv` | matriz de alocação completa (`origem`, `destino`, `itens`, `custo`) |
| `relatorio.md` | relatório pronto para anexar/apresentar |

### 3. As perguntas (filtros)

Depois do menu, o `main.py` pergunta o cenário antes de rodar a otimização:

| Pergunta | O que faz | Padrão (Enter) |
|---|---|---|
| **1) Recorte da base** | `[1]` base completa, `[2]` por categoria, `[3]` por período, `[4]` categoria + período | base completa |
| **1.1) Categoria** (se escolher 2 ou 4) | mostra as 10 categorias mais frequentes e aceita número ou nome | a primeira da lista |
| **1.2) Período** (se escolher 3 ou 4) | pede data inicial e final (AAAA-MM-DD) | sem limite |
| **2) alpha** | desconto de consolidação no trecho até o CD (1,00 = frete cheio) | 0,70 |
| **3) Centros de distribuição** | mantém SP, MG, PR, PE, GO ou aceita outras UFs | manter |
| **4) Resultados** | liga/desliga gráficos, janelas na tela e análise de sensibilidade | gráficos sim, resto não |

No fim ele mostra um resumo do que vai rodar e pergunta "Rodar agora?".

A execução também pode ser feita sem as perguntas, usando os padrões:

```bash
python3 src/main.py --sem-perguntas
```

A opção 2 do menu roda uma matriz pequena com dados conhecidos e salva em
`saidas/exemplo/`; serve para verificar a instalação sem os CSVs tratados.

### 4. Estratégia dos filtros

Quando um filtro é aplicado, várias rotas deixam de ter pedidos dentro do recorte.
Para não jogar itens em rotas de penalidade, o recorte mantém o frete médio
observado **naquele filtro** e usa o frete médio histórico da mesma rota na base
completa como estimativa quando não há pedido. O `main.py` informa quantas rotas
foram estimadas em cada execução.

## F) Como o Método de Vogel foi aplicado

1. **Montagem (Matheus):** cada item entregue da Olist vira uma linha com UF de
   origem, UF de destino e frete. Agrupar por UF gera a oferta `o_i` (itens que
   saem de cada estado), a demanda `d_j` (itens que chegam) e o custo `c_ij`
   (frete médio por item de cada rota).
2. **Centros de distribuição (regra do item D):** o custo de cada rota passa a ser
   `c'_ij = min(c_ij, min_h [alpha·c_ih + c_hj])`, ou seja, o envio direto só é
   mantido quando nenhum CD candidato é mais barato.
3. **Balanceamento:** `Σo_i = Σd_j = 110.197` itens. Se um recorte desbalancear, é
   criada uma linha ou coluna fictícia (`DUMMY`) de custo zero, como pede o método.
4. **Vogel (Rebecca):** a cada iteração o algoritmo calcula a **penalidade** de
   cada linha e de cada coluna (diferença entre o custo mais barato e o segundo
   mais barato daquela linha/coluna), escolhe a **maior penalidade** — a que mais
   custa deixar de usar — e aloca o **máximo possível** na célula de menor custo
   daquela linha/coluna. A origem ou o destino que zera sai do problema e o
   processo se repete até acabar a oferta e a demanda.
5. **Custo final:** `custo_total = Σ c'_ij · x_ij`, comparado com o frete
   efetivamente pago na base (`Σ freight_value`).
6. **Validação:** o `main.py` recompõe as somas e confere, restrição por restrição,
   que a solução é factível (oferta escoada, demanda atendida, `x_ij` inteiro e não
   negativo, custo coerente e nenhum item em rota sem caminho).

## G) Resultados obtidos

Execução padrão (`python3 src/main.py`, base completa, `alpha = 0,7`,
CDs: SP, MG, PR, PE, GO):

| Indicador | Valor |
|---|---|
| Itens entregues analisados | 110.197 |
| Matriz de custo | 22 origens x 27 destinos (594 rotas) |
| Frete real pago na Olist | R$ 2.198.275,64 |
| Custo da alocação do Vogel | R$ 1.880.223,44 |
| **Economia** | **R$ 318.052,20 (14,47%)** |
| Frete médio por item | R$ 19,95 → R$ 17,06 |
| Tempo de execução | ~1,3 s matriz + 0,03 s Vogel + ~2,7 s gráficos |

Todas as restrições do modelo são validadas na execução (saída "todas as
restrições do modelo foram respeitadas").

**Rotas mais carregadas pelo Vogel:**

| Origem | Destino | Itens | R$/item | % do volume |
|---|---|---|---|---|
| SP | SP | 46.448 | 13,20 | 42,15% |
| SP | RJ | 9.458 | 20,39 | 8,58% |
| MG | MG | 8.557 | 17,13 | 7,77% |
| PR | PR | 5.649 | 15,76 | 5,13% |
| RJ | RJ | 4.685 | 12,45 | 4,25% |

**Sensibilidade ao desconto de consolidação (pergunta 6 do modo interativo):**

| alpha | Custo Vogel | Economia |
|---|---|---|
| 0,30 | R$ 1.841.091,50 | 16,25% |
| 0,50 | R$ 1.868.883,95 | 14,98% |
| 0,70 | R$ 1.880.223,44 | 14,47% |
| 0,85 | R$ 1.874.958,79 | 14,71% |
| 1,00 | R$ 1.875.216,31 | 14,70% |

**Leitura crítica (o que fazer com o número):**

- Mesmo com `alpha = 1,0` (CD sem nenhum desconto, ou seja, só a realocação entre
  rotas), a economia fica em ~14,7%. Isso mostra que **a maior parte do ganho vem de
  mandar cada volume pela rota de menor frete médio**, e não do desconto hipotético
  de consolidação. O desconto do CD é um ganho adicional, não a causa principal.
- O resultado é sensível a `alpha` de forma fraca e não monótona (0,85 apareceu
  ligeiramente mais caro que 0,70): o Vogel é heurístico e a ordem gulosa de
  alocação muda com o custo das rotas. Para o relatório, o número a usar é a faixa
  de 14,5% a 16,3% de economia, não um valor único.
- Cerca de 42% do volume fica em SP → SP. Ganho de custo alto, mas concentra risco
  operacional: exige capacidade e contrato de frete nessa rota para a economia se
  sustentar. As rotas SP → RJ e MG → MG vêm em seguida (8,6% e 7,8%).
- O Vogel é uma **heurística**: garante solução factível e muito próxima do ótimo,
  mas não prova de otimalidade. O número serve como comparação prática com o frete
  realmente pago.

## H) Estrutura do projeto

```
Ship4You/
├── src/                     # código do pipeline
│   ├── main.py              # integração, filtros, execução e relatório (Arthur)
│   ├── matriz_transporte.py # oferta, demanda, matriz de custo e regra dos CDs (Matheus)
│   ├── vogel.py             # Método de Vogel (Rebecca)
│   ├── analise_resultados.py# comparação com o frete real e gráficos (Bender)
│   ├── limpeza_olist.py     # limpeza dos CSVs originais do Olist
│   └── caminhos.py          # resolve dados/ e saidas/ de qualquer diretório
├── dados/                   # CSVs tratados usados na execução
├── saidas/                  # o que o main.py gera (figuras, CSV e relatório)
├── dashboard/               # dashboard visual (abre no navegador, sem servidor)
├── docs/                    # briefing da equipe e material de apoio
├── requirements.txt         # dependências do projeto
├── LICENSE
└── README.md                # este arquivo
```

## I) Onde cada item da rubrica está no projeto

| Critério | Onde está |
|---|---|
| 2.1 Funcionamento e forma de cálculo | `src/vogel.py`: penalidades de linha e coluna, escolha da maior penalidade e alocação máxima na célula de menor custo. A regra dos CDs aparece descrita em palavras na saída do `main.py` e na seção D. |
| 2.2 Implementação em Python | `src/main.py`: carrega a base, executa o pipeline, valida as restrições do modelo e mede o tempo de cada etapa. |
| 2.3 Exibição visual | `saidas/graficos/`: mapa de calor das rotas, barras Custo Real x Vogel, rotas mais carregadas e curva de sensibilidade. Versão interativa em `dashboard/index.html`. |
| 2.5 Contexto e análise crítica | `saidas/relatorio.md` (seção 6) e seção G deste README: economia em reais e em %, decisão prática e concentração de volume. |

