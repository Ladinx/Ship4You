"""
matriz_transporte.py — Modelagem de dados e matriz de transporte.

Responsável: Matheus (agrupamento por UF, oferta, demanda e matriz de custo).
Entrega: uma função que devolve 'custos', 'oferta' e 'demanda' prontos para o Vogel.

Ajustes de integração (Arthur, main.py):
- carregar_dados_base passou a trazer também a data da compra e a categoria do
  produto, que são os filtros pedidos na tarefa de integração;
- aplicar_filtros() isola a regra de filtragem em um único lugar;
- gerar_matriz_transporte(..., filtros=...) aceita um recorte de período/categoria
  e, quando uma rota não tem pedidos dentro do recorte, usa o frete médio
  histórico dessa rota na base completa como estimativa (em vez de penalidade);
- gerar_matriz_transporte(..., return_info=True) devolve um dicionário de
  diagnóstico para o relatório do main.py (sem quebrar quem já usa a função).
"""
import os
import numpy as np
import pandas as pd


# Colunas que a modelagem usa (as demais são apoio para os filtros)
COLUNAS_MODELO = ["order_id", "seller_state", "customer_state", "price", "freight_value"]


def carregar_dados_base(pasta_dados: str = "dataset-tratado") -> pd.DataFrame:
    """
    Carrega e cruza os CSVs tratados seguindo a regra definida em custo_rotas.py.

    Uma linha = um item entregue, com a UF de origem (seller_state), a UF de
    destino (customer_state), o preço, o frete, a data da compra e a categoria
    do produto (usados pelos filtros do main.py).
    """
    # Garante compatibilidade caso a pasta seja 'dataset-tratado' ou 'data/clean'
    if not os.path.exists(pasta_dados) and os.path.exists("data/clean"):
        pasta_dados = "data/clean"

    items = pd.read_csv(
        os.path.join(pasta_dados, "order_items_clean.csv"),
        usecols=["order_id", "product_id", "seller_id", "price", "freight_value"],
    )
    orders = pd.read_csv(
        os.path.join(pasta_dados, "orders_clean.csv"),
        usecols=["order_id", "order_status", "customer_id",
                 "order_purchase_timestamp", "purchase_year_month"],
    )
    sellers = pd.read_csv(
        os.path.join(pasta_dados, "sellers_clean.csv"),
        usecols=["seller_id", "seller_state"],
    )
    customers = pd.read_csv(
        os.path.join(pasta_dados, "customers_clean.csv"),
        usecols=["customer_id", "customer_state"],
    )
    produtos = pd.read_csv(
        os.path.join(pasta_dados, "products_clean.csv"),
        usecols=["product_id", "product_category_name"],
    )

    df = (
        items.merge(orders.query("order_status == 'delivered'"), on="order_id")
        .merge(sellers, on="seller_id")
        .merge(customers, on="customer_id")
        .merge(produtos, on="product_id", how="left")
    )
    return df[COLUNAS_MODELO + ["order_purchase_timestamp", "product_category_name"]]


def aplicar_filtros(
    df: pd.DataFrame,
    data_inicio: str = None,
    data_fim: str = None,
    categorias: list = None,
) -> pd.DataFrame:
    """
    Aplica os filtros simples do main.py sobre a base cruzada.

    data_inicio / data_fim: intervalo (inclusivo) da data da compra, ex.: '2018-01-01'
    categorias: lista de nomes de product_category_name, ex.: ['cama_mesa_banho']

    Levanta ValueError se o recorte ficar vazio, para o erro aparecer no terminal
    em vez de gerar uma matriz sem linhas.
    """
    filtrado = df
    descricao = []

    if data_inicio is not None:
        datas = pd.to_datetime(filtrado["order_purchase_timestamp"])
        filtrado = filtrado[datas >= pd.to_datetime(data_inicio)]
        descricao.append(f"de {data_inicio}")
    if data_fim is not None:
        datas = pd.to_datetime(filtrado["order_purchase_timestamp"])
        filtrado = filtrado[datas <= pd.to_datetime(data_fim)]
        descricao.append(f"até {data_fim}")

    if categorias:
        if isinstance(categorias, str):
            categorias = [c.strip() for c in categorias.split(",") if c.strip()]
        filtrado = filtrado[filtrado["product_category_name"].isin(categorias)]
        descricao.append(f"categoria(s) {', '.join(categorias)}")

    if filtrado.empty:
        raise ValueError(
            "Os filtros aplicados não deixaram nenhum item entregue "
            f"({' e '.join(descricao) or 'sem filtros'}). "
            "Use --listar-categorias para conferir os nomes e as datas disponíveis."
        )
    return filtrado.copy()


def _matriz_custo_direto(df: pd.DataFrame, origens: list, destinos: list) -> pd.DataFrame:
    """Custo direto c_ij = frete médio por item de cada par (origem, destino)."""
    return df.pivot_table(
        index="seller_state",
        columns="customer_state",
        values="freight_value",
        aggfunc="mean",
    ).reindex(index=origens, columns=destinos)


def _aplicar_centros_distribuicao(
    matriz_direta: pd.DataFrame,
    cds_candidatos: list,
    alpha: float,
    penalidade_inexistente: float,
):
    """
    Aplica a regra dos CDs do README:  c'_ij = min( c_ij , min_h [ alpha*c_ih + c_hj ] )

    O envio direto continua valendo; o CD só entra quando sai mais barato.
    alpha é o desconto de consolidação no trecho até o CD (alpha = 1 -> sem desconto).
    """
    origens = list(matriz_direta.index)
    destinos = list(matriz_direta.columns)

    # Só usa como CD a UF que aparece na matriz como origem e como destino
    cds_validos = [h for h in cds_candidatos if h in origens and h in destinos]

    matriz_efetiva = matriz_direta.copy()
    for i in origens:
        for j in destinos:
            custo_direto = matriz_direta.loc[i, j]
            melhor_custo = custo_direto if pd.notna(custo_direto) else np.inf

            # Testa passar por cada CD candidato h
            for h in cds_validos:
                c_ih = matriz_direta.loc[i, h]
                c_hj = matriz_direta.loc[h, j]
                if pd.notna(c_ih) and pd.notna(c_hj):
                    custo_via_cd = (alpha * c_ih) + c_hj
                    if custo_via_cd < melhor_custo:
                        melhor_custo = custo_via_cd

            # Se ainda assim não houver caminho (nem direto nem via CD), aplica penalidade alta
            if np.isinf(melhor_custo):
                melhor_custo = penalidade_inexistente

            matriz_efetiva.loc[i, j] = melhor_custo

    return matriz_efetiva, cds_validos


def gerar_matriz_transporte(
    cds_candidatos: list = None,
    alpha: float = 0.7,
    pasta_dados: str = "dataset-tratado",
    penalidade_inexistente: float = 99999.0,
    filtros: dict = None,
    return_info: bool = False,
):
    """
    Constrói as entradas padronizadas para o Método de Vogel:
    - custos (np.ndarray 2D): matriz c'_ij considerando envio direto ou via Centros de Distribuição (CDs)
    - oferta (list): itens enviados por cada seller_state
    - demanda (list): itens recebidos por cada customer_state
    - origens (list): lista das UFs de origem
    - destinos (list): lista das UFs de destino
    - custo_real_historico (float): soma real dos fretes pagos na base para comparação posterior

    filtros: dict aceito por aplicar_filtros (data_inicio, data_fim, categorias).
             Quando há filtro, as rotas sem pedidos no recorte herdam o frete médio
             histórico da mesma rota na base completa (estimativa), para não jogar
             itens em rotas de penalidade.
    return_info: se True, devolve também um dict de diagnóstico (7º elemento).
    """
    if cds_candidatos is None:
        # Exemplos de grandes hubs logísticos como CDs iniciais (podem ser alterados nos testes)
        cds_candidatos = ["SP", "MG", "PR", "PE", "GO"]

    filtros = filtros or {}

    df_base = carregar_dados_base(pasta_dados)
    df = aplicar_filtros(df_base, **filtros)
    custo_real_historico = float(df["freight_value"].sum())

    origens = sorted(df["seller_state"].unique().tolist())
    destinos = sorted(df["customer_state"].unique().tolist())

    # 1. Oferta (o_i) e Demanda (d_j)
    oferta = df.groupby("seller_state").size().reindex(origens).astype(int).tolist()
    demanda = df.groupby("customer_state").size().reindex(destinos).astype(int).tolist()

    # 2. Matriz de custo direto (c_ij) do recorte filtrado
    matriz_recorte = _matriz_custo_direto(df, origens, destinos)

    # Rotas que existem na base completa servem de estimativa para as que ficaram
    # sem pedido dentro do filtro (combine_first mantém o valor do recorte quando existe).
    estados = sorted(set(df_base["seller_state"]) | set(df_base["customer_state"]))
    matriz_completa = _matriz_custo_direto(df_base, estados, estados)
    matriz_direta = matriz_recorte.combine_first(matriz_completa).reindex(
        index=estados, columns=estados
    )

    # 3. Matriz efetiva (c'_ij) aplicando a regra dos Centros de Distribuição do README:
    # c'_ij = min( c_ij , min_h [ alpha * c_ih + c_hj ] )
    matriz_efetiva, cds_validos = _aplicar_centros_distribuicao(
        matriz_direta, cds_candidatos, alpha, penalidade_inexistente
    )

    custos = matriz_efetiva.loc[origens, destinos].to_numpy(dtype=float)

    # 4. Garantia de balanceamento (Sum(Oferta) == Sum(Demanda))
    total_oferta = sum(oferta)
    total_demanda = sum(demanda)

    if total_oferta > total_demanda:
        demanda.append(total_oferta - total_demanda)
        destinos.append("DUMMY")
        custos = np.hstack((custos, np.zeros((custos.shape[0], 1), dtype=float)))
    elif total_demanda > total_oferta:
        oferta.append(total_demanda - total_oferta)
        origens.append("DUMMY")
        custos = np.vstack((custos, np.zeros((1, custos.shape[1]), dtype=float)))

    if not return_info:
        return custos, oferta, demanda, origens, destinos, custo_real_historico

    # Diagnóstico para o relatório do main.py
    sem_historico = int(matriz_recorte.isna().to_numpy().sum())
    info = {
        "filtros": filtros,
        "alpha": alpha,
        "cds": cds_validos,
        "itens": int(len(df)),
        "n_origens": len(origens),
        "n_destinos": len(destinos),
        "rotas_possiveis": len(origens) * len(destinos),
        "rotas_com_historico_no_recorte": int(matriz_recorte.notna().to_numpy().sum()),
        "rotas_estimadas_pela_base_completa": sem_historico,
        "rotas_sem_caminho": int((custos >= penalidade_inexistente).sum()),
        "custo_medio_item": custo_real_historico / float(len(df)),
        "data_min": str(pd.to_datetime(df["order_purchase_timestamp"]).min()),
        "data_max": str(pd.to_datetime(df["order_purchase_timestamp"]).max()),
    }
    return custos, oferta, demanda, origens, destinos, custo_real_historico, info


if __name__ == "__main__":
    # Teste local da entrega
    custos, oferta, demanda, origens, destinos, custo_real = gerar_matriz_transporte(
        cds_candidatos=["SP", "MG", "PR", "PE", "GO"],
        alpha=0.7,
    )

    print(f"Origens ({len(origens)}): {origens}")
    print(f"Destinos ({len(destinos)}): {destinos}")
    print(f"Oferta total: {sum(oferta)} | Demanda total: {sum(demanda)}")
    print(f"Dimensão da matriz de custos: {custos.shape}")
    print(f"Custo total real histórico (Olist): R$ {custo_real:,.2f}")
    print(f"Rotas ainda sem caminho após CDs: {np.sum(custos >= 99999.0)}")