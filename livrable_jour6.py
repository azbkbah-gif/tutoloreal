"""Jour 6 : interroger le modèle sémantique comme on le ferait avec le looker-sdk."""

import json
import os

from dotenv import load_dotenv

from src.clients.bigquery_client import ClientBigQuery
from src.semantique.client import ClientSemantique
from src.semantique.moteur import ErreurSemantique, Requete

if __name__ == "__main__":
    load_dotenv()
    bq = ClientBigQuery(os.environ["GCP_PROJECT"], max_go=1.0)
    sem = ClientSemantique(bq, dossier_lookml="lookml")

    # 1. Découvrir le modèle (ce que l'agent fera en premier)
    print("Explores disponibles :")
    for e in sem.lister_explores():
        print(f"  - {e['name']} : {e['label']}")

    print("\nChamps de l'explore ventes_ia :")
    for c in sem.lister_champs("ventes_ia"):
        print(f"  [{c['categorie'][:3]}] {c['name']:<30} {c['label']}")

    # 2. Une requête, exactement comme un WriteQuery Looker
    requete = Requete(
        explore="ventes_ia",
        fields=["products.category", "order_items.ca_net", "order_items.taux_marge"],
        filters={"order_items.created_year": "2025", "users.country": "France"},
        sorts=["order_items.ca_net desc"],
        limit=10,
    )

    print("\nSQL généré :")
    print(sem.voir_sql(requete))

    print("\nRésultat :")
    lignes = sem.executer_requete(requete)
    for ligne in lignes:
        print(f"  {ligne['products.category']:<16} {ligne['order_items.ca_net']:>12,.2f} €"
              f"   marge {ligne['order_items.taux_marge']:.1%}")

    with open("resultat_jour6.json", "w", encoding="utf-8") as f:
        json.dump(lignes, f, indent=2, ensure_ascii=False, default=str)

    # 3. Les garde-fous : ce que le moteur refuse
    print("\nGarde-fous :")
    for q in [
        Requete("ventes_ia", ["products.cost"]),                     # champ masqué
        Requete("ventes_ia", ["order_items.chiffre"]),               # champ inexistant
        Requete("ventes_ia", ["order_items.ca_net"], {"order_items.created_date": "hier"}),
    ]:
        try:
            sem.voir_sql(q)
        except ErreurSemantique as e:
            print(f"  refusé : {e}")
