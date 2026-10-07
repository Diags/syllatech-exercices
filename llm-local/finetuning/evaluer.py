"""Le modèle de base, puis le même avec l'adaptateur LoRA, sur le banc de 12 annonces.

    uv run --extra finetune python finetuning/evaluer.py

Même consigne, même décodage glouton (déterministe) dans les deux cas : seule
change la présence de l'adaptateur. Le banc n'a servi à rien pendant
l'entraînement (voir donnees_entrainement.verifier_separation). Écrit
finetuning/resultats.json.
"""

import json
import pathlib
import re
import sys
import time

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from donnees_entrainement import CONSIGNE_JSON  # noqa: E402
from entrainer import BASE, SORTIE  # noqa: E402

from jobportal.donnees import ANNONCES, CHAMPS  # noqa: E402
from jobportal.fiche import champs_justes  # noqa: E402

RESULTATS = pathlib.Path(__file__).with_name("resultats.json")

sys.stdout.reconfigure(encoding="utf-8")


def lire_json(texte: str):
    """Le premier objet JSON du texte, ou None s'il n'y en a pas de valide."""
    trouve = re.search(r"\{.*?\}", texte, re.S)
    try:
        return json.loads(trouve.group(0)) if trouve else None
    except json.JSONDecodeError:
        return None


def evaluer(modele, tokenizer, etiquette: str) -> dict:
    print(f"\n{etiquette}")
    justes, invalides, details, debut = 0, 0, [], time.perf_counter()
    for annonce in ANNONCES:
        conversation = [{"role": "system", "content": CONSIGNE_JSON}, {"role": "user", "content": annonce["texte"]}]
        texte = tokenizer.apply_chat_template(conversation, tokenize=False, add_generation_prompt=True)
        entree = tokenizer(texte, return_tensors="pt", add_special_tokens=False)
        with torch.no_grad():
            sortie = modele.generate(**entree, max_new_tokens=80, do_sample=False)
        reponse = tokenizer.decode(sortie[0, entree["input_ids"].shape[1]:], skip_special_tokens=True)
        fiche = lire_json(reponse)
        n = champs_justes(fiche, annonce["attendu"]) if isinstance(fiche, dict) else 0
        invalides += not isinstance(fiche, dict)
        justes += n
        details.append({"reponse": reponse, "justes": n})
        print(f"   {n}/5  {reponse[:110]!r}")
    resultat = {"champs_justes": justes, "champs_total": len(ANNONCES) * len(CHAMPS),
                "json_invalides": invalides,
                "secondes_par_annonce": round((time.perf_counter() - debut) / len(ANNONCES), 2),
                "detail": details}
    print(f"   → {justes}/{resultat['champs_total']} champs justes, {invalides} JSON invalide(s)")
    return resultat


def main() -> int:
    if not (SORTIE / "adapter_config.json").exists():
        print("Pas d'adaptateur : lancez d'abord finetuning/entrainer.py")
        return 1
    tokenizer = AutoTokenizer.from_pretrained(BASE)
    base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float32).eval()
    resultats = {"avant": evaluer(base, tokenizer, f"{BASE}, sans adaptateur")}
    adapte = PeftModel.from_pretrained(base, SORTIE).eval()
    resultats["apres"] = evaluer(adapte, tokenizer, f"{BASE} + adaptateur LoRA")
    RESULTATS.write_text(json.dumps(resultats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nécrit : {RESULTATS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
