"""Validateur LookML local : remplace le bouton « Validate LookML » quand on n'a pas d'instance Looker.

Ce qu'il vérifie :
  - la syntaxe de chaque fichier .lkml ;
  - les constantes @{...} déclarées dans le manifest ;
  - les références ${champ} et ${vue.champ} ;
  - les clés primaires, les jointures (sql_on, relationship) et les champs d'un explore ;
  - les refinements (view: +nom) ;
  - avec --bigquery : que les tables et les colonnes ${TABLE}.colonne existent vraiment.

Usage, depuis la racine du repo :
    python scripts/valider_lookml.py
    python scripts/valider_lookml.py --bigquery
Code retour 1 s'il y a au moins une erreur (utile en CI au jour 8).
"""

import argparse
import glob
import re
import sys
from pathlib import Path

import lkml

REF = re.compile(r"\$\{([^}]+)\}")
CONST = re.compile(r"@\{([^}]+)\}")
COLONNE = re.compile(r"\$\{TABLE\}\.(\w+)")
TYPES_SANS_SQL = {"count"}


class Rapport:
    def __init__(self):
        self.erreurs, self.alertes = [], []

    def erreur(self, ou, msg):
        self.erreurs.append(f"[ERREUR] {ou} : {msg}")

    def alerte(self, ou, msg):
        self.alertes.append(f"[ALERTE] {ou} : {msg}")


# ---------------------------------------------------------------- lecture

def lire_projet(racine: Path, r: Rapport):
    """Lit tous les fichiers .lkml et renvoie (constantes, vues, raffinements, modèles)."""
    constantes, vues, raffinements, modeles = {}, {}, [], {}
    for chemin in sorted(racine.rglob("*.lkml")):
        rel = chemin.relative_to(racine).as_posix()
        try:
            contenu = lkml.load(chemin.read_text(encoding="utf-8"))
        except Exception as e:                      # erreur de syntaxe
            r.erreur(rel, f"syntaxe invalide ({e})")
            continue
        for c in contenu.get("constants", []):
            constantes[c["name"]] = c.get("value", "")
        for v in contenu.get("views", []):
            v["_fichier"] = rel
            if v["name"].startswith("+"):
                raffinements.append(v)
            elif v["name"] in vues:
                r.erreur(rel, f"vue '{v['name']}' définie deux fois")
            else:
                vues[v["name"]] = v
        if rel.endswith(".model.lkml") or contenu.get("explores"):
            modeles[rel] = contenu
    return constantes, vues, raffinements, modeles


def appliquer_raffinements(vues, raffinements, r: Rapport):
    """Fusionne view: +nom dans la vue d'origine (les attributs du raffinement l'emportent)."""
    for raf in raffinements:
        nom = raf["name"][1:]
        if nom not in vues:
            r.erreur(raf["_fichier"], f"raffinement de la vue inconnue '{nom}'")
            continue
        cible = vues[nom]
        for cle in ("dimensions", "measures", "dimension_groups"):
            existants = {c["name"]: c for c in cible.get(cle, [])}
            for champ in raf.get(cle, []):
                if champ["name"] in existants:
                    existants[champ["name"]].update(champ)
                else:
                    cible.setdefault(cle, []).append(champ)


def champs_de_vue(vue: dict) -> dict:
    """Renvoie {nom_du_champ: définition} en développant les dimension_group."""
    champs = {}
    for d in vue.get("dimensions", []):
        champs[d["name"]] = {**d, "_genre": "dimension"}
    for m in vue.get("measures", []):
        champs[m["name"]] = {**m, "_genre": "measure"}
    for g in vue.get("dimension_groups", []):
        if g.get("type") == "duration":
            for i in g.get("intervals", ["day"]):
                champs[f"{i}s_{g['name']}"] = {**g, "_genre": "dimension"}
        else:
            for t in g.get("timeframes", ["raw", "date"]):
                champs[f"{g['name']}_{t}"] = {**g, "_genre": "dimension"}
    return champs


def textes_sql(champ: dict) -> list[str]:
    return [champ[k] for k in ("sql", "sql_start", "sql_end") if k in champ]


# ---------------------------------------------------------------- contrôles

def verifier_vues(vues, constantes, r: Rapport) -> dict:
    """Contrôles internes à chaque vue. Renvoie {vue: {champ: def}}."""
    catalogue = {nom: champs_de_vue(v) for nom, v in vues.items()}
    for nom, v in vues.items():
        ou = f"{v['_fichier']} › {nom}"
        for c in CONST.findall(v.get("sql_table_name", "")):
            if c not in constantes:
                r.erreur(ou, f"constante @{{{c}}} absente du manifest")
        if "sql_table_name" not in v and "derived_table" not in v:
            r.erreur(ou, "ni sql_table_name ni derived_table")
        pk = [d["name"] for d in v.get("dimensions", []) if d.get("primary_key") == "yes"]
        if not pk:
            r.alerte(ou, "aucune primary_key : les mesures seront fausses après une jointure")
        elif len(pk) > 1:
            r.erreur(ou, f"plusieurs primary_key : {pk}")

        for champ_nom, champ in catalogue[nom].items():
            if champ["_genre"] == "measure" and champ.get("type", "count") not in TYPES_SANS_SQL \
                    and "sql" not in champ:
                r.erreur(f"{ou}.{champ_nom}", f"mesure de type {champ.get('type')} sans sql")
            for texte in textes_sql(champ):
                for ref in REF.findall(texte):
                    if ref == "TABLE":
                        continue
                    if "." in ref:
                        autre_vue, autre_champ = ref.split(".", 1)
                        if autre_vue not in catalogue:
                            r.erreur(f"{ou}.{champ_nom}", f"${{{ref}}} : vue '{autre_vue}' inconnue")
                        elif autre_champ not in catalogue[autre_vue]:
                            r.erreur(f"{ou}.{champ_nom}", f"${{{ref}}} : champ inconnu")
                    elif ref not in catalogue[nom]:
                        r.erreur(f"{ou}.{champ_nom}", f"${{{ref}}} : champ inconnu dans '{nom}'")
            # filtres de mesure : le parseur les range dans filters__all
            groupes = list(champ.get("filters__all", [])) + [champ.get("filters", []) or []]
            for groupe in groupes:
                for filtre in groupe:
                    for cle in (filtre if isinstance(filtre, dict) else {}):
                        v_f, _, c_f = cle.rpartition(".")
                        v_f = v_f or nom
                        if v_f not in catalogue or c_f not in catalogue[v_f]:
                            r.erreur(f"{ou}.{champ_nom}", f"filtre sur un champ inconnu '{cle}'")
    return catalogue


def vues_dependantes(vue: str, vues: dict) -> set[str]:
    """Vues référencées par ${autre_vue.champ} depuis une vue."""
    deps = set()
    for champ in champs_de_vue(vues[vue]).values():
        for texte in textes_sql(champ):
            for ref in REF.findall(texte):
                if "." in ref:
                    deps.add(ref.split(".", 1)[0])
    return deps - {vue}


def dependances(champ_complet: str, presentes: dict, catalogue: dict) -> set[str]:
    """Toutes les dépendances vue.champ d'un champ, en suivant les références en cascade."""
    vus, a_voir = set(), [champ_complet]
    while a_voir:
        courant = a_voir.pop()
        v, _, c = courant.partition(".")
        champ = catalogue.get(presentes.get(v, ""), {}).get(c, {})
        for texte in textes_sql(champ):
            for ref in REF.findall(texte):
                if ref == "TABLE":
                    continue
                complet = ref if "." in ref else f"{v}.{ref}"
                if complet not in vus:
                    vus.add(complet)
                    a_voir.append(complet)
    return vus - {champ_complet}


def verifier_explores(modeles, vues, catalogue, r: Rapport):
    explores_connus = {}
    for fichier, contenu in modeles.items():
        if fichier.endswith(".model.lkml") and "connection" not in contenu:
            r.erreur(fichier, "pas de 'connection'")
        for ex in contenu.get("explores", []):
            nom = ex["name"]
            ou = f"{fichier} › explore {nom}"
            if nom in explores_connus:
                r.erreur(ou, "explore défini deux fois")
            explores_connus[nom] = ex
            base = ex.get("from", ex.get("view_name", nom))
            alias = ex.get("view_name", nom)
            if base not in vues:
                r.erreur(ou, f"vue de base '{base}' inconnue")
                continue
            presentes = {alias: base}
            for j in ex.get("joins", []):
                jv = j.get("from", j["name"])
                if jv not in vues:
                    r.erreur(ou, f"jointure '{j['name']}' : vue inconnue")
                    continue
                presentes[j["name"]] = jv
                if "sql_on" not in j and "foreign_key" not in j and j.get("type") != "cross":
                    r.erreur(ou, f"jointure '{j['name']}' sans sql_on")
                if "relationship" not in j:
                    r.alerte(ou, f"jointure '{j['name']}' sans relationship (many_to_one par défaut)")
                for ref in REF.findall(j.get("sql_on", "")):
                    v, _, c = ref.partition(".")
                    if v not in presentes and v != j["name"]:
                        r.erreur(ou, f"sql_on de '{j['name']}' : ${{{ref}}} hors de l'explore")
                    elif c and c not in catalogue[presentes.get(v, jv)]:
                        r.erreur(ou, f"sql_on de '{j['name']}' : ${{{ref}}} champ inconnu")
            # une vue qui référence ${autre.champ} exige que 'autre' soit jointe
            for a, v in presentes.items():
                for dep in vues_dependantes(v, vues):
                    if dep not in presentes:
                        r.erreur(ou, f"la vue '{v}' référence '{dep}', qui n'est pas jointe")
            # champs déclarés dans fields: [...]
            for f in ex.get("fields", []):
                f = f.lstrip("-")
                if f in ("ALL_FIELDS*",) or f.endswith("*"):
                    continue
                v, _, c = f.partition(".")
                if v not in presentes:
                    r.erreur(ou, f"fields : vue '{v}' absente de l'explore")
                elif c not in catalogue[presentes[v]]:
                    r.erreur(ou, f"fields : champ '{f}' inconnu")
            # les champs exposés doivent avoir leurs dépendances (même indirectes) exposées
            if ex.get("fields"):
                exposes = {f for f in ex["fields"] if not f.startswith("-")}
                for f in sorted(exposes):
                    for dep in dependances(f, presentes, catalogue):
                        if dep not in exposes:
                            r.erreur(ou, f"fields : '{f}' dépend de '{dep}', non exposé")
        for t in contenu.get("tests", []):
            src = t.get("explore_source", {})
            if src.get("name") not in explores_connus:
                r.erreur(fichier, f"test '{t['name']}' : explore '{src.get('name')}' inconnu")
    return explores_connus


def verifier_bigquery(vues, constantes, r: Rapport):
    """Vérifie l'existence réelle des tables et colonnes dans BigQuery."""
    import os

    from dotenv import load_dotenv
    from google.cloud import bigquery

    load_dotenv()
    client = bigquery.Client(project=os.environ["GCP_PROJECT"])
    for nom, v in vues.items():
        table = v.get("sql_table_name", "")
        for c, val in constantes.items():
            table = table.replace(f"@{{{c}}}", val)
        table = table.strip().strip("`")
        if not table:
            continue
        try:
            colonnes = {s.name for s in client.get_table(table).schema}
        except Exception as e:
            r.erreur(f"{v['_fichier']} › {nom}", f"table '{table}' inaccessible ({type(e).__name__})")
            continue
        for champ_nom, champ in champs_de_vue(v).items():
            for texte in textes_sql(champ):
                for col in COLONNE.findall(texte):
                    if col not in colonnes:
                        r.erreur(f"{v['_fichier']} › {nom}.{champ_nom}",
                                 f"colonne '{col}' absente de {table}")


# ---------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dossier", default="lookml")
    parser.add_argument("--bigquery", action="store_true", help="vérifier tables et colonnes dans BigQuery")
    args = parser.parse_args()

    racine = Path(args.dossier)
    r = Rapport()
    constantes, vues, raffinements, modeles = lire_projet(racine, r)
    appliquer_raffinements(vues, raffinements, r)
    catalogue = verifier_vues(vues, constantes, r)
    explores = verifier_explores(modeles, vues, catalogue, r)
    if args.bigquery:
        verifier_bigquery(vues, constantes, r)

    print(f"Projet : {len(vues)} vues, {len(explores)} explores, "
          f"{sum(len(c) for c in catalogue.values())} champs, {len(constantes)} constantes")
    for ligne in r.alertes + r.erreurs:
        print(ligne)
    if r.erreurs:
        print(f"\nÉchec : {len(r.erreurs)} erreur(s), {len(r.alertes)} alerte(s)")
        return 1
    print(f"\nLookML valide ({len(r.alertes)} alerte(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
