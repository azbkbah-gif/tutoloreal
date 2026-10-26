

# clients = ["L'Oréal", "Carrefour", "Renault"]
# print(clients[0])
# print(clients[-1])
# clients.append("Servier")
# print(len(clients))
# for c in clients:
#     print(c.upper())

# tjms = [600, 540, 650, 580]
# print(min(tjms))
# print(sum(tjms))

# mission = {"client": "L'Oréal", "tjm": 600, "debut": "2026-11-02"}
# print(mission["tjm"])
# print(mission["debut"])
# print(mission.get("fin", "inconnue"))
# mission["technos"] = ["Lookml", "Python"]
# for cle, valeur in mission.items():
#     print(f"{cle} : {valeur}")


missions = [
    {"client": "L'oréal", "tjm": 600, "jours": 20},
    {"client": "carrefour", "tjm": 540, "jours": 18},
    {"client": "renault", "tjm": 650, "jours":21}
]
for m in missions:
    print(f"{m['client']}: {m['tjm']} * {m['jours']} $")

tjms = [m["tjm"] for m in missions]
bien_payees =  [m for m in missions if m["tjm"] >=550]
travplus = [m for m in missions if m["jours"] > 19]
noms = [m["client"] for m in bien_payees]
print(tjms)
print(noms)
print(sum(tjms)/len(tjms))
print(travplus)

def chiffre_affaires(tjm: int, jours: int = 20) -> int:
    # """Calcule le chiffre d'affaires HT"""
    """Renvoie le CA HT. 'jours' vaut 20 par defaut."""
    return tjm * jours
print(chiffre_affaires(600))
print(chiffre_affaires(600, jours=18))

for m in missions:
    print(m["client"], chiffre_affaires(m["tjm"], m["jours"]))

try: 
    jours = int(input("jours: "))
except ValueError:
    print("Merci de saisir un nombre")
    jours = 0

import csv
with open("missions.csv", "w", newline="" , encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["client", "tjm", "jours"])
    writer.writeheader()
    writer.writerows(missions)

with open("missions.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for ligne in reader:
        print(ligne["client"], ligne["tjm"])


import pandas as pd
df = pd.read_csv("missions.csv")
print(df)
print(df[df["tjm"] >= 550])
df["ca"] = df["tjm"] * df["jours"]
print(df.sort_values("ca", ascending=False)) #order by
print(df["ca"].sum())  #sum
print(df.groupby("client")["ca"].sum())  #group by  
df.to_csv("resultat.csv", index=False)  #export to csv



# import csv
# import pandas as pd

# missions = [
#     {"client": "renault", "annee": 2023,  "tjm": 520, "jours": 200},
#     {"client": "carrefour", "annee": 2024,  "tjm": 550, "jours": 190},
#     {"client": "L'Oréal", "annee": 2025,  "tjm": 580, "jours": 205},
#     {"client": "Servier", "annee": 2022,  "tjm": 500, "jours": 180},
#     {"client": "carrefour", "annee": 2025,  "tjm": 560, "jours": 40},
#     {"client": "L'Oréal", "annee": 2026,  "tjm": 600, "jours": 150}, 
# ]

# def chiffre_affaires(tjm: int, jours: int) -> int:
#     """Renvoie le CA HT d'une mission"""
#     return tjm * jours

# with open("missions.csv","w", newline="",  encoding="utf-8") as f:
#     writer = csv.DictWriter(f, fieldnames=["client", "annee", "tjm", "jours"])
#     writer.writeheader()
#     writer.writerows(missions)

# totaux = {}
# with open("missions.csv", encoding="utf-8") as f:
#     reader = csv.DictReader(f)
#     for ligne in reader:
#         client = ligne["client"]
#         ca = chiffre_affaires(int(ligne["tjm"]), int(ligne["jours"]))
#         totaux[client] = totaux.get(client, 0) + ca
# print("CA par client (module csv) : ")
# for client, total in sorted(totaux.items(), key=lambda x: x[1], reverse=True):
#     print(f"{client:<10} {total:>9,} $")

# with open("ca_par_client.csv", "w", newline="", encoding="utf-8") as f:
#     writer = csv.writer(f)
#     writer.writerow(["client", "ca_total"])
#     for client, total in totaux.items():
#         writer.writerow([client, total])

# df = pd.read_csv("missions.csv")
# df["ca"] = df["tjm"] * df["jours"]
# totaux_pandas = df.groupby("client") ["ca"].sum()

# print("\nCA par client (pandas) : ")
# print(totaux_pandas.sort_values(ascending=False))

# if totaux == totaux_pandas.to_dict():
#     print("\nVerification Ok: les deux calculs sont identiques")
# else:
#     print("\nattention : les resultats different")
