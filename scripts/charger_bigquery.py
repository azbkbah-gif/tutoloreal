"""Crée le dataset BigQuery et y charge les CSV générés par generer_thelook.py.

Prérequis :
    - gcloud auth application-default login (fait au jour 4)
    - GCP_PROJECT dans le .env à la racine
    - les CSV présents dans data/

Usage, depuis la racine du repo :
    python scripts/charger_bigquery.py
    python scripts/charger_bigquery.py --dataset thelook_fictif --location EU
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

SF = bigquery.SchemaField

SCHEMAS = {
    "products": [
        SF("id", "INTEGER", mode="REQUIRED"),
        SF("cost", "FLOAT"),
        SF("category", "STRING"),
        SF("name", "STRING"),
        SF("brand", "STRING"),
        SF("retail_price", "FLOAT"),
        SF("department", "STRING"),
        SF("sku", "STRING"),
        SF("distribution_center_id", "INTEGER"),
    ],
    "users": [
        SF("id", "INTEGER", mode="REQUIRED"),
        SF("first_name", "STRING"),
        SF("last_name", "STRING"),
        SF("email", "STRING"),
        SF("age", "INTEGER"),
        SF("gender", "STRING"),
        SF("city", "STRING"),
        SF("country", "STRING"),
        SF("traffic_source", "STRING"),
        SF("created_at", "TIMESTAMP"),
    ],
    "orders": [
        SF("order_id", "INTEGER", mode="REQUIRED"),
        SF("user_id", "INTEGER"),
        SF("status", "STRING"),
        SF("gender", "STRING"),
        SF("created_at", "TIMESTAMP"),
        SF("returned_at", "TIMESTAMP"),
        SF("shipped_at", "TIMESTAMP"),
        SF("delivered_at", "TIMESTAMP"),
        SF("num_of_item", "INTEGER"),
    ],
    "order_items": [
        SF("id", "INTEGER", mode="REQUIRED"),
        SF("order_id", "INTEGER"),
        SF("user_id", "INTEGER"),
        SF("product_id", "INTEGER"),
        SF("status", "STRING"),
        SF("created_at", "TIMESTAMP"),
        SF("shipped_at", "TIMESTAMP"),
        SF("delivered_at", "TIMESTAMP"),
        SF("returned_at", "TIMESTAMP"),
        SF("sale_price", "FLOAT"),
    ],
}

# Partitionnement par jour + clustering, comme on le ferait en entreprise
PARTITIONS = {
    "orders": ("created_at", ["status", "user_id"]),
    "order_items": ("created_at", ["status", "product_id"]),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default="thelook_fictif")
    parser.add_argument("--location", default="EU")
    parser.add_argument("--donnees", default="data")
    args = parser.parse_args()

    load_dotenv()
    projet = os.environ["GCP_PROJECT"]
    client = bigquery.Client(project=projet)

    # 1. Dataset (ne fait rien s'il existe déjà)
    dataset = bigquery.Dataset(f"{projet}.{args.dataset}")
    dataset.location = args.location
    dataset.description = "Données fictives au format thelook_ecommerce (2 ans glissants)"
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset prêt : {projet}.{args.dataset} ({args.location})")

    # 2. Chargement de chaque table
    for table, schema in SCHEMAS.items():
        chemin = Path(args.donnees) / f"{table}.csv"
        config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,   # remplace à chaque run
        )
        if table in PARTITIONS:
            colonne, clusters = PARTITIONS[table]
            config.time_partitioning = bigquery.TimePartitioning(field=colonne)
            config.clustering_fields = clusters

        table_id = f"{projet}.{args.dataset}.{table}"
        with open(chemin, "rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=config)
        job.result()                                    # attend la fin du chargement
        nb = client.get_table(table_id).num_rows
        print(f"  {table:<12} {nb:>8,} lignes chargées")

    # 3. Vérification
    sql = f"""
    SELECT DATE_TRUNC(DATE(created_at), MONTH) AS mois,
           COUNT(DISTINCT order_id) AS nb_commandes,
           ROUND(SUM(sale_price), 2) AS ca
    FROM `{projet}.{args.dataset}.order_items`
    WHERE status = 'Complete'
    GROUP BY mois ORDER BY mois DESC LIMIT 6
    """
    print("\nContrôle, CA des 6 derniers mois :")
    for ligne in client.query(sql).result():
        print(f"  {ligne['mois']}  {ligne['nb_commandes']:>6} commandes  {ligne['ca']:>12,.2f} €")


if __name__ == "__main__":
    main()