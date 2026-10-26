import csv
import os

from dotenv import load_dotenv

from src.clients.bigquery_client import ClientBigQuery

if __name__ == "__main__":
    load_dotenv()
    projet = os.environ["GCP_PROJECT"]

    # 1. Client normal, limite 1 Go
    bq = ClientBigQuery(projet, max_go=1.0)
    resultats = bq.ca_par_categorie("2025-01-01")

    print("CA par catégorie depuis le 01/01/2025 :")
    for r in resultats:
        print(f"  {r['categorie']:<16} {r['nb_commandes']:>6} commandes  {r['ca']:>12,.2f} €")
    print(f"  {'TOTAL':<16} {sum(r['ca'] for r in resultats):>32,.2f} €")

    # 2. Export CSV
    with open("ca_categorie.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["categorie", "nb_commandes", "ca"])
        writer.writeheader()
        writer.writerows(resultats)
    print("\nRésultat écrit dans ca_categorie.csv")

    # 3. Test du garde-fou : limite ridiculement basse
    bq_strict = ClientBigQuery(projet, max_go=0.0001)
    try:
        bq_strict.ca_par_categorie("2025-01-01")
        print("Le garde-fou n'a pas fonctionné !")
    except ValueError as e:
        print(f"\nGarde-fou déclenché comme prévu : {e}")