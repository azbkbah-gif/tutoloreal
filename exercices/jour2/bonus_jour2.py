# bonus_jour2.py
import csv
import pandas as pd


def chiffre_affaires(tjm: int, jours: int) -> int:
    """Renvoie le chiffre d'affaires HT d'une mission."""
    return tjm * jours


# --- 1. CA par année, à la main ---
totaux_annee = {}
with open("missions.csv", encoding="utf-8") as f:
    for ligne in csv.DictReader(f):
        annee = int(ligne["annee"])          # int() : sinon "2025" reste du texte
        ca = chiffre_affaires(int(ligne["tjm"]), int(ligne["jours"]))
        totaux_annee[annee] = totaux_annee.get(annee, 0) + ca

print("CA par année (à la main) :")
for annee in sorted(totaux_annee):          # trié par année croissante
    print(f"  {annee} : {totaux_annee[annee]:>9,} €")

# --- 2. CA par année, avec pandas ---
df = pd.read_csv("missions.csv")
df["ca"] = df["tjm"] * df["jours"]
ca_annee = df.groupby("annee")["ca"].sum()
print("\nCA par année (pandas) :")
print(ca_annee)
print("Identiques :", totaux_annee == ca_annee.to_dict())

# --- 3. Regroupement sur deux colonnes ---
ca_client_annee = df.groupby(["client", "annee"])["ca"].sum()
print("\nCA par client et par année :")
print(ca_client_annee)

# Version tableau croisé : clients en lignes, années en colonnes
tableau = ca_client_annee.unstack(fill_value=0)
print("\nTableau croisé :")
print(tableau)

# Revenir à une table "plate", comme un résultat SQL
print("\nVersion plate :")
print(ca_client_annee.reset_index())