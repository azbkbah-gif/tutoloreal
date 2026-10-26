import json
import os

from dotenv import load_dotenv

from src.clients.meteo import ClientMeteo

if __name__ == "__main__":
    load_dotenv()
    lat = float(os.environ["LATITUDE"])     # le .env contient du texte : float() obligatoire
    lon = float(os.environ["LONGITUDE"])

    client = ClientMeteo()

    temp = client.temperature(lat, lon)
    print(f"Température actuelle : {temp} °C")

    previsions = client.previsions(lat, lon, jours=3)
    print("\nPrévisions :")
    for p in previsions:
        print(f"  {p['date']} : {p['min']} °C / {p['max']} °C")

    with open("previsions.json", "w", encoding="utf-8") as f:
        json.dump(previsions, f, indent=2, ensure_ascii=False)
    print("\nPrévisions sauvegardées dans previsions.json")