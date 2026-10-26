from google.cloud import bigquery


class ClientBigQuery:
    """Client BigQuery avec garde-fou sur le volume lu."""

    def __init__(self, project: str, dataset: str = "thelook_fictif", max_go: float = 1.0):
        self.client = bigquery.Client(project=project)
        self.dataset = f"{project}.{dataset}"
        self.max_go = max_go

    def _config(self, params: list | None, dry_run: bool = False) -> bigquery.QueryJobConfig:
        """Construit la configuration commune à tous les appels."""
        return bigquery.QueryJobConfig(
            query_parameters=params or [],
            dry_run=dry_run,
            use_query_cache=not dry_run,
        )

    def estimer_go(self, sql: str, params: list | None = None) -> float:
        """Volume que lirait la requête, en Go, sans l'exécuter ni la payer."""
        job = self.client.query(sql, job_config=self._config(params, dry_run=True))
        return job.total_bytes_processed / 1e9

    def executer(self, sql: str, params: list | None = None) -> list[dict]:
        """Exécute la requête si elle reste sous max_go, et renvoie une liste de dicts."""
        go = self.estimer_go(sql, params)
        if go > self.max_go:
            raise ValueError(
                f"Requête trop coûteuse : {go:.4f} Go (limite {self.max_go} Go)"
            )
        job = self.client.query(sql, job_config=self._config(params))
        return [dict(ligne) for ligne in job.result()]

    def ca_par_categorie(self, date_debut: str, statut: str = "Complete") -> list[dict]:
        """CA HT et nombre de commandes par catégorie de produit depuis date_debut (AAAA-MM-JJ)."""
        sql = f"""
        SELECT p.category AS categorie,
               COUNT(DISTINCT oi.order_id) AS nb_commandes,
               ROUND(SUM(oi.sale_price), 2) AS ca
        FROM `{self.dataset}.order_items` oi
        JOIN `{self.dataset}.products` p ON p.id = oi.product_id
        WHERE DATE(oi.created_at) >= @date_debut
          AND oi.status = @statut
        GROUP BY categorie
        ORDER BY ca DESC
        """
        params = [
            bigquery.ScalarQueryParameter("date_debut", "DATE", date_debut),
            bigquery.ScalarQueryParameter("statut", "STRING", statut),
        ]
        return self.executer(sql, params)