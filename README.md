# Pesquisa Operacional I

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

| Tabela | Uso |
|---|---|
| `order_items` | valor do frete e vendedor |
| `orders` | filtrar apenas os pedidos entregues |
| `customers` e `sellers` | estados de origem e destino |
| `geolocation` | coordenadas dos CEPs |

> **Nota sobre os dados:** o dataset já está tratado e o script de tratamento está neste repositório. Os dados em si não podem ser disponibilizados no GitHub devido às licenças de uso impostas pela Olist.

## C) Por que o Método de Vogel é o mais adequado

O nosso problema é, por natureza, um **problema de transporte**: estados que vendem uma quantidade limitada de itens, estados que compram e um custo de frete diferente para cada rota, com o objetivo de decidir quanto enviar de cada origem para cada destino gastando o mínimo.

O dataset, agregado por estado, fornece as três entradas do método: **oferta** (itens enviados por cada estado vendedor), **demanda** (itens recebidos por cada estado comprador) e **matriz de custo** (frete médio por item em cada rota).

Como essa matriz tem rotas com custos bem diferentes entre si, o Vogel é uma boa escolha: ele leva em conta o que se perde ao deixar de usar as rotas mais baratas, e pode ser mostrado passo a passo.

## D) Rascunho da Modelagem Formal

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
\min Z = \sum_{i} \sum_{j} c_{ij} x_{ij}
```

### Restrições

Oferta de cada origem:

```math
\sum_{j} x_{ij} = o_i \quad \forall i
```

Demanda de cada destino:

```math
\sum_{i} x_{ij} = d_j \quad \forall j
```

Não-negatividade:

```math
x_{ij} \ge 0 \quad \forall i, j
```

### Condição de equilíbrio

```math
\sum_{i} o_i = \sum_{j} d_j
```

Se não fechar, adiciona-se uma origem ou um destino fictício com custo $c = 0$.
