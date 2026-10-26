import requests


class ClientMeteo:
    """Client minimal pour l'API publique Open-Meteo."""

    def __init__(self, timeout: int = 10):
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.timeout = timeout

    def _appeler(self, params: dict) -> dict | None:
        """Appelle l'API et renvoie la réponse en dict, ou None en cas d'erreur."""
        try:
            rep = requests.get(self.base_url, params=params, timeout=self.timeout)
            rep.raise_for_status()
            return rep.json()
        except requests.exceptions.Timeout:
            print("L'API ne répond pas")
        except requests.exceptions.HTTPError as e:
            print("Erreur HTTP :", e)
        except requests.exceptions.ConnectionError:
            print("Pas de connexion réseau")
        return None

    def temperature(self, lat: float, lon: float) -> float | None:
        """Température actuelle en °C."""
        donnees = self._appeler(
            {"latitude": lat, "longitude": lon, "current": "temperature_2m"}
        )
        if donnees is None:
            return None
        return donnees["current"]["temperature_2m"]

    def previsions(self, lat: float, lon: float, jours: int = 3) -> list[dict]:
        """Températures min et max pour les prochains jours."""
        donnees = self._appeler(
            {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_min,temperature_2m_max",
                "forecast_days": jours,
                "timezone": "Europe/Paris",
            }
        )
        if donnees is None:
            return []
        daily = donnees["daily"]
        return [
            {"date": d, "min": tmin, "max": tmax}
            for d, tmin, tmax in zip(
                daily["time"], daily["temperature_2m_min"], daily["temperature_2m_max"]
            )
        ]