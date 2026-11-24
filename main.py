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
    python3 main.py                  # abre o menu e as perguntas (só apertar Enter)
    python3 main.py --sem-perguntas  # roda o cenário padrão sem perguntar nada
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np
import pandas as pd

# Cores no terminal: colorama habilita ANSI no console do Windows (cmd/PowerShell).
# Em Linux/macOS é no-op. Sem a biblioteca, o programa continua funcionando sem cor.
try:
    import colorama

    colorama.just_fix_windows_console()
except ImportError:  # pragma: no cover - depende do ambiente
    colorama = None

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


def _cor_ativa() -> bool:
    """
    Cor ligada quando a saída é um terminal de verdade.
    Convenções respeitadas: NO_COLOR desliga sempre (https://no-color.org).
    No Windows sem colorama, desliga para não imprimir lixo na tela.
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if colorama is None and os.name == "nt":
        return False
    return sys.stdout.isatty()


COR_ATIVA = _cor_ativa()


def _cor(texto: str, codigo: str) -> str:
    """Aplica cor quando o terminal suporta (para não sujar log/arquivo)."""
    if not COR_ATIVA:
        return texto
    return f"\033[{codigo}m{texto}\033[0m"


def _destacar(texto: str) -> str:
    """Títulos das perguntas em negrito/ciano."""
    return _cor(texto, "1;36")


def titulo(texto: str) -> None:
    print()
    print("=" * 72)
    print(_cor(texto, "1;36"))
    print("=" * 72)

# ---------------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------------
def criar_parser() -> argparse.ArgumentParser:
    """
    O programa é guiado por perguntas: basta rodar `python3 main.py` e apertar Enter.
    O único argumento existe para rodar sem ninguém na frente do teclado.
    """
    p = argparse.ArgumentParser(
        description="Ship4You — Matriz de transporte -> Vogel -> Gráficos (modo interativo)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--sem-perguntas", action="store_true",
                   help="roda o cenário padrão direto, sem as perguntas (para gerar o resultado automaticamente)")
    return p


def preencher_padroes(args) -> None:
    """Valores padrão do cenário — os mesmos oferecidos como sugestão nas perguntas."""
    args.alpha = 0.7
    args.cds = ",".join(CDS_PADRAO)
    args.data_inicio = None
    args.data_fim = None
    args.categoria = None
    args.dados = "dataset-tratado"
    args.saida = "resultados"
    args.sem_graficos = False
    args.mostrar = False
    args.sensibilidade = None
    args.top = 10


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
        marca = _cor("OK  ", "1;32") if c["ok"] else _cor("FALHA", "1;31")
        print(f"[{marca}] {c['restricao']:<52} {c['detalhe']}")
    if all(c["ok"] for c in checks):
        print()
        print(_cor("-> Solução factível: todas as restrições do modelo foram respeitadas.", "32"))
    else:
        print()
        print(_cor("-> Solução com restrição violada: revise os dados ou os parâmetros.", "31"))


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
        economia_txt = _cor(f"{percentual(linhas[-1]['economia_pct']):>8}", "1;32")
        print(f"  alpha={decimal(a):<5} custo Vogel = {moeda(custo_total):>18} "
              f"| economia = {economia_txt}")

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
    print("\nNo modo interativo, escolha a opção 2 e digite o número (ou o nome) da categoria, "
          "por exemplo: " + str(contagem.index[0]))


# ---------------------------------------------------------------------------
# Sumário executivo
# ---------------------------------------------------------------------------
def imprimir_sumario_executivo(resumo: dict, tempos: dict) -> None:
    titulo("SUMÁRIO EXECUTIVO")
    print(f"Frete real pago pela Olist:   {moeda(resumo['custo_real'])}")
    print(f"Custo da alocação do Vogel:   {moeda(resumo['custo_vogel'])}")
    economia = _cor(f"{moeda(resumo['economia_reais'])} ({percentual(resumo['economia_pct'])})", "1;32")
    print(f"Economia:                     {economia}")
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
# Modo interativo: perguntas guiadas para quem só quer rodar e ver o resultado
# ---------------------------------------------------------------------------
def _perguntar(texto: str, padrao: str = "") -> str:
    """Faz a pergunta e devolve a resposta; Enter aceita o padrão."""
    sufixo = f" [{padrao}]" if padrao else ""
    try:
        resposta = input(f"{texto}{sufixo}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  (sem resposta — seguindo com o padrão)")
        return padrao
    return resposta or padrao


def _confirmar(texto: str, padrao_sim: bool = True) -> bool:
    """Pergunta sim/não; Enter aceita o padrão."""
    padrao = "S" if padrao_sim else "N"
    while True:
        resposta = _perguntar(texto, padrao).lower()
        if resposta in ("s", "sim", "y", "yes"):
            return True
        if resposta in ("n", "nao", "não", "no"):
            return False
        print("  responda com s ou n")


def modo_interativo(args) -> argparse.Namespace:
    """Pergunta passo a passo o que rodar, em vez de exigir argumentos decorados."""
    titulo("MODO INTERATIVO — aperte Enter para aceitar o padrão")
    print("Dica: para rodar sem nenhuma pergunta, use: python3 main.py --sem-perguntas\n")

    # 1) Recorte da base (filtros)
    print(_destacar("1) Recorte da base"))
    print("   [1] base completa       [2] por categoria de produto")
    print("   [3] por período         [4] categoria + período")
    recorte = _perguntar("   opção", "1")

    # 1.1) Categoria
    if recorte in ("2", "4"):
        print()
        contagem = carregar_dados_base(args.dados)["product_category_name"].value_counts()
        top = contagem.head(10)
        print("   Categorias mais frequentes:")
        for i, (nome, qtd) in enumerate(top.items(), 1):
            print(f"   [{i:>2}] {str(nome):<30} {numero(qtd):>8} itens")
        resposta = _perguntar("   número(s) ou nome, separados por vírgula", "1")
        nomes = []
        for parte in resposta.split(","):
            parte = parte.strip()
            if parte.isdigit() and 1 <= int(parte) <= len(top):
                nomes.append(str(top.index[int(parte) - 1]))
            elif parte:
                nomes.append(parte)
        args.categoria = ",".join(nomes)

    # 1.2) Período
    if recorte in ("3", "4"):
        print()
        print("   Período das compras (a base vai de 2016-09 a 2018-08):")
        args.data_inicio = _perguntar("   data inicial (AAAA-MM-DD, Enter = sem limite)") or None
        args.data_fim = _perguntar("   data final (AAAA-MM-DD, Enter = sem limite)") or None

    # 2) alpha
    print()
    print(_destacar("2) Desconto de consolidação no trecho até o CD (alpha)"))
    print("   1,00 = esse trecho custa o frete cheio | 0,70 = padrão do trabalho | menor = mais barato passar pelo CD")
    alpha = _perguntar("   alpha", decimal(args.alpha))
    try:
        args.alpha = float(alpha.replace(",", "."))
    except ValueError:
        print(f"   valor inválido — mantendo {decimal(args.alpha)}")

    # 3) CDs
    print()
    print(_destacar(f"3) Centros de distribuição candidatos: {args.cds}"))
    if not _confirmar("   manter esses?", padrao_sim=True):
        args.cds = _perguntar("   UFs separadas por vírgula", args.cds)

    # 4) Saídas
    print()
    print(_destacar("4) Resultados"))
    args.sem_graficos = not _confirmar("   gerar os gráficos?", padrao_sim=True)
    args.mostrar = (not args.sem_graficos) and _confirmar("   abrir as janelas na tela?", padrao_sim=False)
    if _confirmar("   rodar a análise de sensibilidade do alpha?", padrao_sim=False):
        args.sensibilidade = []  # lista vazia = usa os alphas padrão

    # 5) Confirmação
    print()
    print(_destacar("Resumo da execução"))
    print(f"   recorte:      {args.categoria or 'todas as categorias'} | "
          f"{args.data_inicio or 'início da base'} até {args.data_fim or 'fim da base'}")
    print(f"   alpha:        {decimal(args.alpha)} | CDs: {args.cds}")
    print(f"   resultados:   {'gráficos' if not args.sem_graficos else 'sem gráficos'}"
          f"{' + sensibilidade' if args.sensibilidade is not None else ''}")
    if not _confirmar("Rodar agora?", padrao_sim=True):
        raise SystemExit("Execução cancelada.")
    print()
    return args


# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------
def menu_inicial() -> str:
    """Primeira pergunta: o que a pessoa quer fazer."""
    titulo("Ship4You — otimização de frete com o Método de Vogel")
    print("O que você quer fazer?\n")
    print("  [1] Rodar a otimização (matriz -> Vogel -> gráficos)   <- padrão")
    print("  [2] Rodar o exemplo pequeno (teste rápido, sem os dados)")
    print("  [3] Ver as categorias de produto e o período da base")
    return _perguntar("opção", "1")


def executar_pipeline(args) -> int:
    """Pipeline completo: matriz (Matheus) -> Vogel (Becca) -> análise (Bender)."""
    print(_cor("Ship4You — otimização de frete com o Método de Vogel", "1"))
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
    escrever_relatorio(os.path.join(args.saida, "relatorio.md"), cenario, resumo,
                       checks, top, tempos, sensibilidade)

    imprimir_sumario_executivo(resumo, tempos)
    titulo("ARQUIVOS GERADOS")
    print(f"Alocação completa:  {caminho_alocacao}")
    print(f"Relatório:          {os.path.join(args.saida, 'relatorio.md')}")
    if not args.sem_graficos:
        print(f"Gráficos:           {pasta_graficos}/")
    print("\n-> Pipeline concluído.")
    return 0


def main(argv=None) -> int:
    """Ponto de entrada: menu, perguntas e execução."""
    args = criar_parser().parse_args(argv)
    preencher_padroes(args)

    if args.sem_perguntas:
        return executar_pipeline(args)

    escolha = menu_inicial()
    if escolha == "2":
        from analise_resultados import executar_exemplo

        titulo("EXEMPLO — matriz pequena (não precisa dos CSVs)")
        executar_exemplo()
        print("\n-> Exemplo executado em graficos_exemplo/. Serve para testar a instalação.")
        return 0
    if escolha == "3":
        listar_categorias(args)
        return 0

    args = modo_interativo(args)
    return executar_pipeline(args)


if __name__ == "__main__":
    raise SystemExit(main())
