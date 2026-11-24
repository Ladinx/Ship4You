# Ship4You — Relatório da execução

Gerado automaticamente por `main.py` (integração: Arthur).

## 1. Cenário executado

- Filtros: nenhum (base completa)
- Itens entregues: 110.197 (2016-09-15 a 2018-08-29)
- Matriz de custo: 22 origens x 27 destinos (594 rotas)
- Rotas com histórico no recorte: 412; estimadas pela base completa: 182
- Centros de distribuição: SP, MG, PR, PE, GO; alpha (desconto de consolidação): 0,70

## 2. Resultado (frete real x alocação do Vogel)

| Indicador | Valor |
|---|---|
| Frete real pago na Olist | R$ 2.198.275,64 |
| Custo da alocação do Vogel | R$ 1.880.223,44 |
| Economia | R$ 318.052,20 (14,47%) |
| Frete médio real | R$ 19,95 por item |
| Frete médio Vogel | R$ 17,06 por item |

## 3. Validação das restrições do modelo

| Restrição | Situação | Detalhe |
|---|---|---|
| Equilíbrio: soma oferta = soma demanda | OK | 110.197 = 110.197 itens |
| Oferta de cada origem escoada (Σj x_ij = o_i) | OK | 22 origens conferidas |
| Demanda de cada destino atendida (Σi x_ij = d_j) | OK | 27 destinos conferidos |
| Domínio: x_ij inteiro e não negativo | OK | itens indivisíveis (Z>=0) |
| Custo total coerente (Σ c_ij · x_ij) | OK | R$ 1.880.223,44 |
| Nenhum item em rota inexistente | OK | 0 itens em rotas sem caminho |

## 4. Rotas mais carregadas (top 10)

| Origem | Destino | Itens | R$/item | Custo total | % do volume |
|---|---|---|---|---|---|
| SP | SP | 46.448 | R$ 13,20 | R$ 612.964,07 | 42,15% |
| SP | RJ | 9.458 | R$ 20,39 | R$ 192.838,55 | 8,58% |
| MG | MG | 8.557 | R$ 17,13 | R$ 146.554,70 | 7,77% |
| PR | PR | 5.649 | R$ 15,76 | R$ 89.002,63 | 5,13% |
| RJ | RJ | 4.685 | R$ 12,45 | R$ 58.315,15 | 4,25% |
| SP | MG | 4.351 | R$ 20,25 | R$ 88.094,04 | 3,95% |
| SC | SC | 4.000 | R$ 17,18 | R$ 68.739,60 | 3,63% |
| SP | BA | 3.059 | R$ 24,32 | R$ 74.391,27 | 2,78% |
| PR | RS | 2.415 | R$ 21,15 | R$ 51.086,03 | 2,19% |
| SP | ES | 2.225 | R$ 20,54 | R$ 45.710,86 | 2,02% |

## 6. Leitura do resultado

A alocação do Vogel atende exatamente a mesma oferta e a mesma demanda da operação real (110.197 itens) e reduz o frete médio de R$ 19,95 para R$ 17,06 por item, uma economia de R$ 318.052,20 (14,47%).

A rota SP -> SP concentra 42,15% do volume: ganho de custo, mas exige capacidade e contrato de frete nessa rota para a economia se sustentar.

O Vogel é uma heurística: a solução é factível e respeita todas as restrições, mas não é prova de otimalidade — o valor serve como limite prático de comparação com o frete efetivamente pago.

## 7. Tempo de execução

| Etapa | Tempo (s) |
|---|---|
| matriz | 1.525 |
| vogel | 0.010 |
| analise | 2.134 |
