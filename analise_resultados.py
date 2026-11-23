import os

import matplotlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CAMINHO_ORDER_ITEMS = os.path.join("dataset-tratado", "order_items_clean.csv")


# ---------------------------------------------------------------------------
# 1) Custo real da Olist
# ---------------------------------------------------------------------------
def calcular_custo_real(caminho_csv=CAMINHO_ORDER_ITEMS):
    """Soma a coluna 'freight_value' do order_items_clean.csv."""
    df = pd.read_csv(caminho_csv, usecols=["freight_value"])
    return float(df["freight_value"].sum())


# ---------------------------------------------------------------------------
# 2) Resumo dos numeros
# ---------------------------------------------------------------------------
def montar_resumo(custo_real, custo_total):
    economia = custo_real - custo_total
    economia_pct = (economia / custo_real * 100) if custo_real else 0.0
    return {
        "custo_real": custo_real,
        "custo_vogel": custo_total,
        "economia_reais": economia,
        "economia_pct": economia_pct,
    }


def imprimir_resumo(resumo):
    print("=" * 45)
    print("RESUMO: CUSTO REAL x CUSTO VOGEL")
    print("=" * 45)
    print(f"Custo real (Olist):  R$ {resumo['custo_real']:>14,.2f}")
    print(f"Custo Vogel:         R$ {resumo['custo_vogel']:>14,.2f}")
    print(f"Economia:            R$ {resumo['economia_reais']:>14,.2f}")
    print(f"Economia (%):           {resumo['economia_pct']:>14.2f}%")
    print("=" * 45)


# ---------------------------------------------------------------------------
# 3) Graficos
# ---------------------------------------------------------------------------
def grafico_mapa_calor(alocacao, origens, destinos, pasta, mostrar=False):
    """Mapa de calor: quantos itens foram enviados em cada rota."""
    fig, ax = plt.subplots(figsize=(max(6, len(destinos) * 0.6), max(4, len(origens) * 0.5)))
    im = ax.imshow(alocacao, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(destinos)))
    ax.set_xticklabels(destinos, rotation=90)
    ax.set_yticks(range(len(origens)))
    ax.set_yticklabels(origens)
    ax.set_xlabel("Destino (estado comprador)")
    ax.set_ylabel("Origem (estado vendedor)")
    ax.set_title("Rotas mais usadas (itens alocados pelo Vogel)")
    fig.colorbar(im, ax=ax, label="Itens")

    # escreve o numero dentro das celulas so quando a matriz e pequena
    if alocacao.size <= 150:
        for i in range(alocacao.shape[0]):
            for j in range(alocacao.shape[1]):
                if alocacao[i, j] > 0:
                    ax.text(j, i, f"{int(alocacao[i, j])}", ha="center", va="center", fontsize=8)

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
    ax.set_ylabel("Custo total de frete (R$)")
    ax.set_title(f"Economia de {resumo['economia_pct']:.2f}% "
                 f"(R$ {resumo['economia_reais']:,.0f})")
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
             if alocacao[i, j] > 0]
    rotas.sort(key=lambda r: r[2], reverse=True)
    rotas = rotas[:top_n][::-1]  # maior em cima no barh

    rotulos = [f"{o} → {d}" for o, d, _ in rotas]
    qtds = [q for _, _, q in rotas]

    fig, ax = plt.subplots(figsize=(8, max(3, len(rotas) * 0.45)))
    barras = ax.barh(rotulos, qtds, color="#e67e22")
    for barra, q in zip(barras, qtds):
        ax.text(q, barra.get_y() + barra.get_height() / 2,
                f" {int(q)} ({q / total * 100:.1f}%)", va="center", fontsize=8)
    ax.set_xlabel("Itens alocados")
    ax.set_title(f"Rotas mais carregadas (top {len(rotas)})")
    ax.set_xlim(0, max(qtds) * 1.2)
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
    custo_real       : se None, le do order_items_clean.csv
    mostrar          : True abre as janelas dos graficos (alem de salvar)

    Retorna um dict com o resumo.
    """
    custos = np.asarray(custos, dtype=float)
    alocacao = np.asarray(alocacao, dtype=float)

    if custos.shape != alocacao.shape:
        raise ValueError("'custos' e 'alocacao' precisam ter o mesmo formato.")

    origens = list(origens) if origens is not None else [f"O{i + 1}" for i in range(alocacao.shape[0])]
    destinos = list(destinos) if destinos is not None else [f"D{j + 1}" for j in range(alocacao.shape[1])]

    if custo_real is None:
        custo_real = calcular_custo_real()

    os.makedirs(pasta_saida, exist_ok=True)

    resumo = montar_resumo(custo_real, custo_total)
    imprimir_resumo(resumo)

    grafico_mapa_calor(alocacao, origens, destinos, pasta_saida, mostrar)
    grafico_barras_custos(resumo, pasta_saida, mostrar)
    grafico_rotas_sobrecarregadas(alocacao, origens, destinos, pasta_saida, mostrar=mostrar)

    print(f"Graficos salvos em '{pasta_saida}/'")
    return resumo


# ---------------------------------------------------------------------------
# Teste com dados de exemplo (trocar pelos dados reais depois)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    origens_ex = ["SP", "MG", "PR"]
    destinos_ex = ["RJ", "BA", "RS", "SC"]

    custos_ex = np.array([
        [12, 25, 22, 18],
        [15, 22, 28, 24],
        [25, 32, 14, 10],
    ])

    # linhas somam a oferta (60, 40, 50) e colunas somam a demanda (40, 30, 50, 30)
    alocacao_ex = np.array([
        [30, 30, 0, 0],
        [10, 0, 0, 30],
        [0, 0, 50, 0],
    ])

    custo_total_ex = float((custos_ex * alocacao_ex).sum())
    custo_real_ex = 3100.0  # no projeto: calcular_custo_real()

    analisar_resultados(custos_ex, alocacao_ex, custo_total_ex,
                        origens=origens_ex, destinos=destinos_ex,
                        custo_real=custo_real_ex, mostrar=False)
