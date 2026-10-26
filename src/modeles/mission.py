from dataclasses import dataclass

class Mission:
    """Une mission freelance."""

    def __init__(self, client: str, tjm: int, jours: int = 0):
        self.client = client
        self.tjm = tjm
        self.jours = jours

    def ca(self) -> int:
        """CA HT de la mission."""
        return self.tjm * self.jours

    def ca_annuel(self, jours_par_mois: int, mois: int = 11) -> int:
        """CA HT projeté sur une année."""
        return self.tjm * jours_par_mois * mois

    def __repr__(self) -> str:
        return f"Mission({self.client}, {self.tjm} €/j, {self.jours} j)"


@dataclass
class Consultant:
    nom: str
    missions: list

    def ca_total(self) -> int:
        """Somme du CA de toutes les missions."""
        return sum(m.ca() for m in self.missions)