"""
gerar_dashboard.py — exporta os resultados do pipeline para o dashboard visual.

Responsável: apoio visual (dashboard), sem tocar no pipeline existente.

O que este script faz (uma vez, em Python):
  1. roda matriz_transporte -> vogel -> validação, exatamente como o main.py;
  2. lê a base tratada para os agregados descritivos (UF, mês, categoria);
  3. monta o mapa do Brasil a partir dos CEPs (lat/lng) projetados em Albers;
  4. escreve dashboard/dados.js com tudo pronto.

O dashboad no navegador só desenha: nenhum número é recalculado em JS.

Uso:
    cd Ship4You
    python3 dashboard/gerar_dashboard.py
    # depois abrir dashboard/index.html no navegador
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from analise_resultados import PENALIDADE          # noqa: E402
from main import ALPHAS_PADRAO, CDS_PADRAO, validar_solucao  # noqa: E402
from matriz_transporte import carregar_dados_base, gerar_matriz_transporte  # noqa: E402
from vogel import resolver_vogel                    # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.path.join(RAIZ, "dataset-tratado")

NOMES_UF = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}


# ---------------------------------------------------------------------------
# 1) Projeção (Albers equal-area, cônica, padrão para o Brasil)
# ---------------------------------------------------------------------------
class Albers:
    """Projeção cônica de Albers — devolve x,y já normalizados para a tela."""

    def __init__(self, lat1=-2.0, lat2=-22.0, lat0=-12.0, lon0=-51.0):
        self.p1, self.p2, self.p0, self.l0 = map(math.radians, (lat1, lat2, lat0, lon0))
        self.n = 0.5 * (math.sin(self.p1) + math.sin(self.p2))
        self.C = math.cos(self.p1) ** 2 + 2 * self.n * math.sin(self.p1)
        self.rho0 = math.sqrt(self.C - 2 * self.n * math.sin(self.p0)) / self.n
        self.largura = None
        self.altura = None
        self.x0 = self.y0 = 0.0

    def bruto(self, lat, lon):
        rho = math.sqrt(self.C - 2 * self.n * math.sin(math.radians(lat))) / self.n
        theta = self.n * (math.radians(lon) - self.l0)
        return rho * math.sin(theta), self.rho0 - rho * math.cos(theta)

    def calibrar(self, pontos, largura=1000.0):
        """Ajusta a escala/deslocamento para o conjunto de pontos caber em 'largura'."""
        xy = np.array([self.bruto(lat, lon) for lat, lon in pontos])
        xmin, ymin = xy.min(axis=0)
        xmax, ymax = xy.max(axis=0)
        escala = largura / (xmax - xmin)
        self.escala = escala
        self.x0, self.y0 = xmin, ymin
        self.largura = largura
        self.altura = (ymax - ymin) * escala
        return self

    def projetar(self, lat, lon):
        x, y = self.bruto(lat, lon)
        px = (x - self.x0) * self.escala
        py = (y - self.y0) * self.escala
        return round(px, 2), round(self.altura - py, 2)  # y para baixo (tela)


# ---------------------------------------------------------------------------
# 2) Convex hull (monotone chain) para o contorno aproximado de cada UF
# ---------------------------------------------------------------------------
def convex_hull(pontos):
    pts = sorted(set(pontos))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    baixo, cima = [], []
    for p in pts:
        while len(baixo) >= 2 and cross(baixo[-2], baixo[-1], p) <= 0:
            baixo.pop()
        baixo.append(p)
    for p in reversed(pts):
        while len(cima) >= 2 and cross(cima[-2], cima[-1], p) <= 0:
            cima.pop()
        cima.append(p)
    return baixo[:-1] + cima[:-1]


def suavizar(poligono, max_pontos=42):
    """Reduz o número de vértices mantendo o formato (amostragem uniforme)."""
    if len(poligono) <= max_pontos:
        return poligono
    passo = len(poligono) / max_pontos
    reduzido = [poligono[int(i * passo)] for i in range(max_pontos)]
    return reduzido + [reduzido[0]]


# ---------------------------------------------------------------------------
# 3) Mapa: grade de calor e contornos a partir dos CEPs
# ---------------------------------------------------------------------------
def unidade_por_grau(proj: Albers) -> float:
    """Quantas unidades do mapa equivalem a 1 grau (usado para o tamanho das células)."""
    x0, _ = proj.bruto(-15.0, -51.0)
    x1, _ = proj.bruto(-15.0, -50.0)
    return abs(x1 - x0) * proj.escala


def montar_mapa(proj: Albers, df_base: pd.DataFrame):
    """Grade de densidade (0,25°) + contornos por UF + centróides, tudo dos CEPs."""
    geo = pd.read_csv(os.path.join(PASTA_DADOS, "geolocation_clean.csv"))

    # Peso de cada CEP = itens entregues naquele estado (para centróide e hull)
    itens_uf = df_base.groupby("customer_state").size()
    itens_uf = itens_uf[itens_uf > 0]

    # --- centróides por UF (dentro da faixa central, sem outliers extremos) ---
    centroides = {}
    for uf, grupo in geo.groupby("state"):
        vals = grupo
        if len(vals) >= 20:
            lo, hi = vals["lat"].quantile([0.02, 0.98])
            vals = vals[(vals["lat"] >= lo) & (vals["lat"] <= hi)]
        x, y = proj.projetar(float(vals["lat"].median()), float(vals["lng"].median()))
        centroides[uf] = [x, y]

    # --- contornos aproximados ---
    contornos = []
    for uf, grupo in geo.groupby("state"):
        # amostra limitada por UF (percentis para cortar CEPs isolados)
        amostra = grupo
        if len(amostra) > 400:
            amostra = amostra.sample(400, random_state=7)
        pts = [proj.projetar(float(r.lat), float(r.lng)) for r in amostra.itertuples()]
        hull = convex_hull(pts)
        if len(hull) >= 3:
            contornos.append({"uf": uf, "pts": suavizar(hull)})

    # --- grade de calor: pedidos entregues (peso = itens) ---
    pedidos = pd.read_csv(
        os.path.join(PASTA_DADOS, "olist_analitico.csv"),
        usecols=["cust_lat", "cust_lng", "n_items", "total_freight", "is_delivered"],
        low_memory=False,
    )
    pedidos = pedidos[(pedidos["is_delivered"] == True)
                      & pedidos["cust_lat"].notna()
                      & pedidos["cust_lng"].notna()
                      & (pedidos["cust_lat"] > -35) & (pedidos["cust_lat"] < 6)
                      & (pedidos["cust_lng"] > -75) & (pedidos["cust_lng"] < -32)]

    passo = 0.25
    lat_bin = (pedidos["cust_lat"] / passo).round().astype(int)
    lng_bin = (pedidos["cust_lng"] / passo).round().astype(int)
    agrupado = pedidos.groupby([lat_bin, lng_bin]).agg(
        itens=("n_items", "sum"),
        frete=("total_freight", "sum"),
        pedidos=("n_items", "size"),
    ).reset_index()
    agrupado.columns = ["latb", "lngb", "itens", "frete", "pedidos"]

    grade = []
    for r in agrupado.itertuples():
        lat = r.latb * passo
        lng = r.lngb * passo
        x, y = proj.projetar(float(lat), float(lng))
        grade.append({
            "x": x, "y": y,
            "i": int(r.itens),
            "p": int(r.pedidos),
            "f": round(float(r.frete), 2),
        })
    grade.sort(key=lambda c: -c["i"])

    # calibração final: usa a extensão dos pontos do mapa
    return grade, contornos, centroides


# ---------------------------------------------------------------------------
# 4) Agregados descritivos (UF, mês, categoria)
# ---------------------------------------------------------------------------
def agregados(df: pd.DataFrame):
    por_uf_origem = df.groupby("seller_state").agg(
        itens=("freight_value", "size"),
        frete=("freight_value", "sum"),
        frete_medio=("freight_value", "mean"),
    )
    por_uf_destino = df.groupby("customer_state").agg(
        itens=("freight_value", "size"),
        frete=("freight_value", "sum"),
        frete_medio=("freight_value", "mean"),
    )

    mes = pd.to_datetime(df["order_purchase_timestamp"]).dt.strftime("%Y-%m")
    por_mes = df.assign(mes=mes).groupby("mes").agg(
        itens=("freight_value", "size"),
        frete=("freight_value", "sum"),
        preco=("price", "sum"),
    ).reset_index()

    por_categoria = df.groupby("product_category_name").agg(
        itens=("freight_value", "size"),
        frete=("freight_value", "sum"),
        frete_medio=("freight_value", "mean"),
        preco=("price", "sum"),
    ).reset_index()
    por_categoria = por_categoria[por_categoria["itens"] >= 200].sort_values(
        "itens", ascending=False)

    return por_uf_origem, por_uf_destino, por_mes, por_categoria


# ---------------------------------------------------------------------------
# 5) Pipeline (mesmo do main.py) + montagem do pacote
# ---------------------------------------------------------------------------
def rodar_pipeline():
    custos, oferta, demanda, origens, destinos, custo_real, info = gerar_matriz_transporte(
        cds_candidatos=CDS_PADRAO, alpha=0.70, pasta_dados=PASTA_DADOS, return_info=True)
    alocacao, custo_total = resolver_vogel(custos, oferta, demanda)
    cenario = {
        "custos": custos, "oferta": oferta, "demanda": demanda,
        "origens": origens, "destinos": destinos, "custo_real": custo_real,
        "info": info, "alpha": 0.70, "cds": CDS_PADRAO,
    }
    checks = validar_solucao(cenario, alocacao, custo_total)
    return cenario, alocacao, custo_total, checks


def rodar_sensibilidade(alpha_atual=0.70):
    linhas = []
    for a in sorted(ALPHAS_PADRAO):
        custos, oferta, demanda, _, _, custo_real = gerar_matriz_transporte(
            cds_candidatos=CDS_PADRAO, alpha=a, pasta_dados=PASTA_DADOS)
        _, custo_total = resolver_vogel(custos, oferta, demanda)
        linhas.append({
            "alpha": a,
            "custo_vogel": round(float(custo_total), 2),
            "economia_reais": round(float(custo_real - custo_total), 2),
            "economia_pct": round(float((custo_real - custo_total) / custo_real * 100), 2),
            "atual": abs(a - alpha_atual) < 1e-9,
        })
    return linhas


def montar_matriz(custos, alocacao, origens, destinos):
    """Matriz sem a linha/coluna DUMMY (o dashboard mostra só UFs reais)."""
    linhas = [k for k, o in enumerate(origens) if o != "DUMMY"]
    colunas = [k for k, d in enumerate(destinos) if d != "DUMMY"]
    return {
        "origens": [origens[k] for k in linhas],
        "destinos": [destinos[k] for k in colunas],
        "custo": [[round(float(custos[i][j]), 2) for j in colunas] for i in linhas],
        "aloc": [[int(round(float(alocacao[i][j]))) for j in colunas] for i in linhas],
    }


def montar_pacote():
    print("[1/5] rodando matriz + Vogel (cenário padrão) ...")
    cenario, alocacao, custo_total, checks = rodar_pipeline()
    custos = np.asarray(cenario["custos"], dtype=float)
    origens, destinos = cenario["origens"], cenario["destinos"]

    print("[2/5] carregando a base tratada ...")
    df = carregar_dados_base(PASTA_DADOS)

    print("[3/5] agregados de UF, mês e categoria ...")
    uf_o, uf_d, por_mes, por_cat = agregados(df)

    print("[4/5] projetando o mapa dos CEPs ...")
    geo = pd.read_csv(os.path.join(PASTA_DADOS, "geolocation_clean.csv"))
    proj = Albers()
    amostra = geo.sample(min(len(geo), 4000), random_state=1)
    proj.calibrar([(float(r.lat), float(r.lng)) for r in amostra.itertuples()], largura=1000.0)
    grade, contornos, centroides = montar_mapa(proj, df)

    print("[5/5] sensibilidade e empacotamento ...")
    sensibilidade = rodar_sensibilidade(0.70)

    # --- rotas: alocação do Vogel + frete real médio observado na mesma rota ---
    real_rota = df.groupby(["seller_state", "customer_state"]).agg(
        frete_real=("freight_value", "mean"),
        itens_reais=("freight_value", "size"),
    )
    total_itens = float(alocacao.sum())
    rotas = []
    for i, o in enumerate(origens):
        for j, d in enumerate(destinos):
            qtd = float(alocacao[i][j])
            if qtd <= 0:
                continue
            chave = (o, d)
            frete_real = float(real_rota.loc[chave, "frete_real"]) if chave in real_rota.index else None
            itens_reais = int(real_rota.loc[chave, "itens_reais"]) if chave in real_rota.index else 0
            cu = float(custos[i][j])
            rotas.append({
                "o": o, "d": d,
                "itens": int(round(qtd)),
                "cu": round(cu, 2),
                "ct": round(qtd * cu, 2),
                "pct": round(qtd / total_itens * 100, 2) if total_itens else 0.0,
                "real": round(frete_real, 2) if frete_real is not None else None,
                "itens_reais": itens_reais,
            })
    rotas.sort(key=lambda r: -r["itens"])

    # --- UF: oferta/demanda, custo real x Vogel saindo e entrando ---
    ufs = {}
    for i, uf in enumerate(origens):
        if uf == "DUMMY":
            continue
        itens_aloc = float(alocacao[i, :].sum())
        custo_vogel = float((custos[i, :] * alocacao[i, :]).sum())
        real = float(uf_o.loc[uf, "frete"]) if uf in uf_o.index else 0.0
        ufs.setdefault(uf, {})["origem"] = {
            "itens": int(uf_o.loc[uf, "itens"]) if uf in uf_o.index else 0,
            "frete_real": round(real, 2),
            "frete_medio": round(real / itens_aloc, 2) if itens_aloc else 0.0,
            "custo_vogel": round(custo_vogel, 2),
            "frete_medio_vogel": round(custo_vogel / itens_aloc, 2) if itens_aloc else 0.0,
            "economia": round(real - custo_vogel, 2),
        }
    for j, uf in enumerate(destinos):
        if uf == "DUMMY":
            continue
        itens_aloc = float(alocacao[:, j].sum())
        custo_vogel = float((custos[:, j] * alocacao[:, j]).sum())
        real = float(uf_d.loc[uf, "frete"]) if uf in uf_d.index else 0.0
        ufs.setdefault(uf, {})["destino"] = {
            "itens": int(uf_d.loc[uf, "itens"]) if uf in uf_d.index else 0,
            "frete_real": round(real, 2),
            "frete_medio": round(real / itens_aloc, 2) if itens_aloc else 0.0,
            "custo_vogel": round(custo_vogel, 2),
            "frete_medio_vogel": round(custo_vogel / itens_aloc, 2) if itens_aloc else 0.0,
            "economia": round(real - custo_vogel, 2),
        }

    for uf, dados in ufs.items():
        dados["nome"] = NOMES_UF.get(uf, uf)
        dados["xy"] = centroides.get(uf)
        dados["cd"] = uf in CDS_PADRAO

    # --- arcos das rotas mais carregadas (bezier: o ECharts não curva no cartesiano) ---
    def arco_curvo(p0, p1, pontos=26, curvatura=0.16):
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        dist = math.hypot(dx, dy) or 1.0
        # deslocamento perpendicular, sempre para o mesmo lado (arco "voando" para cima)
        cx = mx - dy * curvatura
        cy = my + dx * curvatura
        saida = []
        for k in range(pontos + 1):
            t = k / pontos
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * cx + t ** 2 * p1[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * cy + t ** 2 * p1[1]
            saida.append([round(x, 2), round(y, 2)])
        return saida

    arcos = []
    for r in rotas[:18]:
        a, b = centroides.get(r["o"]), centroides.get(r["d"])
        if not a or not b:
            continue
        arcos.append({
            "o": r["o"], "d": r["d"], "itens": r["itens"], "pct": r["pct"],
            "a": a, "b": b, "pts": arco_curvo(a, b),
        })

    # --- extensão real do desenho (para o eixo do mapa não cortar o país) ---
    xs = [c["x"] for c in grade] + [p[0] for c in contornos for p in c["pts"]]
    ys = [c["y"] for c in grade] + [p[1] for c in contornos for p in c["pts"]]
    xs += [c[0] for c in centroides.values()]
    ys += [c[1] for c in centroides.values()]
    extensao = {
        "x0": math.floor(min(xs)) - 8, "x1": math.ceil(max(xs)) + 8,
        "y0": math.floor(min(ys)) - 8, "y1": math.ceil(max(ys)) + 8,
    }

    itens = float(cenario["info"]["itens"])
    pacote = {
        "meta": {
            "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "fonte": "Brazilian E-Commerce Public Dataset by Olist (Kaggle)",
            "alpha": cenario["alpha"],
            "cds": CDS_PADRAO,
            "data_min": cenario["info"]["data_min"][:10],
            "data_max": cenario["info"]["data_max"][:10],
            "n_origens": len(origens),
            "n_destinos": len(destinos),
            "rotas_possiveis": cenario["info"]["rotas_possiveis"],
            "rotas_com_historico": cenario["info"]["rotas_com_historico_no_recorte"],
            "rotas_estimadas": cenario["info"]["rotas_estimadas_pela_base_completa"],
        },
        "kpis": {
            "itens": int(itens),
            "custo_real": round(float(cenario["custo_real"]), 2),
            "custo_vogel": round(float(custo_total), 2),
            "economia": round(float(cenario["custo_real"] - custo_total), 2),
            "economia_pct": round(float((cenario["custo_real"] - custo_total)
                                        / cenario["custo_real"] * 100), 2),
            "frete_medio_real": round(float(cenario["custo_real"] / itens), 2),
            "frete_medio_vogel": round(float(custo_total / itens), 2),
            "rotas_ativas": len(rotas),
            "rotas_possiveis": int(cenario["info"]["rotas_possiveis"]),
        },
        "rotas": rotas,
        "checks": checks,
        "sensibilidade": sensibilidade,
        "ufs": ufs,
        "meses": [
            {"ym": r.mes, "itens": int(r.itens), "frete": round(float(r.frete), 2),
             "preco": round(float(r.preco), 2)}
            for r in por_mes.itertuples()
        ],
        "categorias": [
            {"nome": r.product_category_name, "itens": int(r.itens),
             "frete": round(float(r.frete), 2), "frete_medio": round(float(r.frete_medio), 2)}
            for r in por_cat.itertuples()
        ],
        "mapa": {
            "largura": round(proj.largura, 2),
            "altura": round(proj.altura, 2),
            "escala_grau": round(unidade_por_grau(proj), 4),
            "extensao": extensao,
            "passo_grau": 0.25,
            "grade": grade,
            "contornos": contornos,
            "arcos": arcos,
        },
        "matriz": montar_matriz(custos, alocacao, origens, destinos),
    }
    return pacote


def main():
    pacote = montar_pacote()
    destino = os.path.join(AQUI, "dados.js")
    with open(destino, "w", encoding="utf-8") as f:
        f.write("// gerado por dashboard/gerar_dashboard.py — não editar à mão\n")
        f.write("window.DADOS = ")
        json.dump(pacote, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    tamanho = os.path.getsize(destino) / 1024
    print(f"\nOK  {destino} ({tamanho:.0f} KB)")
    print(f"    itens={pacote['kpis']['itens']:,} | real=R$ {pacote['kpis']['custo_real']:,.2f}"
          f" | vogel=R$ {pacote['kpis']['custo_vogel']:,.2f}"
          f" | economia={pacote['kpis']['economia_pct']:.2f}%")
    print("    abra dashboard/index.html no navegador")


if __name__ == "__main__":
    main()
