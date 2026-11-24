# Ship4You — dashboard visual

Apoio visual para apresentar os resultados do Vogel. **Não calcula nada no navegador:**
todos os números vêm do pipeline Python (`matriz_transporte` → `vogel` → validação), exportados
uma vez por `gerar_dashboard.py`. O `app.js` só desenha.

## Como abrir

Duplo clique em `index.html` (funciona em `file://`, sem servidor e sem internet).

- `1`–`5` ou `←` `→` trocam de aba.
- `#rotas`, `#mapa`, `#sensibilidade`, `#validacao` abrem direto numa aba.
  `#mapa-SP` abre o mapa com o estado já selecionado.
- **Modo apresentação** aumenta a tipografia e entra em tela cheia (bom para gravar).
- Cada card tem um botão **PNG**; o botão do topo exporta os gráficos da aba atual.

## Como regenerar os dados

```bash
cd Ship4You
python3 dashboard/gerar_dashboard.py     # ~17 s, escreve dashboard/dados.js
```

O script roda o **mesmo** cenário do `main.py` (base completa, `alpha = 0,70`,
CDs SP·MG·PR·PE·GO), a análise de sensibilidade para os cinco valores de `alpha`
e os agregados descritivos da base tratada. Se algum parâmetro do cenário mudar no
`main.py`, rode este script de novo: o dashboard acompanha.

Referência de conferência (deve ser idêntico a `resultados/relatorio.md`):

| Indicador | Valor |
|---|---|
| Itens entregues | 110.197 |
| Frete real pago | R$ 2.198.275,64 |
| Custo do Vogel | R$ 1.880.223,44 |
| Economia | R$ 318.052,20 (14,47%) |

## Abas

| Aba | O que mostra |
|---|---|
| 1. Visão geral | Cascata frete real → custo Vogel, composição do custo, economia por estado vendedor, volume e frete por mês |
| 2. Rotas | Matriz origem × destino (escala log), volume × custo unitário por rota, tabela ordenável das rotas mais carregadas |
| 3. Mapa do Brasil | Calor por célula de 0,25° montado dos CEPs, contornos aproximados por UF, arcos das 18 rotas maiores; clique num estado para ver oferta, demanda e economia dele |
| 4. Sensibilidade | Custo do Vogel para cada `alpha`, com o frete real pago como referência |
| 5. Validação | As seis restrições do modelo conferidas na solução + diagnóstico do recorte |

## Mapa sem biblioteca de mapas

O mapa é desenhado direto dos CEPs (`dataset-tratado/geolocation_clean.csv` e as
coordenadas dos pedidos em `olist_analitico.csv`), sem Leaflet, tiles ou malha do IBGE:

- **projeção** cônica de Albers calculada em Python (`Albers` em `gerar_dashboard.py`);
- **calor** = células de 0,25° ponderadas por itens entregues;
- **contornos** = convex hull dos CEPs de cada UF;
- **arcos** = curvas de Bézier pré-calculadas entre centróides dos estados.

## Arquivos

```
dashboard/
├── index.html            # markup e estrutura
├── style.css             # tema escuro
├── app.js                # desenho dos gráficos e interação (sem cálculo de modelo)
├── dados.js              # gerado: todos os números e coordenadas
├── gerar_dashboard.py    # exporta dados.js a partir do pipeline
└── vendor/echarts.min.js # biblioteca de gráficos (local, não usa CDN)
```

`main.py`, `vogel.py`, `matriz_transporte.py` e `analise_resultados.py` não são alterados
por este dashboard.
