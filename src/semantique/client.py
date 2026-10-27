"""Le « compagnon » parle à ce client : il imite les appels du looker-sdk du jour 6."""

from google.cloud import bigquery

from src.clients.bigquery_client import ClientBigQuery
from src.semantique.moteur import ModeleSemantique, Requete


class ClientSemantique:
    """Interroge le modèle sémantique (LookML) puis exécute le SQL généré sur BigQuery."""

    def __init__(self, bq: ClientBigQuery, dossier_lookml: str = "lookml"):
        self.bq = bq
        self.modele = ModeleSemantique(dossier_lookml)

    def lister_explores(self) -> list[dict]:
        """Équivalent de sdk.all_lookml_models()."""
        return [{"name": nom, "label": e.get("label", nom), "description": e.get("description", "")}
                for nom, e in self.modele.explores.items()]

    def lister_champs(self, explore: str) -> list[dict]:
        """Équivalent de sdk.lookml_model_explore(...).fields : champs visibles uniquement."""
        return self.modele.lister_champs(explore)

    def voir_sql(self, requete: Requete) -> str:
        """Équivalent de sdk.run_inline_query(result_format="sql", ...)."""
        sql, _ = self.modele.generer_sql(requete)
        return sql

    def executer_requete(self, requete: Requete) -> list[dict]:
        """Équivalent de sdk.run_inline_query(result_format="json", ...)."""
        sql, params = self.modele.generer_sql(requete)
        params_bq = [bigquery.ScalarQueryParameter(nom, type_, val) for nom, type_, val in params]
        lignes = self.bq.executer(sql, params_bq)
        # clés au format Looker : "vue.champ"
        return [{cle.replace("__", "."): val for cle, val in ligne.items()} for ligne in lignes]
