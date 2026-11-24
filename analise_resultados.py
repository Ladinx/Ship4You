import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.ticker import FuncFormatter

# mesmo valor que o matriz_transporte.py usa para rotas sem caminho
PENALIDADE = 99999.0


# ---------------------------------------------------------------------------
# 1) Custo real da Olist
# ---------------------------------------------------------------------------
def calcular_custo_real(pasta_dados="dataset-tratado"):
    """
    Soma 'freight_value' do order_items_clean.csv, so dos pedidos entregues
    (mesma base e mesmo filtro que o matriz_transporte.py usa), para a
    comparacao com o Vogel ser justa.
    """
    from matriz_transporte import carregar_dados_base

    df = carregar_dados_base(pasta_dados)
    return float(df["freight_value"].sum())


# ---------------------------------------------------------------------------
# 2) Resumo dos numeros
# ---------------------------------------------------------------------------
def montar_resumo(custo_real, custo_total, custos, alocacao):
    custo_total = float(custo_total)
    economia = custo_real - custo_total
    itens = float(alocacao.sum())
    return {
        "custo_real": custo_real,
        "custo_vogel": custo_total,
        "economia_reais": economia,
        "economia_pct": (economia / custo_real * 100) if custo_real else 0.0,
        "itens": itens,
        "custo_medio_real": custo_real / itens if itens else 0.0,
        "custo_medio_vogel": custo_total / itens if itens else 0.0,
        "itens_em_penalidade": float(alocacao[custos >= PENALIDADE].sum()),
    }


def imprimir_resumo(resumo):
    print("=" * 50)
    print("RESUMO: CUSTO REAL x CUSTO VOGEL")
    print("=" * 50)
    print(f"Itens alocados:        {resumo['itens']:>16,.0f}")
    print(f"Custo real (Olist):    R$ {resumo['custo_real']:>13,.2f}")
    print(f"Custo Vogel:           R$ {resumo['custo_vogel']:>13,.2f}")
    print(f"Economia:              R$ {resumo['economia_reais']:>13,.2f}")
    print(f"Economia (%):             {resumo['economia_pct']:>13.2f}%")
    print(f"Frete medio real:      R$ {resumo['custo_medio_real']:>13,.2f} por item")
    print(f"Frete medio Vogel:     R$ {resumo['custo_medio_vogel']:>13,.2f} por item")
    print("=" * 50)
    if resumo["itens_em_penalidade"] > 0:
        print(f"ATENCAO: {resumo['itens_em_penalidade']:,.0f} itens foram alocados em rotas "
              f"sem caminho (custo de penalidade {PENALIDADE:,.0f}). "
              f"O custo do Vogel esta inflado.")


# ---------------------------------------------------------------------------
# 3) Graficos
# ---------------------------------------------------------------------------
def _formatar_qtd(v):
    return f"{v / 1000:.1f}k" if v >= 1000 else f"{int(v)}"


def grafico_mapa_calor(alocacao, origens, destinos, pasta, mostrar=False):
    """Mapa de calor (escala log) dos itens enviados em cada rota."""
    dados = np.ma.masked_where(alocacao <= 0, alocacao)
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad("#f2f2f2")  # rotas sem uso ficam cinza claro

    # escala log: sem ela, 1 ou 2 rotas gigantes (ex.: SP -> SP) apagam o resto
    usar_log = dados.count() > 0 and dados.min() < dados.max()
    norm = LogNorm(vmin=dados.min(), vmax=dados.max()) if usar_log else None

    fig, ax = plt.subplots(figsize=(max(7, len(destinos) * 0.5), max(5, len(origens) * 0.45)))
    im = ax.imshow(dados, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(len(destinos)))
    ax.set_xticklabels(destinos, rotation=90)
    ax.set_yticks(range(len(origens)))
    ax.set_yticklabels(origens)
    ax.set_xlabel("Destino (estado comprador)")
    ax.set_ylabel("Origem (estado vendedor)")
    ax.set_title("Rotas mais usadas (itens alocados pelo Vogel)")
    fig.colorbar(im, ax=ax, label="Itens" + (" (escala log)" if usar_log else ""))

    # escreve o numero so nas rotas relevantes (>= 1% do total)
    limite = max(1, 0.01 * alocacao.sum())
    for i, j in zip(*np.where(alocacao >= limite)):
        cor = "white" if im.norm(alocacao[i, j]) > 0.6 else "black"
        ax.text(j, i, _formatar_qtd(alocacao[i, j]), ha="center", va="center",
                fontsize=7, color=cor)

    fig.tight_layout()
    fig.savefig(os.path.join(pasta, "mapa_calor_rotas.png"), dpi=150)
    if mostrar:
        plt.show()
    plt.close(fig)


def grafico_barras_custos(resumo, pasta, mostrar=False):
    """Barras comparando Custo Real x Custo Vogel."""
    fig, ax = plt.subplots(figsize=(6, 5))
    valores = [resumo["custo_real"], resumo["custo_vogel"]]
    barras = ax.bar(["Custo real (Olist)", "Custo Vogel"], valores, color=["#c0392b", "#27ae60"])
    for barra, v in zip(barras, valores):
        ax.text(barra.get_x() + barra.get_width() / 2, v, f"R$ {v:,.0f}",
                ha="center", va="bottom", fontsize=9)
    palavra = "Economia" if resumo["economia_reais"] >= 0 else "Aumento de custo"
    ax.set_ylabel("Custo total de frete (R$)")
    # eixo em reais (sem notação científica 1e6), mais legível na apresentação
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"R$ {v:,.0f}".replace(",", ".")))
    ax.set_title(f"{palavra} de {abs(resumo['economia_pct']):.2f}% "
                 f"(R$ {abs(resumo['economia_reais']):,.0f})")
    fig.tight_layout()
    fig.savefig(os.path.join(pasta, "custo_real_vs_vogel.png"), dpi=150)
    if mostrar:
        plt.show()
    plt.close(fig)


def grafico_rotas_sobrecarregadas(alocacao, origens, destinos, pasta, top_n=10, mostrar=False):
    """As top_n rotas com mais itens e a fatia de cada uma no total."""
    total = alocacao.sum()
    rotas = [(origens[i], destinos[j], alocacao[i, j])
             for i in range(alocacao.shape[0])
             for j in range(alocacao.shape[1])
             if alocacao[i, j] > 0 and "DUMMY" not in (origens[i], destinos[j])]
    rotas.sort(key=lambda r: r[2], reverse=True)
    rotas = rotas[:top_n][::-1]  # maior em cima no barh

    rotulos = [f"{o} → {d}" for o, d, _ in rotas]
    qtds = [q for _, _, q in rotas]

    fig, ax = plt.subplots(figsize=(8, max(3, len(rotas) * 0.45)))
    barras = ax.barh(rotulos, qtds, color="#e67e22")
    for barra, q in zip(barras, qtds):
        ax.text(q, barra.get_y() + barra.get_height() / 2,
                f" {int(q):,} ({q / total * 100:.1f}%)", va="center", fontsize=8)
    ax.set_xlabel("Itens alocados")
    ax.set_title(f"Rotas mais carregadas (top {len(rotas)})")
    ax.set_xlim(0, max(qtds) * 1.25)
    fig.tight_layout()
    fig.savefig(os.path.join(pasta, "rotas_sobrecarregadas.png"), dpi=150)
    if mostrar:
        plt.show()
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4) Funcao principal (entrega final)
# ---------------------------------------------------------------------------
def analisar_resultados(custos, alocacao, custo_total,
                        origens=None, destinos=None,
                        custo_real=None, pasta_saida="graficos",
                        mostrar=False):
    """
    Gera os graficos e o resumo dos numeros.

    custos, alocacao : matrizes (origens x destinos)
    custo_total      : custo final calculado pelo Vogel
    origens/destinos : nomes (UFs) para os eixos; se None, usa O1.., D1..
    custo_real       : use o 'custo_real_historico' do gerar_matriz_transporte();
                       se None, calcula pelo CSV (somente pedidos entregues)
    mostrar          : True abre as janelas dos graficos (alem de salvar)

    Retorna um dict com o resumo.
    """
    custos = np.asarray(custos, dtype=float)
    alocacao = np.asarray(alocacao, dtype=float)

    if custos.shape != alocacao.shape:
        raise ValueError("'custos' e 'alocacao' precisam ter o mesmo formato.")

    origens = list(origens) if origens is not None else [f"O{i + 1}" for i in range(alocacao.shape[0])]
    destinos = list(destinos) if destinos is not None else [f"D{j + 1}" for j in range(alocacao.shape[1])]

    if len(origens) != alocacao.shape[0] or len(destinos) != alocacao.shape[1]:
        raise ValueError("'origens'/'destinos' nao batem com o tamanho da matriz "
                         "(lembre da linha/coluna DUMMY, se houver).")

    if custo_real is None:
        custo_real = calcular_custo_real()

    os.makedirs(pasta_saida, exist_ok=True)

    resumo = montar_resumo(custo_real, custo_total, custos, alocacao)
    imprimir_resumo(resumo)

    grafico_mapa_calor(alocacao, origens, destinos, pasta_saida, mostrar)
    grafico_barras_custos(resumo, pasta_saida, mostrar)
    grafico_rotas_sobrecarregadas(alocacao, origens, destinos, pasta_saida, mostrar=mostrar)

    print(f"Graficos salvos em '{pasta_saida}/'")
    return resumo


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------
def executar_com_dados_reais():
    """Matriz (Matheus) -> Vogel (Becca) -> Analise (bender)."""
    from matriz_transporte import gerar_matriz_transporte
    from vogel import resolver_vogel

    custos, oferta, demanda, origens, destinos, custo_real = gerar_matriz_transporte()
    alocacao, custo_total = resolver_vogel(custos, oferta, demanda)

    return analisar_resultados(custos, alocacao, custo_total,
                               origens=origens, destinos=destinos,
                               custo_real=custo_real)


def executar_exemplo():
    """Matriz pequena so para testar o visual, sem precisar dos CSVs."""
    origens = ["SP", "MG", "PR"]
    destinos = ["RJ", "BA", "RS", "SC"]

    custos = np.array([
        [12, 25, 22, 18],
        [15, 22, 28, 24],
        [25, 32, 14, 10],
    ])

    # linhas somam a oferta (60, 40, 50) e colunas somam a demanda (40, 30, 50, 30)
    alocacao = np.array([
        [30, 30, 0, 0],
        [10, 0, 0, 30],
        [0, 0, 50, 0],
    ])

    custo_total = float((custos * alocacao).sum())
    return analisar_resultados(custos, alocacao, custo_total,
                               origens=origens, destinos=destinos,
                               custo_real=3100.0, pasta_saida="graficos_exemplo")


if __name__ == "__main__":
    if "--exemplo" in sys.argv:
        executar_exemplo()
    else:
        executar_com_dados_reais()