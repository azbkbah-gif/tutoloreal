"""Génère des données fictives au format thelook_ecommerce sur 2 années glissantes.

Tables produites (CSV dans le dossier data/) :
    users, products, orders, order_items

Usage, depuis la racine du repo :
    python scripts/generer_thelook.py
    python scripts/generer_thelook.py --nb-commandes 50000 --graine 7
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# --- Référentiels fictifs ----------------------------------------------------

PRENOMS_F = ["Amina", "Sarah", "Léa", "Fatou", "Chloé", "Inès", "Mariam", "Julie",
             "Aïssatou", "Camille", "Emma", "Nadia", "Laura", "Kadiatou", "Manon"]
PRENOMS_H = ["Aziz", "Thomas", "Moussa", "Lucas", "Mamadou", "Hugo", "Karim", "Nicolas",
             "Ibrahima", "Julien", "Yanis", "Alpha", "Antoine", "Omar", "Louis"]
NOMS = ["Diallo", "Martin", "Bah", "Bernard", "Barry", "Dubois", "Camara", "Thomas",
        "Sow", "Robert", "Kaba", "Petit", "Touré", "Durand", "Keita", "Leroy", "Condé"]

# (pays, poids, villes)
PAYS = [
    ("France", 40, ["Paris", "Lyon", "Marseille", "Lille", "Bordeaux", "Nantes", "Saint-Ouen"]),
    ("Belgique", 8, ["Bruxelles", "Liège", "Anvers"]),
    ("Allemagne", 12, ["Berlin", "Munich", "Hambourg"]),
    ("Espagne", 10, ["Madrid", "Barcelone", "Valence"]),
    ("Italie", 10, ["Rome", "Milan", "Turin"]),
    ("Royaume-Uni", 10, ["Londres", "Manchester", "Leeds"]),
    ("Guinée", 5, ["Conakry", "Kankan", "Labé"]),
    ("Sénégal", 5, ["Dakar", "Thiès", "Saint-Louis"]),
]
SOURCES_TRAFIC = [("Search", 45), ("Organic", 15), ("Facebook", 10), ("Email", 10),
                  ("Display", 10), ("Instagram", 10)]

# (catégorie, département, prix_min, prix_max, poids_ventes, mots du nom)
CATEGORIES = [
    ("Soins du visage", "Femme", 12, 95, 25, ["Sérum", "Crème de jour", "Crème de nuit", "Contour des yeux", "Masque"]),
    ("Maquillage", "Femme", 8, 55, 22, ["Fond de teint", "Mascara", "Rouge à lèvres", "Palette", "Correcteur"]),
    ("Parfums", "Mixte", 35, 160, 15, ["Eau de parfum", "Eau de toilette", "Coffret parfum"]),
    ("Capillaire", "Mixte", 6, 45, 18, ["Shampooing", "Après-shampooing", "Masque capillaire", "Huile capillaire"]),
    ("Corps", "Mixte", 6, 40, 10, ["Lait corps", "Gel douche", "Gommage", "Crème mains"]),
    ("Homme", "Homme", 7, 60, 10, ["Gel rasage", "Baume après-rasage", "Soin barbe", "Crème hydratante"]),
]
MARQUES = ["Lumière Paris", "Nova Skin", "Atelier Bleu", "Karité & Co", "Maison Oréa",
           "Pure Sahel", "Velours", "Botanica Lab", "Ivoire", "Studio Teint"]
VARIANTES = ["Hydratant", "Éclat", "Anti-âge", "Peaux sensibles", "Bio", "Intense",
             "Nutrition", "Matifiant", "Fraîcheur", "Réparateur"]

# (statut, poids)
STATUTS = [("Complete", 55), ("Shipped", 15), ("Processing", 8), ("Cancelled", 12), ("Returned", 10)]


def choix_pondere(rng: random.Random, options: list[tuple]) -> tuple:
    """Choisit un tuple dans une liste dont le 2e élément est le poids."""
    return rng.choices(options, weights=[o[1] for o in options], k=1)[0]


def fmt(d: datetime | None) -> str:
    """Format TIMESTAMP accepté par BigQuery ; vide = NULL."""
    return d.strftime("%Y-%m-%d %H:%M:%S") if d else ""


def facteur_saison(d: datetime) -> float:
    """Plus de ventes en fin d'année et une légère croissance dans le temps."""
    saison = {1: 0.8, 2: 0.8, 3: 0.9, 4: 0.95, 5: 1.0, 6: 1.0, 7: 0.9,
              8: 0.85, 9: 1.0, 10: 1.05, 11: 1.4, 12: 1.6}[d.month]
    return saison


def date_ponderee(rng: random.Random, debut: datetime, fin: datetime) -> datetime:
    """Tire une date entre debut et fin, en favorisant les mois forts et la fin de période."""
    total = (fin - debut).total_seconds()
    while True:
        d = debut + timedelta(seconds=rng.random() * total)
        croissance = 0.75 + 0.5 * (d - debut).total_seconds() / total   # de 0,75 à 1,25
        if rng.random() < facteur_saison(d) * croissance / 2.0:
            return d


# --- Générateurs de tables -----------------------------------------------------

def generer_produits(rng: random.Random, nb: int) -> list[dict]:
    produits = []
    for pid in range(1, nb + 1):
        cat, dept, pmin, pmax, _, mots = rng.choice(CATEGORIES)
        marque = rng.choice(MARQUES)
        prix = round(rng.uniform(pmin, pmax), 2)
        produits.append({
            "id": pid,
            "cost": round(prix * rng.uniform(0.3, 0.55), 2),
            "category": cat,
            "name": f"{marque} {rng.choice(mots)} {rng.choice(VARIANTES)}",
            "brand": marque,
            "retail_price": prix,
            "department": dept,
            "sku": f"SKU-{pid:06d}",
            "distribution_center_id": rng.randint(1, 5),
        })
    return produits


def generer_users(rng: random.Random, nb: int, debut: datetime, fin: datetime) -> list[dict]:
    users = []
    for uid in range(1, nb + 1):
        genre = rng.choices(["F", "M"], weights=[65, 35])[0]
        prenom = rng.choice(PRENOMS_F if genre == "F" else PRENOMS_H)
        nom = rng.choice(NOMS)
        pays, _, villes = choix_pondere(rng, PAYS)
        # une partie des clients existait avant la période
        cree = debut - timedelta(days=rng.randint(1, 365)) if rng.random() < 0.3 \
            else debut + timedelta(seconds=rng.random() * (fin - debut).total_seconds() * 0.9)
        users.append({
            "id": uid,
            "first_name": prenom,
            "last_name": nom,
            "email": f"{prenom}.{nom}{uid}@exemple.com".lower(),
            "age": rng.randint(16, 70),
            "gender": genre,
            "city": rng.choice(villes),
            "country": pays,
            "traffic_source": choix_pondere(rng, SOURCES_TRAFIC)[0],
            "created_at": fmt(cree),
        })
    return users


def generer_commandes(rng, nb, users, produits, debut, fin):
    poids_cat = {c[0]: c[4] for c in CATEGORIES}
    poids_produits = [poids_cat[p["category"]] for p in produits]
    orders, items = [], []
    item_id = 1

    for oid in range(1, nb + 1):
        cree = date_ponderee(rng, debut, fin)
        user = rng.choice(users)
        # un client ne peut pas commander avant d'avoir créé son compte
        user_cree = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        if user_cree > cree:
            user["created_at"] = fmt(cree - timedelta(days=rng.randint(0, 30), hours=rng.randint(1, 23)))
        statut = choix_pondere(rng, STATUTS)[0]

        # dates de cycle de vie cohérentes avec le statut
        expedie = livre = retourne = None
        if statut in ("Shipped", "Complete", "Returned"):
            expedie = cree + timedelta(hours=rng.randint(6, 72))
        if statut in ("Complete", "Returned"):
            livre = expedie + timedelta(hours=rng.randint(24, 120))
        if statut == "Returned":
            retourne = livre + timedelta(days=rng.randint(2, 20))
        # une commande récente ne peut pas déjà être livrée dans le futur
        if livre and livre > fin:
            statut, livre, retourne = "Shipped", None, None
        if expedie and expedie > fin:
            statut, expedie = "Processing", None

        nb_articles = rng.choices([1, 2, 3, 4, 5], weights=[45, 28, 15, 8, 4])[0]
        for prod in rng.choices(produits, weights=poids_produits, k=nb_articles):
            remise = rng.choices([1.0, 0.9, 0.8, 0.7], weights=[70, 15, 10, 5])[0]
            if cree.month in (11, 12) and rng.random() < 0.3:      # promos de fin d'année
                remise = min(remise, 0.8)
            items.append({
                "id": item_id,
                "order_id": oid,
                "user_id": user["id"],
                "product_id": prod["id"],
                "status": statut,
                "created_at": fmt(cree),
                "shipped_at": fmt(expedie),
                "delivered_at": fmt(livre),
                "returned_at": fmt(retourne),
                "sale_price": round(prod["retail_price"] * remise, 2),
            })
            item_id += 1

        orders.append({
            "order_id": oid,
            "user_id": user["id"],
            "status": statut,
            "gender": user["gender"],
            "created_at": fmt(cree),
            "returned_at": fmt(retourne),
            "shipped_at": fmt(expedie),
            "delivered_at": fmt(livre),
            "num_of_item": nb_articles,
        })
    return orders, items


def ecrire_csv(chemin: Path, lignes: list[dict]) -> None:
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        writer.writeheader()
        writer.writerows(lignes)
    print(f"  {chemin.name:<18} {len(lignes):>8,} lignes")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nb-users", type=int, default=8000)
    parser.add_argument("--nb-produits", type=int, default=600)
    parser.add_argument("--nb-commandes", type=int, default=40000)
    parser.add_argument("--graine", type=int, default=42, help="même graine = mêmes données")
    parser.add_argument("--sortie", default="data")
    args = parser.parse_args()

    rng = random.Random(args.graine)
    fin = datetime.now().replace(microsecond=0)
    debut = fin - timedelta(days=730)                  # 2 années glissantes
    sortie = Path(args.sortie)
    sortie.mkdir(parents=True, exist_ok=True)

    print(f"Période : {debut:%Y-%m-%d} -> {fin:%Y-%m-%d}")
    produits = generer_produits(rng, args.nb_produits)
    users = generer_users(rng, args.nb_users, debut, fin)
    orders, items = generer_commandes(rng, args.nb_commandes, users, produits, debut, fin)

    print(f"Fichiers écrits dans {sortie}/ :")
    ecrire_csv(sortie / "products.csv", produits)
    ecrire_csv(sortie / "users.csv", users)   # après les commandes : created_at a pu être ajusté
    ecrire_csv(sortie / "orders.csv", orders)
    ecrire_csv(sortie / "order_items.csv", items)


if __name__ == "__main__":
    main()