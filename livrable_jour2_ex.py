import csv
import pandas as pd

missions =  [
    {"client": "renault", "annee": 2023,  "tjm": 520, "jours": 200},
    {"client": "carrefour", "annee": 2024,  "tjm": 550, "jours": 190},
    {"client": "L'Oréal", "annee": 2025,  "tjm": 580, "jours": 205},
    {"client": "Servier", "annee": 2022,  "tjm": 500, "jours": 180},
    {"client": "carrefour", "annee": 2025,  "tjm": 560, "jours": 40},
    {"client": "L'Oréal", "annee": 2026,  "tjm": 600, "jours": 150}, 
]

def chiffre_affaires(tjm: int, jours: int) -> int:
    """Renvoie le CA HT d'une mission"""
    return tjm * jours

with open("missions.csv","w", newline="",  encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["client", "annee", "tjm", "jours"])
    writer.writeheader()
    writer.writerows(missions)

totaux = {}
with open("missions.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for ligne in reader:
        client = ligne["client"]
        ca = chiffre_affaires(int(ligne["tjm"]), int(ligne["jours"]))
        totaux[client] = totaux.get(client, 0) + ca
print("CA par client (module csv) : ")
for client, total in sorted(totaux.items(), key=lambda x: x[1], reverse=True):
    print(f"{client:<10} {total:>9,} $")

with open("ca_par_client.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["client", "ca_total"])
    for client, total in totaux.items():
        writer.writerow([client, total])

df = pd.read_csv("missions.csv")
df["ca"] = df["tjm"] * df["jours"]
totaux_pandas = df.groupby("client") ["ca"].sum()

print("\nCA par client (pandas) : ")
print(totaux_pandas.sort_values(ascending=False))

if totaux == totaux_pandas.to_dict():
    print("\nVerification Ok: les deux calculs sont identiques")
else:
    print("\nattention : les resultats different")

