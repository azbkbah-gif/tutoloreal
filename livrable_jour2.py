

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