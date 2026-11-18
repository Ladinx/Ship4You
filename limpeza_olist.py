"""
Limpeza e tratamento do dataset Olist Brazilian E-commerce (Kaggle).
Lê os CSVs brutos em data/ e grava versões tratadas em data/clean/,
além de uma tabela analítica consolidada (data/clean/olist_analitico.csv).
"""
import pandas as pd
import numpy as np

RAW = "data"
OUT = "data/clean"
import os
os.makedirs(OUT, exist_ok=True)

def read(name):
    return pd.read_csv(f"{RAW}/{name}")

def save(df, name):
    df.to_csv(f"{OUT}/{name}", index=False)
    print(f"  -> {name}: {df.shape[0]} linhas, {df.shape[1]} colunas")

report = []

# ---------------------------------------------------------------- orders
orders = read("olist_orders_dataset.csv")
date_cols = ["order_purchase_timestamp", "order_approved_at",
             "order_delivered_carrier_date", "order_delivered_customer_date",
             "order_estimated_delivery_date"]
for c in date_cols:
    orders[c] = pd.to_datetime(orders[c], errors="coerce")

# Nulos em datas de entrega são informativos (pedido não entregue) -> mantidos como NaT
orders["is_delivered"] = orders.order_status.eq("delivered")

# Features de tempo (só fazem sentido para pedidos entregues)
orders["delivery_time_days"] = (
    orders.order_delivered_customer_date - orders.order_purchase_timestamp
).dt.total_seconds() / 86400
orders["delay_days"] = (
    orders.order_delivered_customer_date - orders.order_estimated_delivery_date
).dt.total_seconds() / 86400
orders["delay_days"] = orders.delay_days.clip(lower=0)  # adiantado = 0
orders["purchase_year_month"] = orders.order_purchase_timestamp.dt.to_period("M").astype(str)

# Remove pedidos impossíveis: entrega registrada antes da compra
bad = orders.order_delivered_customer_date < orders.order_purchase_timestamp
report.append(f"orders: {bad.sum()} pedidos com data de entrega anterior à compra removidos")
orders = orders[~bad]
save(orders, "orders_clean.csv")

# ---------------------------------------------------------------- customers / sellers
customers = read("olist_customers_dataset.csv")
sellers = read("olist_sellers_dataset.csv")
for df, col in [(customers, "customer_zip_code_prefix"), (sellers, "seller_zip_code_prefix")]:
    df[col] = df[col].astype(str).str.zfill(5)  # recupera zeros à esquerda
    df["city"] = df.filter(regex="city$").iloc[:, 0].str.strip().str.lower()
save(customers, "customers_clean.csv")
save(sellers, "sellers_clean.csv")

# ---------------------------------------------------------------- geolocation
geo = read("olist_geolocation_dataset.csv")
n0 = len(geo)
geo = geo.drop_duplicates()                                  # 261.831 duplicatas exatas
bbox = (-34.0, 5.5, -74.5, -32.0)                            # lat/lng aproximados do Brasil
geo = geo[geo.geolocation_lat.between(bbox[0], bbox[1]) &
          geo.geolocation_lng.between(bbox[2], bbox[3])]
geo["geolocation_city"] = geo.geolocation_city.str.strip().str.lower()
report.append(f"geolocation: {n0} -> {len(geo)} linhas (duplicatas + coords fora do Brasil removidas)")

# Consolida para 1 linha por prefixo de CEP (média das coords, cidade/estado mais frequentes)
geo_agg = (geo.groupby("geolocation_zip_code_prefix")
              .agg(lat=("geolocation_lat", "mean"),
                   lng=("geolocation_lng", "mean"),
                   city=("geolocation_city", lambda s: s.mode().iat[0]),
                   state=("geolocation_state", lambda s: s.mode().iat[0]))
              .reset_index()
              .rename(columns={"geolocation_zip_code_prefix": "zip_prefix"}))
geo_agg["zip_prefix"] = geo_agg.zip_prefix.astype(str).str.zfill(5)
save(geo_agg, "geolocation_clean.csv")

# ---------------------------------------------------------------- order_items
items = read("olist_order_items_dataset.csv")
items["shipping_limit_date"] = pd.to_datetime(items.shipping_limit_date, errors="coerce")
items["total_item_value"] = items.price + items.freight_value
save(items, "order_items_clean.csv")

# ---------------------------------------------------------------- order_payments
payments = read("olist_order_payments_dataset.csv")
n_notdef = payments.payment_type.eq("not_defined").sum()
payments = payments[payments.payment_type != "not_defined"]  # 3 linhas sem tipo definido
# voucher com valor 0 é legítimo; valores negativos não existem (verificado)
report.append(f"payments: {n_notdef} linhas com payment_type='not_defined' removidas")
save(payments, "order_payments_clean.csv")

# ---------------------------------------------------------------- reviews
reviews = read("olist_order_reviews_dataset.csv")
n0 = len(reviews)
reviews = reviews.sort_values("review_answer_timestamp").drop_duplicates("review_id", keep="last")
report.append(f"reviews: {n0} -> {len(reviews)} (review_id duplicado: mantida a resposta mais recente)")
for c in ["review_comment_title", "review_comment_message"]:
    reviews[c] = reviews[c].str.strip()
reviews["has_comment"] = reviews.review_comment_message.notna()
reviews["review_creation_date"] = pd.to_datetime(reviews.review_creation_date, errors="coerce")
reviews["review_answer_timestamp"] = pd.to_datetime(reviews.review_answer_timestamp, errors="coerce")
save(reviews, "order_reviews_clean.csv")

# ---------------------------------------------------------------- products
products = read("olist_products_dataset.csv")
products["product_category_name"] = products.product_category_name.fillna("outros")
products["product_weight_g"] = products.product_weight_g.replace(0, np.nan)
num_cols = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm",
            "product_name_lenght", "product_description_lenght", "product_photos_qty"]
products[num_cols] = products[num_cols].fillna(products[num_cols].median())
report.append("products: categoria nula -> 'outros'; peso 0g e numéricos nulos -> mediana")
save(products, "products_clean.csv")

# ---------------------------------------------------------------- translation
translation = read("product_category_name_translation.csv")
save(translation, "category_translation_clean.csv")

# ---------------------------------------------------------------- tabela analítica consolidada
# 1 linha = 1 pedido
pay_agg = (payments.groupby("order_id")
             .agg(payment_value_total=("payment_value", "sum"),
                  payment_types=("payment_type", lambda s: ",".join(sorted(set(s)))),
                  max_installments=("payment_installments", "max"))
             .reset_index())
rev_agg = reviews.groupby("order_id").review_score.mean().rename("avg_review_score").reset_index()
item_agg = (items.groupby("order_id")
              .agg(n_items=("order_item_id", "count"),
                   total_price=("price", "sum"),
                   total_freight=("freight_value", "sum"),
                   n_sellers=("seller_id", "nunique"))
              .reset_index())

df = (orders
      .merge(customers, on="customer_id", how="left")
      .merge(item_agg, on="order_id", how="left")
      .merge(pay_agg, on="order_id", how="left")
      .merge(rev_agg, on="order_id", how="left")
      .merge(products, on="product_id", how="left") if False else None)

# product_id está no nível de item; agrega categoria principal do pedido
cat = (items.merge(products[["product_id", "product_category_name"]], on="product_id")
            .merge(translation, on="product_category_name", how="left")
            .groupby("order_id")
            .agg(main_category=("product_category_name_english", lambda s: s.mode().iat[0]
                                if s.notna().any() else "outros"))
            .reset_index())

df = (orders
      .merge(customers, on="customer_id", how="left")
      .merge(item_agg, on="order_id", how="left")
      .merge(pay_agg, on="order_id", how="left")
      .merge(rev_agg, on="order_id", how="left")
      .merge(cat, on="order_id", how="left"))
df = df.merge(geo_agg.add_prefix("cust_"), left_on="customer_zip_code_prefix",
              right_on="cust_zip_prefix", how="left").drop(columns="cust_zip_prefix")
save(df, "olist_analitico.csv")

# ---------------------------------------------------------------- relatório
print("\n===== RELATÓRIO DE LIMPEZA =====")
for r in report:
    print("-", r)
print(f"\nTabela analítica: {df.shape[0]} pedidos, {df.shape[1]} colunas")
print("Nulos restantes por coluna (top 10):")
print(df.isna().sum().sort_values(ascending=False).head(10).to_string())
