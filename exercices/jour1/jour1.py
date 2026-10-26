client = "L'Oréal"
tjm = 600
taux_tva = 0.20
en_mission = True
print(client, tjm, taux_tva, en_mission)
print(type(tjm), type(taux_tva))

jours = 21
ca_mois = tjm * jours
print(f"CA du mois chez {client}: {ca_mois} € HT")
print(f"Soit {ca_mois *(1 + taux_tva):.2f} € TTC")

if tjm >= 600:
    print("Bon TJM")
elif tjm >= 540:
    print("TJM correct")
else:
    print("TJM à negocier")

for mois in range(1, 13):
    print(f"CA du mois {mois}: {tjm * 20} € HT")

saisie = input("Combien de jours travaillés ? ")
jours = int(saisie)
print(f"CA : {tjm * jours} € ")
