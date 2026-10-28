"""Le compagnon data : un agent Gemini branché sur le modèle sémantique."""

import datetime
import os

from google import genai
from google.genai import types

from src.agent.outils import OutilsVentes

INSTRUCTIONS = """Tu es le compagnon data des équipes commerciales. Tu réponds en français,
de façon concise, aux questions sur les ventes.

Règles :
1. Les champs disponibles sont listés à la fin de ces instructions : utilise uniquement ces noms exacts.
2. Chaque chiffre de ta réponse doit venir d'un appel à interroger_ventes. N'invente jamais un chiffre.
3. Pour le chiffre d'affaires ou les ventes, utilise par défaut order_items.ca_net (CA net).
4. Si un outil renvoie une erreur, lis-la, corrige ta requête et réessaie (au plus deux fois).
5. Si la question sort du périmètre des ventes, ou si aucun champ ne permet d'y répondre,
   dis-le clairement au lieu de deviner.
6. Indique toujours la période et les filtres utilisés. Formate les montants en euros
   (ex. 153 192 €) et les taux en pourcentage.
Nous sommes le {date_du_jour}."""


def creer_client() -> genai.Client:
    """Gemini via une clé AI Studio (GEMINI_API_KEY) ou via Vertex AI.

    En cas de saturation (429) ou d'indisponibilité (503), le SDK réessaie
    jusqu'à 5 fois, en attendant de plus en plus longtemps entre deux essais.
    """
    return genai.Client(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2.0,
                max_delay=30.0,
                http_status_codes=[429, 500, 503, 504],
            )
        )
    )
# def creer_client() -> genai.Client:
#     """Gemini via une clé AI Studio (GEMINI_API_KEY) ou via Vertex AI.

#     Vertex AI : mettre GOOGLE_GENAI_USE_VERTEXAI=true, GOOGLE_CLOUD_PROJECT et
#     GOOGLE_CLOUD_LOCATION dans le .env ; l'authentification utilise alors l'ADC du jour 4.
#     """
#     return genai.Client()

def creer_chat(outils: OutilsVentes, modele: str | None = None):
    """Renvoie (client, chat). Le catalogue des champs est injecté dans les instructions :
    l'agent le connaît dès le départ, sans avoir à appeler lister_champs."""
    client = creer_client()
    catalogue = outils.sem.lister_champs("ventes_ia")
    lignes = [f"- {c['name']} ({c['categorie']}) : {c['label']}. {c['description']}" for c in catalogue]
    instructions = (
        INSTRUCTIONS.format(date_du_jour=datetime.date.today().isoformat())
        + "\n\nChamps disponibles (noms exacts à utiliser) :\n" + "\n".join(lignes)
    )
    config = types.GenerateContentConfig(
        system_instruction=instructions,
        tools=[outils.interroger_ventes],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=8),
        temperature=0.1,
    )
    chat = client.chats.create(model=modele or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), config=config)
    return client, chat

# def creer_chat(outils: OutilsVentes, modele: str | None = None):
#     """Une conversation avec mémoire : chaque message tient compte des précédents.

#     Renvoie (client, chat) : il faut garder le client en vie aussi longtemps que le chat,
#     sinon Python le supprime et ferme sa connexion réseau.
#     """
#     client = creer_client()
#     config = types.GenerateContentConfig(
#         system_instruction=INSTRUCTIONS.format(date_du_jour=datetime.date.today().isoformat()),
#         tools=[outils.lister_champs, outils.interroger_ventes],
#         automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=8),
#         temperature=0.1,
#     )
#     chat = client.chats.create(model=modele or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), config=config)
#     return client, chat

# def creer_chat(outils: OutilsVentes, modele: str | None = None):
#     """Une conversation avec mémoire : chaque message tient compte des précédents."""
#     client = creer_client()
#     config = types.GenerateContentConfig(
#         system_instruction=INSTRUCTIONS.format(date_du_jour=datetime.date.today().isoformat()),
#         tools=[outils.lister_champs, outils.interroger_ventes],
#         automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=8),
#         temperature=0.1,
#     )
#     return client.chats.create(model=modele or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), config=config)
