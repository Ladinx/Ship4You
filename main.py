"""
Integração, execução e documentação do projeto Ship4You.

Responsável: Arthur (integração, execução e documentação).

Pipeline executado aqui, na ordem da divisão de tarefas:

    matriz_transporte.gerar_matriz_transporte   (Matheus) -> custos, oferta, demanda
    vogel.resolver_vogel                        (Becca)   -> alocacao, custo_total
    analise_resultados.analisar_resultados      (Bender)  -> gráficos + resumo

Além de chamar as três partes, este arquivo:
  - aplica filtros simples (período da compra e categoria do produto) antes de rodar;
  - mede o tempo de cada etapa do pipeline;
  - valida as restrições do modelo de transporte na solução do Vogel;
  - salva os artefatos da entrega (alocação em CSV, resumo em JSON e relatório em Markdown);
  - opcionalmente faz a análise de sensibilidade do desconto de consolidação (alpha).

Exemplos de uso:
    python3 main.py                                    # base completa, alpha = 0.7
    python3 main.py --exemplo                          # teste rápido, sem os CSVs
    python3 main.py --categoria cama_mesa_banho         # recorte por categoria
    python3 main.py --data-inicio 2018-01-01 --data-fim 2018-06-30
    python3 main.py --alpha 0.5 --cds SP,MG,PR          # muda CDs e desconto
    python3 main.py --sensibilidade                     # varre vários alpha
    python3 main.py --listar-categorias                 # ajuda a escolher o filtro
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from analise_resultados import (
    PENALIDADE,
    analisar_resultados,
    imprimir_resumo,
    montar_resumo,
)
from matriz_transporte import carregar_dados_base, gerar_matriz_transporte
from vogel import resolver_vogel

# Centros de distribuição testados por padrão (grandes hubs logísticos)
CDS_PADRAO = ["SP", "MG", "PR", "PE", "GO"]

# Valores de alpha usados na análise de sensibilidade
ALPHAS_PADRAO = [0.3, 0.5, 0.7, 0.85, 1.0]


# ---------------------------------------------------------------------------
# Formatação de números no padrão brasileiro
# ---------------------------------------------------------------------------
def moeda(valor: float) -> str:
    """R$ 1.880.223,44"""
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "_").replace(".", ",").replace("_", ".")


def numero(valor: float, casas: int = 0) -> str:
    """110.197"""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def percentual(valor: float) -> str:
    """14,47%"""
    return f"{valor:.2f}".replace(".", ",") + "%"


def decimal(valor: float, casas: int = 2) -> str:
    """0,70 — para ler o alpha no padrão brasileiro"""
    return f"{valor:.{casas}f}".replace(".", ",")


def titulo(texto: str) -> None:
    print()
    print("=" * 72)
    print(texto)
    print("=" * 72)

# ---------------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------------
def criar_parser() -> argparse.ArgumentParser:
    """Define os filtros e parâmetros que podem ser passados antes de rodar."""
    p = argparse.ArgumentParser(
        description="Ship4You — Matriz de transporte -> Vogel -> Gráficos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--alpha", type=float, default=0.7,
                   help="desconto de consolidação no trecho até o CD, de 0 a 1 (padrão: 0.7)")
    p.add_argument("--cds", default=",".join(CDS_PADRAO),
                   help=f"UFs candidatas a centro de distribuição (padrão: {','.join(CDS_PADRAO)})")
    p.add_argument("--data-inicio", default=None, metavar="AAAA-MM-DD",
                   help="filtra pedidos comprados a partir desta data")
    p.add_argument("--data-fim", default=None, metavar="AAAA-MM-DD",
                   help="filtra pedidos comprados até esta data (inclusive)")
    p.add_argument("--categoria", default=None,
                   help="uma ou mais categorias de produto separadas por vírgula "
                        "(use --listar-categorias para ver os nomes)")
    p.add_argument("--dados", default="dataset-tratado",
                   help="pasta com os CSVs tratados (padrão: dataset-tratado)")
    p.add_argument("--saida", default="resultados",
                   help="pasta de saída dos gráficos, CSV, JSON e relatório (padrão: resultados)")
    p.add_argument("--sem-graficos", action="store_true",
                   help="roda matriz + Vogel sem gerar os gráficos (execução rápida)")
    p.add_argument("--mostrar", action="store_true",
                   help="além de salvar, abre as janelas dos gráficos na tela")
    p.add_argument("--sensibilidade", nargs="*", type=float, default=None, metavar="ALPHA",
                   help="analisa o custo para vários alpha (padrão: 0.3 0.5 0.7 0.85 1.0)")
    p.add_argument("--top", type=int, default=10,
                   help="quantas rotas listar no relatório (padrão: 10)")
    p.add_argument("--exemplo", action="store_true",
                   help="roda a matriz pequena de exemplo (não precisa dos CSVs)")
    p.add_argument("--listar-categorias", action="store_true",
                   help="lista as categorias disponíveis e o período da base")
    return p


# ---------------------------------------------------------------------------
# Etapa 1: monta o cenário (matriz de custos, oferta e demanda)
# ---------------------------------------------------------------------------
def obter_filtros(args) -> dict:
    """Converte os argumentos de filtro no dicionário que a matriz espera."""
    filtros = {}
    if args.data_inicio:
        filtros["data_inicio"] = args.data_inicio
    if args.data_fim:
        filtros["data_fim"] = args.data_fim
    if args.categoria:
        filtros["categorias"] = [c.strip() for c in args.categoria.split(",") if c.strip()]
    return filtros


def construir_cenario(args, alpha: float = None) -> dict:
    """
    Chama a modelagem de dados (Matheus) e devolve tudo o que o resto do
    pipeline precisa, já com os filtros aplicados.
    """
    cds = [c.strip().upper() for c in args.cds.split(",") if c.strip()]
    alpha = args.alpha if alpha is None else alpha

    custos, oferta, demanda, origens, destinos, custo_real, info = gerar_matriz_transporte(
        cds_candidatos=cds,
        alpha=alpha,
        pasta_dados=args.dados,
        filtros=obter_filtros(args),
        return_info=True,
    )
    return {
        "custos": custos,
        "oferta": oferta,
        "demanda": demanda,
        "origens": origens,
        "destinos": destinos,
        "custo_real": custo_real,
        "info": info,
        "alpha": alpha,
        "cds": cds,
    }


def imprimir_cenario(cenario: dict) -> None:
    info = cenario["info"]
    filtros = info["filtros"]
    titulo("1/3  MATRIZ DE TRANSPORTE (Matheus)")

    if filtros:
        partes = []
        if filtros.get("data_inicio"):
            partes.append(f"de {filtros['data_inicio']}")
        if filtros.get("data_fim"):
            partes.append(f"até {filtros['data_fim']}")
        if filtros.get("categorias"):
            partes.append("categoria(s): " + ", ".join(filtros["categorias"]))
        print(f"Filtros aplicados:     {' e '.join(partes)}")
    else:
        print("Filtros aplicados:     nenhum (base completa)")

    print(f"Pedidos entregues:     {numero(info['itens'])} itens "
          f"({info['data_min'][:10]} a {info['data_max'][:10]})")
    print(f"Origens x destinos:    {info['n_origens']} UFs x {info['n_destinos']} UFs "
          f"= {numero(info['rotas_possiveis'])} rotas")
    print(f"Rotas com histórico:   {numero(info['rotas_com_historico_no_recorte'])} "
          f"(restantes estimadas pela base completa: "
          f"{numero(info['rotas_estimadas_pela_base_completa'])})")
    print(f"Centros de distribuição: {', '.join(cenario['cds'])} "
          f"(válidos na matriz: {', '.join(info['cds']) or 'nenhum'})")
    print(f"Desconto de consolidação (alpha) no trecho até o CD: {decimal(cenario['alpha'])} "
          f"— com 1,0 esse trecho custa o frete cheio; quanto menor, mais barato fica "
          f"passar pelo CD")
    print(f"Frete médio real:      {moeda(info['custo_medio_item'])} por item")
    print(f"Custo real da Olist:   {moeda(cenario['custo_real'])} (frete efetivamente pago)")
    print(f"Custo total oferta/demanda: {numero(sum(cenario['oferta']))} = "
          f"{numero(sum(cenario['demanda']))} (problema balanceado)")
    if info["rotas_sem_caminho"]:
        print(f"ATENÇÃO: {info['rotas_sem_caminho']} rotas ficaram sem caminho possível.")


# ---------------------------------------------------------------------------
# Etapa 2 + validação: confere as restrições do modelo na solução do Vogel
# ---------------------------------------------------------------------------
def validar_solucao(cenario: dict, alocacao: np.ndarray, custo_total: float) -> list:
    """Testa, uma a uma, as restrições do modelo matemático do README."""
    oferta = np.asarray(cenario["oferta"], dtype=float)
    demanda = np.asarray(cenario["demanda"], dtype=float)
    custos = np.asarray(cenario["custos"], dtype=float)
    alocacao = np.asarray(alocacao, dtype=float)
    checks = []

    def adicionar(restricao, ok, detalhe):
        checks.append({"restricao": restricao, "ok": bool(ok), "detalhe": detalhe})

    adicionar("Equilíbrio: soma oferta = soma demanda",
              np.isclose(oferta.sum(), demanda.sum()),
              f"{numero(oferta.sum())} = {numero(demanda.sum())} itens")

    adicionar("Oferta de cada origem escoada (Σj x_ij = o_i)",
              np.allclose(alocacao.sum(axis=1), oferta),
              f"{len(oferta)} origens conferidas")

    adicionar("Demanda de cada destino atendida (Σi x_ij = d_j)",
              np.allclose(alocacao.sum(axis=0), demanda),
              f"{len(demanda)} destinos conferidos")

    adicionar("Domínio: x_ij inteiro e não negativo",
              bool(alocacao.min() >= 0 and np.allclose(alocacao, np.round(alocacao))),
              "itens indivisíveis (Z>=0)")

    adicionar("Custo total coerente (Σ c_ij · x_ij)",
              np.isclose(custo_total, float((custos * alocacao).sum())),
              moeda(custo_total))

    itens_penalidade = float(alocacao[custos >= PENALIDADE].sum())
    adicionar("Nenhum item em rota inexistente",
              itens_penalidade == 0,
              f"{numero(itens_penalidade)} itens em rotas sem caminho")

    return checks


def imprimir_validacao(checks: list) -> None:
    titulo("VALIDAÇÃO DAS RESTRIÇÕES DO MODELO")
    for c in checks:
        marca = "OK  " if c["ok"] else "FALHA"
        print(f"[{marca}] {c['restricao']:<52} {c['detalhe']}")
    if all(c["ok"] for c in checks):
        print("\n-> Solução factível: todas as restrições do modelo foram respeitadas.")
    else:
        print("\n-> Solução com restrição violada: revise os dados ou os parâmetros.")


# ---------------------------------------------------------------------------
# Artefatos da entrega: alocação em CSV, resumo em JSON e relatório em Markdown
# ---------------------------------------------------------------------------
def tabela_rotas(cenario: dict, alocacao: np.ndarray, top_n: int = 10):
    """Lista as rotas usadas pelo Vogel, da maior para a menor, com custo e participação."""
    custos = np.asarray(cenario["custos"], dtype=float)
    total = float(alocacao.sum())
    linhas = []
    for i, origem in enumerate(cenario["origens"]):
        for j, destino in enumerate(cenario["destinos"]):
            qtd = float(alocacao[i][j])
            if qtd > 0:
                linhas.append({
                    "origem": origem,
                    "destino": destino,
                    "itens": int(round(qtd)),
                    "custo_unitario": round(float(custos[i][j]), 2),
                    "custo_total": round(qtd * float(custos[i][j]), 2),
                    "participacao_pct": round(qtd / total * 100, 2) if total else 0.0,
                })
    tabela = pd.DataFrame(linhas).sort_values("itens", ascending=False).reset_index(drop=True)
    return tabela, tabela.head(top_n)


def imprimir_top_rotas(top: pd.DataFrame) -> None:
    titulo(f"ROTAS MAIS CARREGADAS PELO VOGEL (top {len(top)})")
    print(f"{'origem':>7} {'destino':>8} {'itens':>10} {'R$/item':>10} {'custo total':>16} {'% volume':>9}")
    for _, r in top.iterrows():
        print(f"{r['origem']:>7} {r['destino']:>8} {numero(r['itens']):>10} "
              f"{moeda(r['custo_unitario']):>10} {moeda(r['custo_total']):>16} "
              f"{percentual(r['participacao_pct']):>9}")


def salvar_json(caminho: str, cenario: dict, resumo: dict, checks: list, tempos: dict) -> None:
    """Grava os números principais em JSON, para reusar em slides/planilha."""
    conteudo = {
        "parametros": {
            "alpha": cenario["alpha"],
            "cds": cenario["cds"],
            "filtros": cenario["info"]["filtros"],
            "itens": cenario["info"]["itens"],
            "origens": cenario["origens"],
            "destinos": cenario["destinos"],
        },
        "resultado": {chave: round(float(valor), 2) for chave, valor in resumo.items()},
        "validacao": checks,
        "tempos_segundos": {etapa: round(t, 3) for etapa, t in tempos.items()},
    }
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)


def escrever_relatorio(caminho: str, cenario: dict, resumo: dict, checks: list,
                      top: pd.DataFrame, tempos: dict, sensibilidade) -> None:
    """Relatório curto em Markdown: cenário, números, validação, rotas e leitura."""
    info = cenario["info"]
    filtros = info["filtros"]
    linhas = ["# Ship4You — Relatório da execução", ""]
    linhas.append("Gerado automaticamente por `main.py` (integração: Arthur).")
    linhas.append("")

    # 1. Cenário
    linhas += ["## 1. Cenário executado", ""]
    linhas.append(f"- Filtros: {filtros if filtros else 'nenhum (base completa)'}")
    linhas.append(f"- Itens entregues: {numero(info['itens'])} "
                  f"({info['data_min'][:10]} a {info['data_max'][:10]})")
    linhas.append(f"- Matriz de custo: {info['n_origens']} origens x {info['n_destinos']} destinos "
                  f"({numero(info['rotas_possiveis'])} rotas)")
    linhas.append(f"- Rotas com histórico no recorte: {numero(info['rotas_com_historico_no_recorte'])}; "
                  f"estimadas pela base completa: {numero(info['rotas_estimadas_pela_base_completa'])}")
    linhas.append(f"- Centros de distribuição: {', '.join(cenario['cds'])}; "
                  f"alpha (desconto de consolidação): {decimal(cenario['alpha'])}")
    linhas.append("")

    # 2. Resultado
    linhas += ["## 2. Resultado (frete real x alocação do Vogel)", ""]
    linhas.append("| Indicador | Valor |")
    linhas.append("|---|---|")
    linhas.append(f"| Frete real pago na Olist | {moeda(resumo['custo_real'])} |")
    linhas.append(f"| Custo da alocação do Vogel | {moeda(resumo['custo_vogel'])} |")
    linhas.append(f"| Economia | {moeda(resumo['economia_reais'])} ({percentual(resumo['economia_pct'])}) |")
    linhas.append(f"| Frete médio real | {moeda(resumo['custo_medio_real'])} por item |")
    linhas.append(f"| Frete médio Vogel | {moeda(resumo['custo_medio_vogel'])} por item |")
    linhas.append("")

    # 3. Validação
    linhas += ["## 3. Validação das restrições do modelo", ""]
    linhas.append("| Restrição | Situação | Detalhe |")
    linhas.append("|---|---|---|")
    for c in checks:
        linhas.append(f"| {c['restricao']} | {'OK' if c['ok'] else 'FALHA'} | {c['detalhe']} |")
    linhas.append("")

    # 4. Rotas
    linhas += [f"## 4. Rotas mais carregadas (top {len(top)})", ""]
    linhas.append("| Origem | Destino | Itens | R$/item | Custo total | % do volume |")
    linhas.append("|---|---|---|---|---|---|")
    for _, r in top.iterrows():
        linhas.append(f"| {r['origem']} | {r['destino']} | {numero(r['itens'])} | "
                      f"{moeda(r['custo_unitario'])} | {moeda(r['custo_total'])} | "
                      f"{percentual(r['participacao_pct'])} |")
    linhas.append("")

    # 5. Sensibilidade
    if sensibilidade is not None and len(sensibilidade):
        linhas += ["## 5. Sensibilidade ao desconto de consolidação (alpha)", ""]
        linhas.append("| alpha | Custo Vogel | Economia | Economia % |")
        linhas.append("|---|---|---|---|")
        for _, r in sensibilidade.iterrows():
            linhas.append(f"| {decimal(r['alpha'])} | {moeda(r['custo_vogel'])} | "
                          f"{moeda(r['economia_reais'])} | {percentual(r['economia_pct'])} |")
        linhas.append("")

    # 6. Leitura do resultado (o que fazer com o número)
    linhas += ["## 6. Leitura do resultado", ""]
    linhas.append(
        f"A alocação do Vogel atende exatamente a mesma oferta e a mesma demanda da operação "
        f"real ({numero(resumo['itens'])} itens) e reduz o frete médio de "
        f"{moeda(resumo['custo_medio_real'])} para {moeda(resumo['custo_medio_vogel'])} por item, "
        f"uma economia de {moeda(resumo['economia_reais'])} ({percentual(resumo['economia_pct'])})."
    )
    if len(top):
        primeira = top.iloc[0]
        linhas.append(
            f"\nA rota {primeira['origem']} -> {primeira['destino']} concentra "
            f"{percentual(primeira['participacao_pct'])} do volume: ganho de custo, mas exige "
            "capacidade e contrato de frete nessa rota para a economia se sustentar."
        )
    linhas.append(
        "\nO Vogel é uma heurística: a solução é factível e respeita todas as restrições, "
        "mas não é prova de otimalidade — o valor serve como limite prático de comparação "
        "com o frete efetivamente pago."
    )
    linhas.append("")
    linhas.append("## 7. Tempo de execução")
    linhas.append("")
    linhas.append("| Etapa | Tempo (s) |")
    linhas.append("|---|---|")
    for etapa, t in tempos.items():
        linhas.append(f"| {etapa} | {t:.3f} |")
    linhas.append("")

    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(linhas))


# ---------------------------------------------------------------------------
# Análise de sensibilidade ao alpha
# ---------------------------------------------------------------------------
def executar_sensibilidade(args, alphas=None) -> pd.DataFrame:
    """Roda o pipeline para vários alpha e mede quanto a economia depende do desconto."""
    alphas = sorted(alphas or ALPHAS_PADRAO)
    titulo("ANÁLISE DE SENSIBILIDADE — desconto de consolidação (alpha)")
    print("O alpha é o desconto de consolidação no trecho até o CD: com alpha = 1,0 esse "
          "trecho custa o frete cheio; quanto menor o alpha, mais barato fica mandar o "
          "pedido até o CD.\n")

    linhas = []
    for a in alphas:
        cenario = construir_cenario(args, alpha=a)
        _, custo_total = resolver_vogel(cenario["custos"], cenario["oferta"], cenario["demanda"])
        economia = cenario["custo_real"] - custo_total
        linhas.append({
            "alpha": a,
            "custo_vogel": round(custo_total, 2),
            "economia_reais": round(economia, 2),
            "economia_pct": round(economia / cenario["custo_real"] * 100, 2),
        })
        print(f"  alpha={decimal(a):<5} custo Vogel = {moeda(custo_total):>18} "
              f"| economia = {percentual(linhas[-1]['economia_pct']):>8}")

    tabela = pd.DataFrame(linhas)
    print("\nLeitura: se o resultado quase não muda quando alpha varia, a economia vem da "
          "realocação entre rotas e não do desconto hipotético do CD. Pequenas oscilações "
          "para cima e para baixo aparecem porque o Vogel é heurístico (escolha gulosa), "
          "não porque o custo da rota piorou.")
    return tabela


def grafico_sensibilidade(tabela: pd.DataFrame, custo_real: float, pasta: str) -> str:
    """Curva custo x alpha, com a linha do frete real pago como referência."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(tabela["alpha"], tabela["custo_vogel"], marker="o", color="#27ae60",
            label="Custo com Vogel")
    ax.axhline(custo_real, linestyle="--", color="#c0392b", label="Frete real pago (Olist)")
    for _, r in tabela.iterrows():
        ax.annotate(f"{r['economia_pct']:.1f}%", (r["alpha"], r["custo_vogel"]),
                    textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xlabel("alpha (desconto de consolidação no trecho até o CD)")
    ax.set_ylabel("Custo total de frete (R$)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"R$ {v:,.0f}".replace(",", ".")))
    ax.set_title("Sensibilidade da economia ao desconto do centro de distribuição")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    caminho = os.path.join(pasta, "sensibilidade_alpha.png")
    fig.savefig(caminho, dpi=150)
    plt.close(fig)
    return caminho


# ---------------------------------------------------------------------------
# Ajuda: listar categorias e período da base
# ---------------------------------------------------------------------------
def listar_categorias(args) -> None:
    """Mostra as categorias da base e o período disponível, para escolher o filtro."""
    df = carregar_dados_base(args.dados)
    datas = pd.to_datetime(df["order_purchase_timestamp"])
    titulo("BASE DISPONÍVEL")
    print(f"Itens entregues: {numero(len(df))} | período: {datas.min().date()} a {datas.max().date()}")
    print(f"Estados vendedores: {df['seller_state'].nunique()} | "
          f"estados compradores: {df['customer_state'].nunique()}")
    contagem = df["product_category_name"].value_counts()
    print(f"\nCategorias ({contagem.size}) — itens por categoria:")
    for nome, qtd in contagem.head(25).items():
        print(f"  {str(nome):<32} {numero(qtd):>8}")
    if contagem.size > 25:
        print(f"  ... e mais {contagem.size - 25} categorias")
    print("\nExemplo: python3 main.py --categoria " + str(contagem.index[0]))


# ---------------------------------------------------------------------------
# Sumário executivo
# ---------------------------------------------------------------------------
def imprimir_sumario_executivo(resumo: dict, tempos: dict) -> None:
    titulo("SUMÁRIO EXECUTIVO")
    print(f"Frete real pago pela Olist:   {moeda(resumo['custo_real'])}")
    print(f"Custo da alocação do Vogel:   {moeda(resumo['custo_vogel'])}")
    print(f"Economia:                     {moeda(resumo['economia_reais'])} "
          f"({percentual(resumo['economia_pct'])})")
    print(f"Frete médio por item:         {moeda(resumo['custo_medio_real'])} -> "
          f"{moeda(resumo['custo_medio_vogel'])}")
    print("\nDecisão prática: manter a oferta e a demanda atuais e priorizar as rotas de "
          "menor frete médio já reduz o custo total na ordem acima.")
    print("Como o centro de distribuição entra na conta: para cada rota o modelo compara "
          "duas opções — mandar o pedido direto do estado vendedor para o estado comprador, "
          "ou mandar primeiro até um CD (pagando esse trecho com o desconto de consolidação) "
          "e dali até o comprador. Fica sempre com a mais barata das duas; então o CD só é "
          "usado quando a soma dos dois trechos sai mais em conta que o envio direto.")
    print("\nTempo de execução (s): " +
          " | ".join(f"{etapa} {t:.2f}" for etapa, t in tempos.items()))


# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    args = criar_parser().parse_args(argv)

    if args.exemplo:
        from analise_resultados import executar_exemplo

        titulo("EXEMPLO — matriz pequena (não precisa dos CSVs)")
        executar_exemplo()
        print("\n-> Exemplo executado em graficos_exemplo/. Serve para testar a instalação.")
        return 0

    if args.listar_categorias:
        listar_categorias(args)
        return 0

    print("Ship4You — otimização de frete com o Método de Vogel")
    print(f"Python {sys.version.split()[0]} | base: {args.dados} | saída: {args.saida}")
    tempos = {}

    # 1) Matriz de transporte (Matheus)
    t = time.perf_counter()
    try:
        cenario = construir_cenario(args)
    except ValueError as erro:
        print(f"\nErro nos filtros: {erro}")
        return 1
    tempos["matriz"] = time.perf_counter() - t
    imprimir_cenario(cenario)

    # 2) Método de Vogel (Becca)
    titulo("2/3  MÉTODO DE VOGEL (Becca)")
    t = time.perf_counter()
    alocacao, custo_total = resolver_vogel(cenario["custos"], cenario["oferta"], cenario["demanda"])
    tempos["vogel"] = time.perf_counter() - t
    print(f"Rotas usadas: {int((alocacao > 0).sum())} de {alocacao.size} células da matriz")
    print(f"Custo mínimo encontrado pelo Vogel: {moeda(custo_total)}")

    # Validação das restrições do modelo
    checks = validar_solucao(cenario, alocacao, custo_total)
    imprimir_validacao(checks)

    # 3) Análise e gráficos (Bender)
    titulo("3/3  ANÁLISE E GRÁFICOS (Bender)")
    os.makedirs(args.saida, exist_ok=True)
    pasta_graficos = os.path.join(args.saida, "graficos")
    t = time.perf_counter()
    if args.sem_graficos:
        resumo = montar_resumo(cenario["custo_real"], custo_total, cenario["custos"], alocacao)
        imprimir_resumo(resumo)
        print("(--sem-graficos: figuras não geradas nesta execução)")
    else:
        resumo = analisar_resultados(
            cenario["custos"], alocacao, custo_total,
            origens=cenario["origens"], destinos=cenario["destinos"],
            custo_real=cenario["custo_real"], pasta_saida=pasta_graficos,
            mostrar=args.mostrar,
        )
    tempos["analise"] = time.perf_counter() - t

    # Rotas mais carregadas
    tabela, top = tabela_rotas(cenario, alocacao, top_n=args.top)
    imprimir_top_rotas(top)

    # Sensibilidade opcional
    sensibilidade = None
    if args.sensibilidade is not None:
        sensibilidade = executar_sensibilidade(args, args.sensibilidade)
        os.makedirs(pasta_graficos, exist_ok=True)
        caminho = grafico_sensibilidade(sensibilidade, resumo["custo_real"], pasta_graficos)
        sensibilidade.to_csv(os.path.join(args.saida, "sensibilidade_alpha.csv"), index=False)
        print(f"\nCurva de sensibilidade salva em: {caminho}")

    # Artefatos da entrega
    caminho_alocacao = os.path.join(args.saida, "alocacao.csv")
    tabela.to_csv(caminho_alocacao, index=False)
    salvar_json(os.path.join(args.saida, "resumo.json"), cenario, resumo, checks, tempos)
    escrever_relatorio(os.path.join(args.saida, "relatorio.md"), cenario, resumo,
                       checks, top, tempos, sensibilidade)

    imprimir_sumario_executivo(resumo, tempos)
    titulo("ARQUIVOS GERADOS")
    print(f"Alocação completa:  {caminho_alocacao}")
    print(f"Resumo numérico:    {os.path.join(args.saida, 'resumo.json')}")
    print(f"Relatório:          {os.path.join(args.saida, 'relatorio.md')}")
    if not args.sem_graficos:
        print(f"Gráficos:           {pasta_graficos}/")
    print("\n-> Pipeline concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
