"""Recette : le moteur doit donner les mêmes chiffres qu'une requête SQL écrite à la main.

Ces tests interrogent le vrai BigQuery. Ils sont exclus par défaut :
    pytest -m bigquery          # pour les lancer en local (ADC + GCP_PROJECT dans le .env)
"""

import os

import pytest

pytestmark = pytest.mark.bigquery


@pytest.fixture(scope="module")
def contexte():
    from dotenv import load_dotenv
    from google.cloud import bigquery

    from src.clients.bigquery_client import ClientBigQuery
    from src.semantique.client import ClientSemantique

    load_dotenv()
    projet = os.environ["GCP_PROJECT"]
    bq = ClientBigQuery(projet, max_go=1.0)
    return bq, ClientSemantique(bq, "lookml"), f"{projet}.thelook_fictif", bigquery


def test_ca_net_par_categorie_france_2025(contexte):
    from src.semantique.moteur import Requete

    bq, sem, ds, _ = contexte
    moteur = sem.executer_requete(Requete(
        "ventes_ia",
        ["products.category", "order_items.ca_net"],
        {"order_items.created_year": "2025", "users.country": "France"},
    ))
    reference = bq.executer(f"""
        SELECT p.category, SUM(oi.sale_price) AS ca_net
        FROM `{ds}.order_items` oi
        JOIN `{ds}.products` p ON p.id = oi.product_id
        JOIN `{ds}.users` u ON u.id = oi.user_id
        WHERE EXTRACT(YEAR FROM oi.created_at) = 2025
          AND oi.status NOT IN ('Cancelled', 'Returned')
          AND u.country = 'France'
        GROUP BY 1
    """)
    attendu = {r["category"]: float(r["ca_net"]) for r in reference}
    obtenu = {r["products.category"]: float(r["order_items.ca_net"]) for r in moteur}
    assert obtenu.keys() == attendu.keys()
    for categorie, valeur in attendu.items():
        assert obtenu[categorie] == pytest.approx(valeur, abs=0.01), categorie


def test_nombre_de_commandes_2025(contexte):
    from src.semantique.moteur import Requete

    bq, sem, ds, _ = contexte
    moteur = sem.executer_requete(Requete(
        "ventes_ia", ["order_items.nb_commandes"], {"order_items.created_year": "2025"}))
    reference = bq.executer(f"""
        SELECT COUNT(DISTINCT order_id) AS n FROM `{ds}.order_items`
        WHERE EXTRACT(YEAR FROM created_at) = 2025
    """)
    assert moteur[0]["order_items.nb_commandes"] == reference[0]["n"]
    assert moteur[0]["order_items.nb_commandes"] > 10_000
