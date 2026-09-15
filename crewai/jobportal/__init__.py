"""Le job portal, en equipes d'agents CrewAI.

CrewAI ecrit un fichier de preference de tracage au premier lancement et
affiche un cadre. On coupe telemetrie et tracage AVANT tout import du paquet,
pour que les chapitres restent lisibles et que rien ne parte sur le reseau.
"""

import os

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
