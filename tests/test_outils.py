"""Tests des outils de l'agent, avec un faux client sémantique (aucun appel réseau)."""

import decimal
import json

import pytest

from src.agent.outils import OutilsVentes
from src.semantique.moteur import ErreurSemantique, ModeleSemantique


class FauxClientSemantique:
    """Remplace ClientSemantique : génère le vrai SQL, mais renvoie des lignes fixes."""

    def __init__(self):
        self.modele = ModeleSemantique("lookml")
        self.requetes = []

    def lister_champs(self, explore):
        return self.modele.lister_champs(explore)

    def executer_requete(self, requete):
        self.modele.generer_sql(requete)          # lève ErreurSemantique si la requête est invalide
        self.requetes.append(requete)
        return [{"products.category": "Parfums", "order_items.ca_net": decimal.Decimal("153191.96")}]


@pytest.fixture
def outils():
    return OutilsVentes(FauxClientSemantique())


def test_lister_champs_separe_dimensions_et_mesures(outils):
    r = outils.lister_champs()
    assert any(c["nom"] == "order_items.ca_net" for c in r["mesures"])
    assert any(c["nom"] == "products.category" for c in r["dimensions"])


def test_interroger_ventes_renvoie_du_json_simple(outils):
    r = outils.interroger_ventes(
        ["products.category", "order_items.ca_net"],
        '{"order_items.created_year": "2025", "users.country": "France"}',
    )
    assert r["nb_lignes"] == 1
    assert r["lignes"][0]["order_items.ca_net"] == 153191.96   # Decimal converti en float
    json.dumps(r)                                              # doit être sérialisable


def test_les_erreurs_sont_renvoyees_a_l_agent(outils):
    r = outils.interroger_ventes(["order_items.inconnu"])
    assert "erreur" in r and "inconnu" in r["erreur"]


def test_json_invalide(outils):
    r = outils.interroger_ventes(["order_items.ca_net"], "pas du json")
    assert "JSON" in r["erreur"]


def test_limite_plafonnee(outils):
    outils.interroger_ventes(["order_items.ca_net"], limite=10_000)
    assert outils.sem.requetes[-1].limit == 200


def test_journal_des_appels(outils):
    outils.lister_champs()
    outils.interroger_ventes(["order_items.ca_net"])
    assert [a["outil"] for a in outils.journal] == ["lister_champs", "interroger_ventes"]
