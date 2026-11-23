import os
import numpy as np
import pandas as pd


def carregar_dados_base(pasta_dados: str = "dataset-tratado") -> pd.DataFrame:
    """
    Carrega e cruza os CSVs tratados seguindo a regra definida em custo_rotas.py.
    """
    # Garante compatibilidade caso a pasta seja 'dataset-tratado' ou 'data/clean'
    if not os.path.exists(pasta_dados) and os.path.exists("data/clean"):
        pasta_dados = "data/clean"

    items = pd.read_csv(
        os.path.join(pasta_dados, "order_items_clean.csv"),
        usecols=["order_id", "seller_id", "price", "freight_value"],
    )
    orders = pd.read_csv(
        os.path.join(pasta_dados, "orders_clean.csv"),
        usecols=["order_id", "order_status", "customer_id"],
    )
    sellers = pd.read_csv(
        os.path.join(pasta_dados, "sellers_clean.csv"),
        usecols=["seller_id", "seller_state"],
    )
    customers = pd.read_csv(
        os.path.join(pasta_dados, "customers_clean.csv"),
        usecols=["customer_id", "customer_state"],
    )

    df = (
        items.merge(orders.query("order_status == 'delivered'"), on="order_id")
        .merge(sellers, on="seller_id")
        .merge(customers, on="customer_id")[
            ["order_id", "seller_state", "customer_state", "price", "freight_value"]
        ]
    )
    return df


def gerar_matriz_transporte(
    cds_candidatos: list = None,
    alpha: float = 0.7,
    pasta_dados: str = "dataset-tratado",
    penalidade_inexistente: float = 99999.0,
):
    """
    Constrói as entradas padronizadas para o Método de Vogel:
    - custos (np.ndarray 2D): matriz c'_ij considerando envio direto ou via Centros de Distribuição (CDs)
    - oferta (list): itens enviados por cada seller_state
    - demanda (list): itens recebidos por cada customer_state
    - origens (list): lista das UFs de origem
    - destinos (list): lista das UFs de destino
    - custo_real_historico (float): soma real dos fretes pagos na base para comparação posterior
    """
    if cds_candidatos is None:
        # Exemplos de grandes hubs logísticos como CDs iniciais (podem ser alterados nos testes)
        cds_candidatos = ["SP", "MG", "PR", "PE", "GO"]

    df = carregar_dados_base(pasta_dados)
    custo_real_historico = float(df["freight_value"].sum())

    origens = sorted(df["seller_state"].unique().tolist())
    destinos = sorted(df["customer_state"].unique().tolist())

    # 1. Oferta (o_i) e Demanda (d_j)
    oferta = df.groupby("seller_state").size().reindex(origens).astype(int).tolist()
    demanda = df.groupby("customer_state").size().reindex(destinos).astype(int).tolist()

    # 2. Matriz de custo direto (c_ij): média de freight_value por par (seller_state, customer_state)
    matriz_direta = df.pivot_table(
        index="seller_state",
        columns="customer_state",
        values="freight_value",
        aggfunc="mean",
    ).reindex(index=origens, columns=destinos)

    # 3. Matriz efetiva (c'_ij) aplicando a regra dos Centros de Distribuição do README:
    # c'_ij = min( c_ij , min_h [ alpha * c_ih + c_hj ] )
    matriz_efetiva = matriz_direta.copy()

    # Filtra apenas CDs que existem tanto como origem quanto como destino na matriz
    cds_validos = [h for h in cds_candidatos if h in origens and h in destinos]

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

    custos = matriz_efetiva.to_numpy(dtype=float)

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

    return custos, oferta, demanda, origens, destinos, custo_real_historico


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