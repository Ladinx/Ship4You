import pandas as pd

items = pd.read_csv("data/clean/order_items_clean.csv",
                    usecols=["order_id", "seller_id", "price", "freight_value"])
orders = pd.read_csv("data/clean/orders_clean.csv", usecols=["order_id", "order_status", "customer_id"])
sellers = pd.read_csv("data/clean/sellers_clean.csv", usecols=["seller_id", "seller_state"])
customers = pd.read_csv("data/clean/customers_clean.csv", usecols=["customer_id", "customer_state"])

df = (items.merge(orders.query("order_status == 'delivered'"), on="order_id")
           .merge(sellers, on="seller_id")
           .merge(customers, on="customer_id")
           [["order_id", "seller_state", "customer_state", "price", "freight_value"]])

print("1) Total de itens entregues:", len(df))
print("2) Estados distintos - vendedores:", df.seller_state.nunique(),
      "| compradores:", df.customer_state.nunique())
print(f"3) Frete médio por item: R$ {df.freight_value.mean():.2f}")
pct = df.freight_value.sum() / df.price.sum() * 100
print(f"4) Frete total / valor produtos: {pct:.2f}%")

print("\n5) Oferta (itens por seller_state):")
print(df.seller_state.value_counts().to_string())

print("\n6) Demanda (itens por customer_state):")
print(df.customer_state.value_counts().to_string())

matriz = df.pivot_table(index="seller_state", columns="customer_state",
                        values="freight_value", aggfunc="mean")
print("\n7) Matriz de custo (frete médio R$/item):")
print(matriz.round(2).to_string())

total_rotas = df.seller_state.nunique() * df.customer_state.nunique()
sem_pedidos = total_rotas - matriz.notna().sum().sum()
print(f"\n8) Rotas sem pedidos: {sem_pedidos} de {total_rotas} possíveis")
