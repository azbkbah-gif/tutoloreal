# livrable_jour1.py

TAUX_TVA = 0.20          # en majuscules : une constante, qui ne change pas
OBJECTIF_ANNUEL = 120000
MOIS_TRAVAILLES = 11

# 1. Saisie (input renvoie du texte, int() le transforme en nombre)
tjm = int(input("Ton TJM (€) : "))
jours = int(input("Nombre de jours travaillés par mois : "))

# 2. CA mensuel
ca_mois_ht = tjm * jours
ca_mois_ttc = ca_mois_ht * (1 + TAUX_TVA)
print(f"CA mensuel : {ca_mois_ht} € HT, soit {ca_mois_ttc:.2f} € TTC")

# 3. CA annuel
ca_annuel = ca_mois_ht * MOIS_TRAVAILLES
print(f"CA annuel sur {MOIS_TRAVAILLES} mois : {ca_annuel} € HT")

# 4. Objectif
if ca_annuel >= OBJECTIF_ANNUEL:
    print("Objectif atteint")
else:
    manque = OBJECTIF_ANNUEL - ca_annuel
    print(f"Il manque {manque} € pour atteindre l'objectif")