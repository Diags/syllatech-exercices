"""Les 22 questions (banc et validation) à travers le service, contre le vrai Ollama.

    uv run python mesures/observer.py

Écrit mesures/traces.jsonl (une ligne par requête, telle que le service la
journalise) et mesures/observabilite.json (le résumé de /metriques).
L'index est construit avant, et sa durée comptée à part.
"""

import json
import pathlib
import sys
import time

import ollama
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from jobportal.api import creer_application  # noqa: E402
from jobportal.banc import CAS, CAS_VALIDATION  # noqa: E402
from jobportal.donnees import OFFRES  # noqa: E402
from jobportal.observabilite import Journal  # noqa: E402
from jobportal.recherche import Index  # noqa: E402

ICI = pathlib.Path(__file__).parent
sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    traces = ICI / "traces.jsonl"
    traces.unlink(missing_ok=True)
    client = ollama.Client()
    debut = time.perf_counter()
    index = Index(client, OFFRES)  # chronométré à part : il n'est construit qu'une fois
    index_s = round(time.perf_counter() - debut, 1)
    api = TestClient(creer_application(client, journal=Journal(traces), index_pret=index))
    for cas in CAS + CAS_VALIDATION:
        api.post("/question", json={"question": cas["question"]})
    resume = api.get("/metriques").json()
    lignes = [json.loads(l) for l in traces.read_text(encoding="utf-8").splitlines()]
    resume = {**resume, "construction_index_s": index_s, "requetes_journalisees": len(lignes)}
    (ICI / "observabilite.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1) + "\n",
                                            encoding="utf-8")
    print(json.dumps(resume, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
