"""Mini moteur sémantique : lit un projet LookML et génère le SQL BigQuery d'une requête.

C'est une version pédagogique de ce que fait Looker quand on lance un explore :
    champs + filtres + tris  ->  LookML  ->  SQL  ->  BigQuery

Ce qui est géré :
    dimensions, dimension_group (time et duration), tier, yesno,
    mesures count, count_distinct, sum, average, min, max, number,
    mesures filtrées, jointures nécessaires uniquement, refinements,
    restriction fields: [...] d'un explore, filtres au format Looker.
Ce qui ne l'est pas (simplifications assumées) :
    symmetric aggregates (sommes sur une vue jointe en one_to_many),
    derived tables, liquid, fuseaux horaires.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import lkml

REF = re.compile(r"\$\{([^}]+)\}")
CONST = re.compile(r"@\{([^}]+)\}")
AGREGATS = {"sum": "SUM", "average": "AVG", "min": "MIN", "max": "MAX"}


@dataclass
class Requete:
    """Équivalent de models40.WriteQuery dans le looker-sdk."""

    explore: str
    fields: list[str]
    filters: dict[str, str] = field(default_factory=dict)
    sorts: list[str] = field(default_factory=list)
    limit: int = 500


class ErreurSemantique(ValueError):
    """Requête invalide au regard du modèle (champ inconnu, filtre illisible...)."""


class ModeleSemantique:
    def __init__(self, dossier: str = "lookml"):
        self.dossier = Path(dossier)
        self.constantes: dict[str, str] = {}
        self.vues: dict[str, dict] = {}
        self.explores: dict[str, dict] = {}
        self._charger()

    # ------------------------------------------------------------ chargement

    def _charger(self) -> None:
        raffinements = []
        for chemin in sorted(self.dossier.rglob("*.lkml")):
            contenu = lkml.load(chemin.read_text(encoding="utf-8"))
            for c in contenu.get("constants", []):
                self.constantes[c["name"]] = c.get("value", "")
            for v in contenu.get("views", []):
                if v["name"].startswith("+"):
                    raffinements.append(v)
                else:
                    self.vues[v["name"]] = v
            for e in contenu.get("explores", []):
                self.explores[e["name"]] = e
        for raf in raffinements:
            cible = self.vues[raf["name"][1:]]
            for cle in ("dimensions", "measures", "dimension_groups"):
                existants = {c["name"]: c for c in cible.get(cle, [])}
                for champ in raf.get(cle, []):
                    if champ["name"] in existants:
                        existants[champ["name"]].update(champ)
                    else:
                        cible.setdefault(cle, []).append(champ)
        self.champs = {nom: self._developper(v) for nom, v in self.vues.items()}

    @staticmethod
    def _developper(vue: dict) -> dict:
        """{nom: définition} avec les dimension_group développés en champs."""
        champs = {}
        for d in vue.get("dimensions", []):
            champs[d["name"]] = {**d, "_genre": "dimension"}
        for m in vue.get("measures", []):
            champs[m["name"]] = {**m, "_genre": "measure"}
        for g in vue.get("dimension_groups", []):
            if g.get("type") == "duration":
                for i in g.get("intervals", ["day"]):
                    champs[f"{i}s_{g['name']}"] = {**g, "_genre": "dimension", "_intervalle": i}
            else:
                for t in g.get("timeframes", ["raw", "date"]):
                    champs[f"{g['name']}_{t}"] = {**g, "_genre": "dimension", "_periode": t,
                                                   "_groupe": g["name"]}
        return champs

    # ------------------------------------------------------------ catalogue

    def _alias_explore(self, explore: str) -> dict[str, str]:
        """{alias dans la requête: nom de la vue}."""
        if explore not in self.explores:
            raise ErreurSemantique(f"explore '{explore}' inconnu ({list(self.explores)})")
        ex = self.explores[explore]
        alias = {ex.get("view_name", explore): ex.get("from", ex.get("view_name", explore))}
        for j in ex.get("joins", []):
            alias[j["name"]] = j.get("from", j["name"])
        return alias

    def lister_champs(self, explore: str, inclure_caches: bool = False) -> list[dict]:
        """Champs utilisables dans un explore, avec leurs métadonnées (ce que lira l'agent)."""
        alias = self._alias_explore(explore)
        autorises = self._champs_autorises(explore)
        resultat = []
        for a, vue in alias.items():
            for nom, c in self.champs[vue].items():
                complet = f"{a}.{nom}"
                if autorises is not None and complet not in autorises:
                    continue
                if c.get("hidden") == "yes" and not inclure_caches:
                    continue
                label = c.get("label", nom.replace("_", " ").capitalize())
                if "_periode" in c:
                    label = f"{label} ({c['_periode']})"
                resultat.append({
                    "name": complet,
                    "categorie": c["_genre"],
                    "type": c.get("type", "string"),
                    "label": label,
                    "description": c.get("description", ""),
                })
        return resultat

    def _champs_autorises(self, explore: str) -> set[str] | None:
        champs = self.explores[explore].get("fields")
        return {f for f in champs if not f.startswith("-")} if champs else None

    def _trouver(self, explore: str, complet: str) -> tuple[str, str, dict]:
        alias = self._alias_explore(explore)
        a, _, nom = complet.partition(".")
        if a not in alias or nom not in self.champs[alias[a]]:
            raise ErreurSemantique(f"champ '{complet}' inconnu dans l'explore '{explore}'")
        autorises = self._champs_autorises(explore)
        if autorises is not None and complet not in autorises:
            raise ErreurSemantique(f"champ '{complet}' non exposé dans l'explore '{explore}'")
        return a, nom, self.champs[alias[a]][nom]

    # ------------------------------------------------------------ SQL des champs

    def _sql_dimension(self, explore, alias_vue, nom, vues_utilisees) -> str:
        vue = self._alias_explore(explore)[alias_vue]
        c = self.champs[vue][nom]
        vues_utilisees.add(alias_vue)
        if "_intervalle" in c:
            debut = self._remplacer(explore, alias_vue, c["sql_start"], vues_utilisees, False)
            fin = self._remplacer(explore, alias_vue, c["sql_end"], vues_utilisees, False)
            if c["_intervalle"] == "day":
                return f"DATE_DIFF(DATE({fin}), DATE({debut}), DAY)"
            return f"TIMESTAMP_DIFF({fin}, {debut}, {c['_intervalle'].upper()})"
        base = self._remplacer(explore, alias_vue, c.get("sql", f"${{TABLE}}.{nom}"),
                               vues_utilisees, False)
        if "_periode" in c:
            return {
                "raw": base, "time": base,
                "date": f"DATE({base})",
                "week": f"DATE_TRUNC(DATE({base}), WEEK(MONDAY))",
                "month": f"FORMAT_DATE('%Y-%m', DATE({base}))",
                "quarter": f"FORMAT_DATE('%Y-Q%Q', DATE({base}))",
                "year": f"EXTRACT(YEAR FROM {base})",
            }.get(c["_periode"], base)
        if c.get("type") == "tier":
            return self._sql_tier(base, [float(t) for t in c.get("tiers", [])])
        if c.get("type") == "yesno":
            return f"CASE WHEN {base} THEN 'Yes' ELSE 'No' END"
        return base

    @staticmethod
    def _sql_tier(base: str, tiers: list[float]) -> str:
        fmt = lambda x: str(int(x)) if x == int(x) else str(x)  # noqa: E731
        cas = [f"WHEN {base} < {fmt(tiers[0])} THEN 'Below {fmt(tiers[0])}'"]
        for bas, haut in zip(tiers, tiers[1:]):
            cas.append(f"WHEN {base} < {fmt(haut)} THEN '{fmt(bas)} to {fmt(haut - 1)}'")
        cas.append(f"WHEN {base} >= {fmt(tiers[-1])} THEN '{fmt(tiers[-1])} or Above'")
        return "CASE " + " ".join(cas) + " ELSE 'Undefined' END"

    def _sql_mesure(self, explore, alias_vue, nom, vues_utilisees, params) -> str:
        vue = self._alias_explore(explore)[alias_vue]
        c = self.champs[vue][nom]
        vues_utilisees.add(alias_vue)
        type_ = c.get("type", "count")
        if type_ == "number":
            return "(" + self._remplacer(explore, alias_vue, c["sql"], vues_utilisees, True, params) + ")"

        # condition issue des filtres de la mesure
        conditions = []
        for groupe in c.get("filters__all", []) + [c.get("filters", [])]:
            for filtre in groupe or []:
                for champ_f, valeur in filtre.items():
                    a_f, n_f = (champ_f.split(".", 1) if "." in champ_f else (alias_vue, champ_f))
                    conditions.append(self._condition(explore, f"{a_f}.{n_f}", valeur,
                                                      vues_utilisees, params, interne=True))
        cond = " AND ".join(conditions)

        if type_ in ("count", "count_distinct"):
            if type_ == "count":
                cle = self._cle_primaire(explore, alias_vue, vues_utilisees)
            else:
                cle = self._remplacer(explore, alias_vue, c["sql"], vues_utilisees, False)
            expr = f"CASE WHEN {cond} THEN {cle} END" if cond else cle
            return f"COUNT(DISTINCT {expr})"
        if type_ in AGREGATS:
            sql = self._remplacer(explore, alias_vue, c["sql"], vues_utilisees, False)
            expr = f"CASE WHEN {cond} THEN {sql} END" if cond else sql
            return f"{AGREGATS[type_]}({expr})"
        raise ErreurSemantique(f"type de mesure '{type_}' non géré ({alias_vue}.{nom})")

    def _cle_primaire(self, explore, alias_vue, vues_utilisees) -> str:
        vue = self._alias_explore(explore)[alias_vue]
        for nom, c in self.champs[vue].items():
            if c.get("primary_key") == "yes":
                return self._sql_dimension(explore, alias_vue, nom, vues_utilisees)
        return "*"

    def _remplacer(self, explore, alias_vue, sql, vues_utilisees, mesures, params=None) -> str:
        """Remplace ${TABLE}, ${champ} et ${vue.champ} par leur SQL, récursivement."""
        alias = self._alias_explore(explore)

        def remplacement(m):
            ref = m.group(1)
            if ref == "TABLE":
                vues_utilisees.add(alias_vue)
                return alias_vue
            a, _, nom = ref.partition(".") if "." in ref else (alias_vue, "", ref)
            if a not in alias or nom not in self.champs[alias[a]]:
                raise ErreurSemantique(f"référence ${{{ref}}} introuvable")
            c = self.champs[alias[a]][nom]
            if c["_genre"] == "measure":
                if not mesures:
                    raise ErreurSemantique(f"mesure ${{{ref}}} utilisée dans une dimension")
                return self._sql_mesure(explore, a, nom, vues_utilisees, params)
            return f"({self._sql_dimension(explore, a, nom, vues_utilisees)})"

        return REF.sub(remplacement, sql)

    # ------------------------------------------------------------ filtres Looker

    def _condition(self, explore, complet, expression, vues_utilisees, params, interne=False) -> str:
        """Traduit un filtre Looker ("-Cancelled,-Returned", ">100", "last month"...) en SQL."""
        if interne:
            alias = self._alias_explore(explore)
            a, _, nom = complet.partition(".")
            c = self.champs[alias[a]][nom]
        else:
            a, nom, c = self._trouver(explore, complet)

        if "_periode" in c:                                   # champ de date
            groupe = c["_groupe"]
            brut = self._sql_dimension(explore, a, f"{groupe}_raw", vues_utilisees) \
                if f"{groupe}_raw" in self.champs[self._alias_explore(explore)[a]] \
                else self._remplacer(explore, a, c["sql"], vues_utilisees, False)
            return self._condition_date(f"DATE({brut})", expression.strip(), params)

        sql = self._sql_dimension(explore, a, nom, vues_utilisees)
        if c.get("type") == "yesno":
            v = expression.strip().lower()
            if v not in ("yes", "no"):
                raise ErreurSemantique(f"filtre yesno attendu 'yes' ou 'no' : {expression}")
            return f"({sql}) = '{'Yes' if v == 'yes' else 'No'}'"
        if c.get("type") == "number" and c["_genre"] == "dimension":
            return self._condition_nombre(sql, expression, params)
        return self._condition_texte(sql, expression, params)

    @staticmethod
    def _param(params, valeur, type_bq) -> str:
        nom = f"p{len(params)}"
        params.append((nom, type_bq, valeur))
        return f"@{nom}"

    def _condition_texte(self, sql, expression, params) -> str:
        inclus, exclus, conds = [], [], []
        for brut in [x.strip() for x in expression.split(",") if x.strip()]:
            negatif = brut.startswith("-")
            v = brut[1:] if negatif else brut
            if v.upper() == "NULL":
                conds.append(f"{sql} IS {'NOT ' if negatif else ''}NULL")
            elif "%" in v:
                conds.append(f"{sql} {'NOT ' if negatif else ''}LIKE {self._param(params, v, 'STRING')}")
            else:
                (exclus if negatif else inclus).append(self._param(params, v, "STRING"))
        if inclus:
            conds.append(f"{sql} IN ({', '.join(inclus)})")
        if exclus:
            conds.append(f"({sql} NOT IN ({', '.join(exclus)}) OR {sql} IS NULL)")
        return "(" + " AND ".join(conds) + ")"

    def _condition_nombre(self, sql, expression, params) -> str:
        e = expression.replace(" ", "")
        m = re.fullmatch(r"(>=|<=|>|<|!=|=)?(-?\d+(?:\.\d+)?)", e)
        if m:
            return f"{sql} {m.group(1) or '='} {self._param(params, float(m.group(2)), 'FLOAT64')}"
        if re.fullmatch(r"-?\d+(\.\d+)?(,-?\d+(\.\d+)?)+", e):
            vals = [self._param(params, float(x), "FLOAT64") for x in e.split(",")]
            return f"{sql} IN ({', '.join(vals)})"
        if e.upper() in ("NULL", "-NULL"):
            return f"{sql} IS {'NOT ' if e.startswith('-') else ''}NULL"
        raise ErreurSemantique(f"filtre numérique illisible : '{expression}'")

    def _condition_date(self, sql_date, e, params) -> str:
        """Intervalle [début, fin[ à partir de l'expression Looker."""
        bas = e.lower()
        aujourdhui = "CURRENT_DATE()"
        relatifs = {
            "today": (aujourdhui, f"DATE_ADD({aujourdhui}, INTERVAL 1 DAY)"),
            "yesterday": (f"DATE_SUB({aujourdhui}, INTERVAL 1 DAY)", aujourdhui),
            "this week": (f"DATE_TRUNC({aujourdhui}, WEEK(MONDAY))",
                          f"DATE_ADD(DATE_TRUNC({aujourdhui}, WEEK(MONDAY)), INTERVAL 1 WEEK)"),
            "this month": (f"DATE_TRUNC({aujourdhui}, MONTH)",
                           f"DATE_ADD(DATE_TRUNC({aujourdhui}, MONTH), INTERVAL 1 MONTH)"),
            "last month": (f"DATE_SUB(DATE_TRUNC({aujourdhui}, MONTH), INTERVAL 1 MONTH)",
                           f"DATE_TRUNC({aujourdhui}, MONTH)"),
            "this year": (f"DATE_TRUNC({aujourdhui}, YEAR)",
                          f"DATE_ADD(DATE_TRUNC({aujourdhui}, YEAR), INTERVAL 1 YEAR)"),
            "last year": (f"DATE_SUB(DATE_TRUNC({aujourdhui}, YEAR), INTERVAL 1 YEAR)",
                          f"DATE_TRUNC({aujourdhui}, YEAR)"),
        }
        if bas in relatifs:
            debut, fin = relatifs[bas]
        elif m := re.fullmatch(r"(?:last )?(\d+) (day|week|month|year)s?", bas):
            n, u = m.groups()
            debut = f"DATE_SUB({aujourdhui}, INTERVAL {int(n)} {u.upper()})"
            fin = f"DATE_ADD({aujourdhui}, INTERVAL 1 DAY)"
        elif re.fullmatch(r"\d{4}", e):
            p = self._param(params, f"{e}-01-01", "DATE")
            debut, fin = p, f"DATE_ADD({p}, INTERVAL 1 YEAR)"
        elif re.fullmatch(r"\d{4}-\d{2}", e):
            p = self._param(params, f"{e}-01", "DATE")
            debut, fin = p, f"DATE_ADD({p}, INTERVAL 1 MONTH)"
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", e):
            p = self._param(params, e, "DATE")
            debut, fin = p, f"DATE_ADD({p}, INTERVAL 1 DAY)"
        elif m := re.fullmatch(r"(\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})", bas):
            debut = self._param(params, m.group(1), "DATE")
            fin = self._param(params, m.group(2), "DATE")
        elif m := re.fullmatch(r"(after|before) (\d{4}-\d{2}-\d{2})", bas):
            p = self._param(params, m.group(2), "DATE")
            return f"{sql_date} >= {p}" if m.group(1) == "after" else f"{sql_date} < {p}"
        else:
            raise ErreurSemantique(
                f"filtre de date illisible : '{e}' (ex. 2025, 2025-03, last month, 30 days, "
                "2025-01-01 to 2025-06-30)")
        return f"({sql_date} >= {debut} AND {sql_date} < {fin})"

    # ------------------------------------------------------------ génération

    def generer_sql(self, q: Requete, autoriser_caches: bool = False) -> tuple[str, list[tuple]]:
        """Renvoie (sql, params) ; params = [(nom, type BigQuery, valeur), ...].

        Par défaut, les champs hidden: yes sont refusés : un agent ne doit utiliser
        que ce qu'il voit dans lister_champs().
        """
        if not autoriser_caches:
            for f in list(q.fields) + list(q.filters):
                if self._trouver(q.explore, f)[2].get("hidden") == "yes":
                    raise ErreurSemantique(f"champ '{f}' masqué (hidden: yes)")
        if not q.fields:
            raise ErreurSemantique("aucun champ demandé")
        if q.limit > 5000:
            raise ErreurSemantique("limit trop élevé (max 5000)")
        ex = self.explores.get(q.explore) or {}
        alias = self._alias_explore(q.explore)
        vues_utilisees: set[str] = set()
        params: list[tuple] = []

        selects, dims, mesures = [], [], []
        for f in q.fields:
            a, nom, c = self._trouver(q.explore, f)
            col = f.replace(".", "__")
            if c["_genre"] == "dimension":
                sql = self._sql_dimension(q.explore, a, nom, vues_utilisees)
                dims.append(col)
            else:
                sql = self._sql_mesure(q.explore, a, nom, vues_utilisees, params)
                mesures.append(col)
            selects.append(f"  {sql} AS {col}")

        where, having = [], []
        for f, expression in q.filters.items():
            _, _, c = self._trouver(q.explore, f)
            if c["_genre"] == "measure":
                a, nom, _ = self._trouver(q.explore, f)
                sql_m = self._sql_mesure(q.explore, a, nom, vues_utilisees, params)
                having.append(self._condition_nombre(sql_m, expression, params))
            else:
                where.append(self._condition(q.explore, f, expression, vues_utilisees, params))

        # jointures : seulement celles nécessaires, en suivant les sql_on
        base = ex.get("view_name", q.explore)
        joins_sql, a_joindre = [], set(vues_utilisees) - {base}
        changement = True
        while changement:
            changement = False
            for j in ex.get("joins", []):
                if j["name"] in a_joindre:
                    for ref in REF.findall(j.get("sql_on", "")):
                        autre = ref.split(".", 1)[0]
                        if autre != base and autre not in a_joindre:
                            a_joindre.add(autre)
                            changement = True
        for j in ex.get("joins", []):
            if j["name"] in a_joindre:
                on = self._remplacer(q.explore, j["name"], j["sql_on"], set(), False)
                type_join = j.get("type", "left_outer").replace("_outer", "").upper()
                joins_sql.append(f"{type_join} JOIN {self._table(alias[j['name']])} AS {j['name']}\n  ON {on}")

        sql = "SELECT\n" + ",\n".join(selects)
        sql += f"\nFROM {self._table(alias[base])} AS {base}"
        if joins_sql:
            sql += "\n" + "\n".join(joins_sql)
        if where:
            sql += "\nWHERE " + "\n  AND ".join(where)
        if dims and mesures:
            sql += "\nGROUP BY " + ", ".join(str(i + 1) for i, f in enumerate(q.fields)
                                             if f.replace(".", "__") in dims)
        elif dims:
            sql += "\nGROUP BY " + ", ".join(str(i + 1) for i in range(len(dims)))
        if having:
            sql += "\nHAVING " + " AND ".join(having)

        tris = []
        for s in q.sorts:
            champ, _, sens = s.partition(" ")
            if champ not in q.fields:
                raise ErreurSemantique(f"tri sur '{champ}', absent des champs demandés")
            tris.append(f"{champ.replace('.', '__')} {'DESC' if sens.lower() == 'desc' else 'ASC'}")
        if not tris:
            tris = [f"{mesures[0]} DESC"] if mesures else [f"{dims[0]} ASC"]
        sql += "\nORDER BY " + ", ".join(tris)
        sql += f"\nLIMIT {int(q.limit)}"
        return sql, params

    def _table(self, vue: str) -> str:
        nom = self.vues[vue].get("sql_table_name", vue)
        for c, val in self.constantes.items():
            nom = nom.replace(f"@{{{c}}}", val)
        return nom.strip()
