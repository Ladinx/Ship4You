"""
vogel.py — Método de Vogel com o passo a passo das iterações.

Responsável: Becca (método de Vogel).

Funções principais:
    resolver_vogel(custos, oferta, demanda)          -> (alocacao, custo_total)
    resolver_vogel_detalhado(custos, oferta, demanda)-> (alocacao, custo_total, historico)
    imprimir_iteracoes(historico, ...)               -> imprime o passo a passo

Como o método decide (o mesmo raciocínio do vídeo):
 1. Para cada linha ativa, penalidade = segundo menor custo - menor custo; o
    mesmo para cada coluna ativa. A penalidade mede quanto custa NÃO usar a
    rota mais barata daquela linha/coluna.
 2. Escolhe a maior penalidade (em empate fica a primeira da lista: linhas
    antes das colunas). Se ela veio de uma linha, a alocação vai na coluna de
    menor custo dessa linha; se veio de uma coluna, vai na linha de menor custo
    dessa coluna.
 3. Aloca o máximo possível (mínimo entre oferta e demanda). Quem zerou
    (linha e/ou coluna) sai do problema.
 4. Repete até acabar oferta e demanda.
 Quando sobra uma única linha ou coluna ativa, a penalidade é o próprio custo,
 porque não existe segundo menor.

Uso direto (não precisa dos CSVs):
    python3 vogel.py                 # base completa, resultado final (como antes)
    python3 vogel.py --iteracoes     # base completa + o passo a passo
    python3 vogel.py --exemplo       # recorte 3x3 do vídeo, com todas as iterações
"""
import argparse

import numpy as np

from matriz_transporte import gerar_matriz_transporte


# ---------------------------------------------------------------------------
# Formatação no padrão brasileiro
# ---------------------------------------------------------------------------
def _num(valor: float, casas: int = 0) -> str:
    """1969 -> '1.969';  18.47 -> '18,47'"""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _moeda(valor: float, casas: int = 2) -> str:
    """R$ 26,38"""
    return "R$ " + _num(valor, casas)


def _pct(valor: float) -> str:
    """7,72%"""
    return f"{valor:.2f}".replace(".", ",") + "%"


def _qtd(valor: float) -> str:
    """Quantidade de itens, sem casas decimais quando é inteira."""
    inteiro = round(float(valor))
    if abs(float(valor) - inteiro) < 1e-9:
        return _num(inteiro)
    return _num(valor, 2)


# ---------------------------------------------------------------------------
# Método de Vogel
# ---------------------------------------------------------------------------
def resolver_vogel_detalhado(custos, oferta, demanda,
                             rotulos_linhas=None, rotulos_colunas=None):
    """
    Resolve o problema de transporte pelo Método de Vogel e devolve também o
    histórico de cada iteração (usado para mostrar o passo a passo).

    Retorno: (alocacao, custo_total, historico)
      alocacao : np.ndarray (n_linhas x n_colunas), quantidades por célula
      historico: lista de dicts, um por iteração (ver chaves em _registrar)
    """
    custos = np.array(custos, dtype=float)
    oferta = list(oferta)
    demanda = list(demanda)

    n_linhas = len(oferta)
    n_colunas = len(demanda)

    rotulos_linhas = list(rotulos_linhas) if rotulos_linhas else [f"L{i + 1}" for i in range(n_linhas)]
    rotulos_colunas = list(rotulos_colunas) if rotulos_colunas else [f"C{j + 1}" for j in range(n_colunas)]

    alocacao = np.zeros((n_linhas, n_colunas))
    linhas_ativas = [True] * n_linhas
    colunas_ativas = [True] * n_colunas
    historico = []

    while sum(oferta) > 0 and sum(demanda) > 0:
        # --- etapa 1: penalidades de cada linha e de cada coluna ativa -------
        penalidades_linhas = []
        penalidades_colunas = []

        for i in range(n_linhas):
            if linhas_ativas[i] and oferta[i] > 0:
                custos_linha = sorted([custos[i][j] for j in range(n_colunas) if colunas_ativas[j]])
                if len(custos_linha) >= 2:
                    penalidades_linhas.append(
                        (custos_linha[1] - custos_linha[0], 'L', i, custos_linha[0],
                         custos_linha[1], rotulos_linhas[i])
                    )
                elif len(custos_linha) == 1:
                    # sem segundo menor: a penalidade é o próprio custo
                    penalidades_linhas.append(
                        (custos_linha[0], 'L', i, custos_linha[0], None, rotulos_linhas[i])
                    )
            elif linhas_ativas[i]:
                linhas_ativas[i] = False

        for j in range(n_colunas):
            if colunas_ativas[j] and demanda[j] > 0:
                custos_coluna = sorted([custos[i][j] for i in range(n_linhas) if linhas_ativas[i]])
                if len(custos_coluna) >= 2:
                    penalidades_colunas.append(
                        (custos_coluna[1] - custos_coluna[0], 'C', j, custos_coluna[0],
                         custos_coluna[1], rotulos_colunas[j])
                    )
                elif len(custos_coluna) == 1:
                    penalidades_colunas.append(
                        (custos_coluna[0], 'C', j, custos_coluna[0], None, rotulos_colunas[j])
                    )
            elif colunas_ativas[j]:
                colunas_ativas[j] = False

        # --- etapa 2: maior penalidade decide quem recebe a alocação ---------
        todas_penalidades = penalidades_linhas + penalidades_colunas
        if not todas_penalidades:
            break

        # max() fica com o primeiro em caso de empate -> linhas antes das colunas
        vencedora = max(todas_penalidades, key=lambda p: p[0])
        _, tipo, index = vencedora[0], vencedora[1], vencedora[2]

        if tipo == 'L':
            linha = index
            colunas_validas = [j for j in range(n_colunas) if colunas_ativas[j]]
            coluna = min(colunas_validas, key=lambda j: custos[linha][j])
        else:
            coluna = index
            linhas_validas = [i for i in range(n_linhas) if linhas_ativas[i]]
            linha = min(linhas_validas, key=lambda i: custos[i][coluna])

        # --- etapa 3: aloca o mínimo entre oferta e demanda ------------------
        oferta_antes = float(oferta[linha])
        demanda_antes = float(demanda[coluna])
        quantidade = min(oferta_antes, demanda_antes)
        alocacao[linha][coluna] += quantidade

        oferta[linha] -= quantidade
        demanda[coluna] -= quantidade

        sai_linha = oferta[linha] == 0
        sai_coluna = demanda[coluna] == 0
        if sai_linha:
            linhas_ativas[linha] = False
        if sai_coluna:
            colunas_ativas[coluna] = False

        historico.append({
            "iteracao": len(historico) + 1,
            "penalidades_linhas": penalidades_linhas,
            "penalidades_colunas": penalidades_colunas,
            "vencedora": vencedora,
            "rotulo_origem": rotulos_linhas[linha],
            "rotulo_destino": rotulos_colunas[coluna],
            "linha": linha,
            "coluna": coluna,
            "custo_unitario": float(custos[linha][coluna]),
            "quantidade": float(quantidade),
            "oferta_antes": oferta_antes,
            "oferta_depois": float(oferta[linha]),
            "demanda_antes": demanda_antes,
            "demanda_depois": float(demanda[coluna]),
            "sai_linha": sai_linha,
            "sai_coluna": sai_coluna,
            "linhas_restantes": [rotulos_linhas[i] for i in range(n_linhas) if linhas_ativas[i]],
            "colunas_restantes": [rotulos_colunas[j] for j in range(n_colunas) if colunas_ativas[j]],
        })

    custo_total = float(np.sum(alocacao * custos))
    return alocacao, custo_total, historico


def resolver_vogel(custos, oferta, demanda, verboso=False,
                   rotulos_linhas=None, rotulos_colunas=None, limite_iteracoes=None):
    """
    Interface usada pelo main.py — mesmo retorno de antes: (alocacao, custo_total).

    verboso=True imprime o passo a passo de cada iteração (opcional, não muda a
    solução). limite_iteracoes corta a impressão (útil na base completa, que tem
    dezenas de iterações).
    """
    alocacao, custo_total, historico = resolver_vogel_detalhado(
        custos, oferta, demanda, rotulos_linhas, rotulos_colunas
    )
    if verboso:
        imprimir_iteracoes(historico, limite=limite_iteracoes)
    return alocacao, custo_total


# ---------------------------------------------------------------------------
# Impressão do passo a passo
# ---------------------------------------------------------------------------
LARGURA = 76            # largura dos separadores
MAX_PENALIDADES = 5     # penalidades mostradas por linha (as maiores)
MAX_LIVRE = 8           # até esse tamanho a lista aparece inteira


def _campo(rotulo: str, texto: str) -> str:
    """Alinha o rótulo do bloco de decisão:  '  Decisão      coluna RR ...'"""
    return f"  {rotulo:<13} {texto}"


def _penalidades_por_linha(penalidades, vencedora) -> str:
    """
    Penalidades de um lado (linhas ou colunas), da maior para a menor:
        'RR 11,99 *   TO 11,28   RN 9,89   RJ 7,48   PB 6,55   (+22)'
    O '*' marca a que ganhou a iteração.
    """
    if not penalidades:
        return "(nenhuma)"

    ordenadas = sorted(penalidades, key=lambda p: p[0], reverse=True)
    mostrar = ordenadas if len(ordenadas) <= MAX_LIVRE else ordenadas[:MAX_PENALIDADES]

    partes = []
    for valor, tipo, indice, _, _, rotulo in mostrar:
        marca = "*" if (tipo, indice) == (vencedora[1], vencedora[2]) else " "
        partes.append(f"{rotulo} {_num(valor, 2).rjust(5)}{marca}")

    resto = len(ordenadas) - len(mostrar)
    linha = "  ".join(partes).rstrip()
    if resto > 0:
        linha += f"   (+{resto})"
    return linha


def imprimir_iteracoes(historico, limite=None):
    """
    Imprime o passo a passo do Vogel, iteração por iteração.

    limite: quantas iterações mostrar em detalhe (None ou 0 = todas).
            As restantes saem numa tabela-resumo compacta.
    """
    if not historico:
        print("Nenhuma iteração executada (oferta ou demanda já era zero).")
        return

    total = len(historico)
    mostrar = total if limite in (None, 0) else min(int(limite), total)

    for h in historico[:mostrar]:
        valor_pen, tipo, indice, custo_min, custo_seg = h["vencedora"][:5]
        candidatas = len(h["penalidades_linhas"]) + len(h["penalidades_colunas"])

        print()
        cabeca = f"ITERAÇÃO {h['iteracao']}/{total}"
        print(cabeca + f"{candidatas:>5} candidatas".rjust(LARGURA - len(cabeca)))
        print("-" * LARGURA)

        print(_campo("Penalidades", "linha   " + _penalidades_por_linha(h["penalidades_linhas"], h["vencedora"])))
        print(_campo("", "coluna  " + _penalidades_por_linha(h["penalidades_colunas"], h["vencedora"])))
        print()

        if tipo == 'L':
            print(_campo("Maior", f"linha {h['rotulo_origem']} — R$ {_num(valor_pen, 2)}"))
            print(_campo("", "aloca na coluna de menor custo dessa linha"))
        else:
            print(_campo("Maior", f"coluna {h['rotulo_destino']} — R$ {_num(valor_pen, 2)}"))
            print(_campo("", "aloca na linha de menor custo dessa coluna"))

        if custo_seg is None:
            print(_campo("", f"não há segundo menor custo: a penalidade é o próprio custo "
                             f"({_moeda(custo_min)})"))
        else:
            print(_campo("", f"não usar a rota mais barata custa {_moeda(valor_pen)} a mais por item "
                             f"({_moeda(custo_min)} -> {_moeda(custo_seg)})"))

        print(_campo("Alocação", f"{h['rotulo_origem']} -> {h['rotulo_destino']}  "
                                  f"{_moeda(h['custo_unitario'])}/item  =  "
                                  f"{_qtd(h['quantidade'])} itens "
                                  f"(min(oferta {_qtd(h['oferta_antes'])}, "
                                  f"demanda {_qtd(h['demanda_antes'])}))"))

        saidas = []
        if h["sai_coluna"]:
            saidas.append(f"coluna {h['rotulo_destino']} sai")
        if h["sai_linha"]:
            saidas.append(f"linha {h['rotulo_origem']} sai")
        print(_campo("Saldo",
                     f"{h['rotulo_origem']}: {_qtd(h['oferta_antes'])} -> {_qtd(h['oferta_depois'])}   "
                     f"{h['rotulo_destino']}: {_qtd(h['demanda_antes'])} -> {_qtd(h['demanda_depois'])}"
                     + (f"   => {'; '.join(saidas)}" if saidas else "")))

        restam_l = h["linhas_restantes"]
        restam_c = h["colunas_restantes"]
        if len(restam_l) + len(restam_c) <= MAX_LIVRE:
            print(_campo("Restam", f"linhas {', '.join(restam_l) or '-'} | "
                                   f"colunas {', '.join(restam_c) or '-'}"))
        else:
            print(_campo("Restam", f"{len(restam_l)} linhas, {len(restam_c)} colunas"))

    if mostrar < total:
        print()
        imprimir_resumo_iteracoes(historico[mostrar:], de=mostrar + 1, ate=total,
                                 nota=f"(iterações {mostrar + 1} a {total}; use --max-iteracoes 0 "
                                      f"para ver todas em detalhe)")


def imprimir_resumo_iteracoes(historico, de=None, ate=None, nota=None):
    """Tabela compacta: uma linha por iteração, com a rota e o que saiu."""
    if not historico:
        return
    total = len(historico)
    titulo = f"RESUMO DAS ITERAÇÕES ({de or 1} a {ate or total})"
    print(titulo)
    if nota:
        print(nota)
    print(f"{'it':>4}  {'vencedor':<18}{'penalidade':>12}   {'rota':<12}{'itens':>9}   sai")
    print("-" * LARGURA)
    for h in historico:
        valor_pen, tipo, indice = h["vencedora"][:3]
        vencedor = ("coluna " if tipo == 'C' else "linha ") + (
            h["rotulo_destino"] if tipo == 'C' else h["rotulo_origem"])
        sai = "linha+coluna" if (h["sai_linha"] and h["sai_coluna"]) else (
            "linha" if h["sai_linha"] else ("coluna" if h["sai_coluna"] else "-"))
        print(f"{h['iteracao']:>4}  {vencedor:<18}{_moeda(valor_pen):>12}   "
              f"{h['rotulo_origem'] + ' -> ' + h['rotulo_destino']:<12}{_qtd(h['quantidade']):>9}   {sai}")
    print("-" * LARGURA)


def imprimir_alocacao(alocacao, custos, rotulos_linhas, rotulos_colunas, titulo="ALOCAÇÃO FINAL"):
    """Tabela origem x destino com as quantidades, mais a conferência de custo por rota."""
    alocacao = np.asarray(alocacao, dtype=float)
    custos = np.asarray(custos, dtype=float)

    celulas = [[_qtd(alocacao[i][j]) if alocacao[i][j] > 0 else "-"
                for j in range(len(rotulos_colunas))] for i in range(len(rotulos_linhas))]
    largura_rot = max(len(r) for r in list(rotulos_linhas) + ["demanda"]) + 2
    largura_col = max([9] + [len(c) for linha in celulas for c in linha]
                      + [len(d) for d in rotulos_colunas] + [len("demanda")])

    print()
    print(titulo)
    print(" " * largura_rot + "".join(f"{d:>{largura_col}}" for d in rotulos_colunas)
          + f"   {'oferta':>{largura_col}}")
    print("-" * (largura_rot + (largura_col + 3) * (len(rotulos_colunas) + 1)))
    for i, origem in enumerate(rotulos_linhas):
        print(f"{origem:<{largura_rot}}" + "".join(f"{c:>{largura_col}}" for c in celulas[i])
              + f"   {_qtd(alocacao[i].sum()):>{largura_col}}")
    print("-" * (largura_rot + (largura_col + 3) * (len(rotulos_colunas) + 1)))
    print(f"{'demanda':<{largura_rot}}" + "".join(f"{_qtd(alocacao[:, j].sum()):>{largura_col}}"
                                                  for j in range(len(rotulos_colunas)))
          + f"   {_qtd(alocacao.sum()):>{largura_col}}")

    print()
    print("Custo por rota usada")
    print(f"  {'rota':<10}{'itens':>10}   {'R$/item':>10}   {'custo':>16}")
    print("-" * LARGURA)
    for i, origem in enumerate(rotulos_linhas):
        for j, destino in enumerate(rotulos_colunas):
            if alocacao[i][j] > 0:
                print(f"  {origem + ' -> ' + destino:<10}{_qtd(alocacao[i][j]):>10}   "
                      f"{_moeda(custos[i][j]):>10}   {_moeda(alocacao[i][j] * custos[i][j]):>16}")
    print("-" * LARGURA)
    print(f"  {'TOTAL':<10}{_qtd(alocacao.sum()):>10}   {'':>10}   {_moeda(float((alocacao * custos).sum())):>16}")


# ---------------------------------------------------------------------------
# Recorte do vídeo (3 origens x 3 destinos, 4.131 itens)
# ---------------------------------------------------------------------------
EXEMPLO_VIDEO = {
    "rotulos_linhas": ["MG", "PR", "RS"],
    "rotulos_colunas": ["RJ", "BA", "SC"],
    "custos": [
        [24.59, 26.38, 29.22],   # MG
        [22.42, 44.85, 20.46],   # PR
        [28.28, 50.99, 20.48],   # RS
    ],
    "oferta": [1969, 1721, 441],
    "demanda": [2653, 625, 853],
}


def _rodar_exemplo_video():
    """Reproduz, com o código, o recorte feito à mão no vídeo."""
    e = EXEMPLO_VIDEO
    print("=" * 78)
    print("RECORTE DO VÍDEO — MG/PR/RS -> RJ/BA/SC")
    print("=" * 78)
    print(f"Oferta:  {', '.join(f'{r}={_qtd(o)}' for r, o in zip(e['rotulos_linhas'], e['oferta']))}"
          f"  (total {_qtd(sum(e['oferta']))})")
    print(f"Demanda: {', '.join(f'{r}={_qtd(d)}' for r, d in zip(e['rotulos_colunas'], e['demanda']))}"
          f"  (total {_qtd(sum(e['demanda']))})")
    print("Custo por item:")
    for r, linha in zip(e["rotulos_linhas"], e["custos"]):
        print(f"  {r}: " + "  ".join(f"{d} {_moeda(c)}" for d, c in zip(e["rotulos_colunas"], linha)))

    alocacao, custo_total, historico = resolver_vogel_detalhado(
        e["custos"], e["oferta"], e["demanda"],
        rotulos_linhas=e["rotulos_linhas"], rotulos_colunas=e["rotulos_colunas"],
    )
    imprimir_iteracoes(historico)
    imprimir_alocacao(alocacao, e["custos"], e["rotulos_linhas"], e["rotulos_colunas"])
    print()
    print(f"Custo total do recorte: {_moeda(custo_total)}  "
          f"({len(historico)} iterações)")
    return alocacao, custo_total


def _rodar_base_completa(mostrar_iteracoes: bool, limite: int = 0):
    """Executa o Vogel sobre a base real da Olist (mesmo que o main.py usa)."""
    custos, oferta, demanda, origens, destinos, custo_real_historico = gerar_matriz_transporte()

    alocacao, custo_total, historico = resolver_vogel_detalhado(
        custos, oferta, demanda, rotulos_linhas=origens, rotulos_colunas=destinos
    )

    if mostrar_iteracoes:
        print("=" * 78)
        print(f"PASSO A PASSO — base completa ({len(origens)} origens x {len(destinos)} destinos)")
        print("=" * 78)
        imprimir_iteracoes(historico, limite=limite or None)
        print()

    print("=" * 78)
    print("RESULTADO — base completa")
    print("=" * 78)
    print(f"Iterações executadas:          {len(historico)}")
    print(f"Rotas usadas:                  {int((alocacao > 0).sum())} de {alocacao.size} células")
    print(f"Custo histórico real (Olist):  {_moeda(custo_real_historico)}")
    print(f"Custo otimizado pelo Vogel:    {_moeda(custo_total)}")

    economia = custo_real_historico - custo_total
    print(f"Economia gerada:               {_moeda(economia)} "
          f"({_pct(economia / custo_real_historico * 100)})")
    return alocacao, custo_total, historico


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Método de Vogel — resultado final e/ou passo a passo das iterações",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--iteracoes", action="store_true",
                   help="mostra o passo a passo das iterações na base completa")
    p.add_argument("--max-iteracoes", type=int, default=6,
                   help="quantas iterações imprimir na base completa (0 = todas; padrão: 6)")
    p.add_argument("--exemplo", action="store_true",
                   help="roda o recorte 3x3 do vídeo com todas as iterações")
    args = p.parse_args(argv)

    if args.exemplo:
        _rodar_exemplo_video()
        return 0

    _rodar_base_completa(args.iteracoes, args.max_iteracoes)
    if not args.iteracoes:
        print("\nDica: python3 vogel.py --iteracoes  (passo a passo) | "
              "python3 vogel.py --exemplo  (recorte do vídeo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
