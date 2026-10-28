"""Les outils que l'agent peut appeler. Chaque fonction = un outil.

Gemini lit le NOM, la DOCSTRING et les ANNOTATIONS DE TYPE de chaque fonction
pour décider quand l'appeler et avec quels arguments : ils sont le « prompt » de l'outil.
"""

import datetime
import decimal
import json

from google.api_core.exceptions import GoogleAPIError

from src.semantique.client import ClientSemantique
from src.semantique.moteur import ErreurSemantique, Requete

EXPLORE = "ventes_ia"
MAX_LIGNES = 200


def _serialisable(valeur):
    """Convertit les types BigQuery (Decimal, date) en types JSON simples."""
    if isinstance(valeur, decimal.Decimal):
        return float(valeur)
    if isinstance(valeur, (datetime.date, datetime.datetime)):
        return valeur.isoformat()
    return valeur


class OutilsVentes:
    """Expose le modèle sémantique à l'agent, avec un journal de tous les appels."""

    def __init__(self, semantique: ClientSemantique):
        self.sem = semantique
        self.journal: list[dict] = []

    def _tracer(self, outil: str, arguments: dict, resultat: dict) -> dict:
        self.journal.append({"outil": outil, "arguments": arguments, "resultat": resultat})
        if "erreur" in resultat:
            apercu = "ERREUR " + resultat["erreur"]
        elif "nb_lignes" in resultat:
            apercu = f"{resultat['nb_lignes']} ligne(s)"
        else:
            apercu = f"{len(resultat.get('dimensions', []))} dimensions, {len(resultat.get('mesures', []))} mesures"
        print(f"   [outil] {outil}({json.dumps(arguments, ensure_ascii=False)}) -> {apercu}")
        return resultat

    # ---------------------------------------------------------------- outil 1

    def lister_champs(self) -> dict:
        """Liste les champs disponibles pour analyser les ventes.

        À appeler AVANT toute requête pour connaître les noms exacts des champs.
        Renvoie les dimensions (axes d'analyse : date, catégorie, marque, pays, âge...)
        et les mesures (chiffres : CA net, nombre de commandes, panier moyen, marge...),
        avec leur description et leurs synonymes.
        """
        champs = self.sem.lister_champs(EXPLORE)
        resultat = {
            "dimensions": [
                {"nom": c["name"], "libelle": c["label"], "description": c["description"]}
                for c in champs if c["categorie"] == "dimension"
            ],
            "mesures": [
                {"nom": c["name"], "libelle": c["label"], "description": c["description"]}
                for c in champs if c["categorie"] == "measure"
            ],
        }
        return self._tracer("lister_champs", {}, resultat)

    # ---------------------------------------------------------------- outil 2

    def interroger_ventes(
        self,
        champs: list[str],
        filtres_json: str = "{}",
        tri: str = "",
        limite: int = 50,
    ) -> dict:
        """Exécute une requête sur le modèle sémantique des ventes et renvoie les lignes.

        Args:
            champs: noms exacts de dimensions et de mesures, tels que renvoyés par
                lister_champs, par exemple ["products.category", "order_items.ca_net"].
            filtres_json: objet JSON {"nom_du_champ": "expression"} au format des filtres Looker.
                Exemples d'expressions : "2025" (une année), "2025-03" (un mois),
                "2025-01-01 to 2025-07-01" (une période, fin exclue), "last month",
                "this year", "6 months" (6 derniers mois), "France" (égal),
                "France,Belgique" (l'un ou l'autre), "-Cancelled" (différent de),
                "%parf%" (contient), ">1000" (supérieur à, aussi sur une mesure).
                Exemple complet : {"order_items.created_year": "2025", "users.country": "France"}
            tri: un champ demandé suivi de "asc" ou "desc", par exemple "order_items.ca_net desc".
            limite: nombre maximum de lignes (200 au plus).
        """
        arguments = {"champs": champs, "filtres_json": filtres_json, "tri": tri, "limite": limite}
        try:
            try:
                filtres = json.loads(filtres_json or "{}")
            except json.JSONDecodeError:
                raise ValueError(f"filtres_json n'est pas un JSON valide : {filtres_json!r}")
            if not isinstance(filtres, dict):
                raise ValueError("filtres_json doit être un objet JSON")
            requete = Requete(
                explore=EXPLORE,
                fields=list(champs),
                filters={str(k): str(v) for k, v in filtres.items()},
                sorts=[tri] if tri else [],
                limit=max(1, min(int(limite), MAX_LIGNES)),
            )
            lignes = self.sem.executer_requete(requete)
        except (ErreurSemantique, ValueError) as e:
            # l'erreur est RENVOYÉE au modèle, qui peut se corriger et réessayer
            return self._tracer("interroger_ventes", arguments, {"erreur": str(e)})
        except GoogleAPIError as e:
            return self._tracer("interroger_ventes", arguments,
                                {"erreur": f"BigQuery a refusé la requête : {type(e).__name__}"})
        lignes = [{k: _serialisable(v) for k, v in ligne.items()} for ligne in lignes]
        return self._tracer("interroger_ventes", arguments, {"nb_lignes": len(lignes), "lignes": lignes})
