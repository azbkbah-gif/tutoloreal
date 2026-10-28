"""Tests du moteur sémantique : on vérifie le SQL généré, sans appeler BigQuery."""

import pytest

from src.semantique.moteur import ErreurSemantique, ModeleSemantique, Requete


@pytest.fixture(scope="module")
def modele():
    return ModeleSemantique("lookml")


# ------------------------------------------------------------------ catalogue

def test_explores_presents(modele):
    assert {"order_items", "ventes_ia"} <= set(modele.explores)


def test_ventes_ia_n_expose_pas_les_champs_caches(modele):
    noms = {c["name"] for c in modele.lister_champs("ventes_ia")}
    assert "order_items.ca_net" in noms
    assert "products.cost" not in noms          # hidden: yes
    assert "users.email" not in noms            # donnée personnelle


def test_chaque_champ_expose_a_un_libelle(modele):
    for c in modele.lister_champs("ventes_ia"):
        assert c["label"], f"{c['name']} sans libellé"


# ------------------------------------------------------------------ SQL généré

def test_jointures_uniquement_si_necessaires(modele):
    sql, _ = modele.generer_sql(Requete("ventes_ia", ["order_items.ca_net"]))
    assert "JOIN" not in sql

    sql, _ = modele.generer_sql(Requete("ventes_ia", ["products.category", "order_items.ca_net"]))
    assert "products" in sql and "users" not in sql


def test_les_valeurs_passent_en_parametres(modele):
    """Protection contre l'injection SQL : aucune valeur de filtre dans le texte SQL."""
    piege = "France'; DROP TABLE users; --"
    sql, params = modele.generer_sql(
        Requete("ventes_ia", ["order_items.ca_net"], {"users.country": piege})
    )
    assert "DROP TABLE" not in sql
    assert ("p0", "STRING", piege) in params or any(p[2] == piege for p in params)


def test_filtre_sur_mesure_dans_having(modele):
    sql, _ = modele.generer_sql(
        Requete("ventes_ia", ["products.category", "order_items.nb_commandes"],
                {"order_items.nb_commandes": ">1000"})
    )
    assert "HAVING" in sql
    assert "WHERE" not in sql


def test_filtre_annee(modele):
    sql, params = modele.generer_sql(
        Requete("ventes_ia", ["order_items.ca_net"], {"order_items.created_year": "2025"})
    )
    assert ("p0", "DATE", "2025-01-01") in params or any(p[2] == "2025-01-01" for p in params)
    assert "INTERVAL 1 YEAR" in sql


def test_six_mois_alignes_sur_le_debut_du_mois(modele):
    sql, _ = modele.generer_sql(
        Requete("ventes_ia", ["order_items.ca_net"], {"order_items.created_date": "6 months"})
    )
    assert "DATE_TRUNC(CURRENT_DATE(), MONTH)" in sql
    assert "INTERVAL 5 MONTH" in sql


def test_limite_et_tri(modele):
    sql, _ = modele.generer_sql(
        Requete("ventes_ia", ["products.category", "order_items.ca_net"],
                sorts=["order_items.ca_net desc"], limit=3)
    )
    assert sql.rstrip().endswith("LIMIT 3")
    assert "ORDER BY order_items__ca_net DESC" in sql


# ------------------------------------------------------------------ refus

@pytest.mark.parametrize(
    "requete, message",
    [
        (Requete("ventes_ia", ["products.cost"]), "masqué"),
        (Requete("ventes_ia", ["order_items.inconnu"]), "inconnu"),
        (Requete("explore_inexistant", ["a.b"]), "inconnu"),
        (Requete("ventes_ia", ["order_items.ca_net"], {"order_items.created_date": "hier"}), "illisible"),
        (Requete("ventes_ia", ["order_items.ca_net"], sorts=["products.category asc"]), "tri"),
        (Requete("ventes_ia", []), "aucun champ"),
        (Requete("ventes_ia", ["order_items.ca_net"], limit=100000), "limit"),
    ],
)
def test_requetes_refusees(modele, requete, message):
    with pytest.raises(ErreurSemantique, match=message):
        modele.generer_sql(requete)
