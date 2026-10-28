"""Le SQL généré par le moteur doit être du SQL BigQuery valide.

Le validateur LookML ne lit pas le SQL contenu dans sql: et sql_on: (le vrai Looker non plus).
Ici, on génère une requête qui utilise CHAQUE champ visible et CHAQUE jointure de chaque
explore, puis on la fait analyser par sqlglot, un parseur SQL qui connaît le dialecte BigQuery.
Une jointure incomplète ("sql_on: ${a} = ;;") ou une parenthèse oubliée fait échouer le test.
"""

import pytest
import sqlglot
from sqlglot.errors import ParseError

from src.semantique.moteur import ModeleSemantique, Requete

MODELE = ModeleSemantique("lookml")


def _champs_par_vue(explore: str) -> dict[str, list[str]]:
    """Champs utilisables (cachés compris) regroupés par vue de l'explore."""
    vues: dict[str, list[str]] = {}
    for c in MODELE.lister_champs(explore, inclure_caches=True):
        vues.setdefault(c["name"].split(".")[0], []).append(c["name"])
    return vues


@pytest.mark.parametrize("explore", sorted(MODELE.explores))
def test_tous_les_champs_generent_du_sql_valide(explore):
    for vue, champs in _champs_par_vue(explore).items():
        for champ in champs:
            sql, _ = MODELE.generer_sql(Requete(explore, [champ], limit=10), autoriser_caches=True)
            try:
                sqlglot.parse_one(sql, read="bigquery")
            except ParseError as e:
                pytest.fail(f"[{explore}] SQL invalide pour {champ} :\n{sql}\n\n{e}")


@pytest.mark.parametrize("explore", sorted(MODELE.explores))
def test_toutes_les_jointures_generent_du_sql_valide(explore):
    """Une requête par vue jointe, pour forcer chaque sql_on à apparaître dans le SQL."""
    base = MODELE.explores[explore].get("view_name", explore)
    mesure_base = next(
        (c["name"] for c in MODELE.lister_champs(explore, inclure_caches=True)
         if c["categorie"] == "measure" and c["name"].startswith(base + ".")),
        None,
    )
    for vue, champs in _champs_par_vue(explore).items():
        if vue == base:
            continue
        dimension = next(c for c in champs if not c.endswith("_raw"))
        champs_requete = [dimension] + ([mesure_base] if mesure_base else [])
        sql, _ = MODELE.generer_sql(Requete(explore, champs_requete, limit=10), autoriser_caches=True)
        assert "JOIN" in sql and f" AS {vue}" in sql, f"jointure {vue} absente :\n{sql}"
        try:
            sqlglot.parse_one(sql, read="bigquery")
        except ParseError as e:
            pytest.fail(f"[{explore}] jointure '{vue}' : SQL invalide :\n{sql}\n\n{e}")
