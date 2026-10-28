"""Jour 7 : discuter avec le compagnon data.

    python agent_jour7.py            # conversation dans le terminal
    python agent_jour7.py --eval     # rejoue les questions de test
"""

import os
import sys
from google.genai import errors

from dotenv import load_dotenv

from src.agent.compagnon import creer_chat
from src.agent.outils import OutilsVentes
from src.clients.bigquery_client import ClientBigQuery
from src.semantique.client import ClientSemantique

QUESTIONS_TEST = [
    "Quel est le CA net des parfums en France en 2025 ?",
    "Quelles sont les 3 catégories avec le meilleur taux de marge depuis le début de l'année ?",
    "Comment a évolué le CA net mois par mois sur les 6 derniers mois ?",
    "Quel est le panier moyen des 25-34 ans par pays en 2025 ?",
    "Et pour les 35-44 ans ?",                       # teste la mémoire de la conversation
    "Quelle est la météo à Paris demain ?",          # hors périmètre : doit refuser
]

def preparer():
    load_dotenv()
    bq = ClientBigQuery(os.environ["GCP_PROJECT"], max_go=1.0)
    outils = OutilsVentes(ClientSemantique(bq, dossier_lookml="lookml"))
    client, chat = creer_chat(outils)
    return outils, client, chat

# def preparer():
#     load_dotenv()
#     bq = ClientBigQuery(os.environ["GCP_PROJECT"], max_go=1.0)
#     outils = OutilsVentes(ClientSemantique(bq, dossier_lookml="lookml"))
#     return outils, creer_chat(outils)


def poser(chat, question: str) -> None:
    print(f"\nVous : {question}")
    try:
        reponse = chat.send_message(question)
        print(f"Compagnon : {reponse.text}")
    except errors.ServerError:
        print("Compagnon : le service Gemini est saturé, réessayez dans une minute.")
    except errors.ClientError as e:
        print(f"Compagnon : requête refusée par Gemini ({e.code}).")
    # reponse = chat.send_message(question)
    # print(f"Compagnon : {reponse.text}")


if __name__ == "__main__":
    outils, client, chat = preparer()
    if "--eval" in sys.argv:
        for q in QUESTIONS_TEST:
            poser(chat, q)
        print(f"\n{len(outils.journal)} appels d'outils au total.")
    else:
        print("Compagnon data prêt. Tapez 'quit' pour sortir.")
        while True:
            question = input("\nVous : ").strip()
            if question.lower() in {"quit", "exit", "q"}:
                break
            if question:
                reponse = chat.send_message(question)
                print(f"Compagnon : {reponse.text}")
