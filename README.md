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
