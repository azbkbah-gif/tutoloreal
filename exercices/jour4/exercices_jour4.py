import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()
PROJET = os.environ["GCP_PROJECT"]
DATASET = f"{PROJET}.thelook_fictif"

client = bigquery.Client(project=PROJET)
print("Connecté au projet :", client.project)


sql = f"""
SELECT status, COUNT(*) AS nb
FROM `{DATASET}.orders`
GROUP BY status
ORDER BY nb DESC
"""

job = client.query(sql)
for ligne in job.result():
    print(f"{ligne['status']:<12} {ligne['nb']:>6}")
print("Octets lus :", job.total_bytes_processed)


df = client.query(sql).to_dataframe()
print(df)
df["part"] = (df["nb"] / df["nb"].sum() * 100).round(1)
print(df)


sql_cat = f"""
SELECT p.category,
       COUNT(DISTINCT oi.order_id) AS nb_commandes,
       ROUND(SUM(oi.sale_price), 2) AS ca
FROM `{DATASET}.order_items` oi
JOIN `{DATASET}.products` p ON p.id = oi.product_id
WHERE DATE(oi.created_at) >= @date_debut
  AND oi.status = @statut
GROUP BY p.category
ORDER BY ca DESC
"""

config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("date_debut", "DATE", "2025-01-01"),
        bigquery.ScalarQueryParameter("statut", "STRING", "Complete"),
    ],
    maximum_bytes_billed=10**9,      # garde-fou : 1 Go maximum
)

df_cat = client.query(sql_cat, job_config=config).to_dataframe()
print(df_cat)

# config = bigquery.QueryJobConfig(
#     query_parameters=[
#         bigquery.ScalarQueryParameter("date_debut", "DATE", "2025-01-01"),
#         bigquery.ScalarQueryParameter("statut", "STRING", "Returned"),
#     ],
#     maximum_bytes_billed=10**9,      # garde-fou : 1 Go maximum
# )

# df_cat = client.query(sql_cat, job_config=config).to_dataframe()
# print(df_cat)

config_dry = bigquery.QueryJobConfig(
    dry_run=True,
    use_query_cache=False,
    query_parameters=config.query_parameters,
)
job_dry = client.query(sql_cat, job_config=config_dry)
print(f"Cette requête lirait {job_dry.total_bytes_processed / 1e6:.2f} Mo")


table = client.get_table(f"{DATASET}.order_items")
print(f"{table.num_rows:,} lignes, {table.num_bytes / 1e6:.1f} Mo")
print("Partition :", table.time_partitioning.field if table.time_partitioning else None)
print("Clustering :", table.clustering_fields)
for champ in table.schema:
    print(f"  {champ.name:<15} {champ.field_type}")

print("\nTables du dataset :")
for t in client.list_tables(DATASET):
    print(" -", t.table_id)
