"""Le modèle fine-tuné, servi par Ollama, et comparé dans les mêmes conditions.

    uv run --extra finetune python finetuning/vers_ollama.py

1. fusionne l'adaptateur LoRA dans le modèle de base (finetuning/fusionne/),
   et écrit à côté le modèle de base seul (finetuning/base-hf/) ;
2. les convertit en GGUF, en f16 et en q8_0, avec le convertisseur de
   llama.cpp, puis les importe dans Ollama PAR LE MÊME CHEMIN, avec le gabarit
   de conversation du Qwen2.5 d'origine ;
3. les évalue avec le banc et le schéma JSON du chapitre 4, plus le 0,5B q4_K_M
   de la bibliothèque Ollama comme repère. Écrit finetuning/ollama.json.

Pourquoi l'étape 3 : evaluer.py compare le modèle avant et après dans
transformers, en fp32 et sans schéma. Ce n'est pas comparable aux modèles du
chapitre 4, servis par Ollama, quantizés et contraints par un schéma. Ici, si.

Mesuré avec Ollama 0.35 : un dossier Hugging Face (safetensors) passe par le
moteur MLX d'Ollama, qui refuse Qwen2 (« unsupported MLX architecture »), avec
ou sans --quantize ; et --quantize n'y accepte pas q4_K_M (« supported types
are int4, int8, nvfp4, mxfp4, mxfp8 »). Le format GGUF, lui, s'importe — mais
déjà quantizé : « create-time quantization is only supported for safetensors
imports; quantize GGUF models before importing ». Le convertisseur Python de
llama.cpp produit du q8_0 ; un q4_K_M demanderait son outil compilé,
llama-quantize. D'où f16 et q8_0 ici.

Il faut une copie de llama.cpp, à un chemin COURT (Windows coupe à 260
caractères, et le dépôt a des chemins longs) :
    git clone --depth 1 https://github.com/ggml-org/llama.cpp C:/lcpp
Le script la cherche dans la variable LLAMA_CPP, sinon dans C:/lcpp.
⚠️ Ajoute à votre Ollama cinq modèles (de 400 Mo à 1 Go). Pour les retirer :
ollama rm qwen2.5:0.5b-instruct-q4_K_M qwen2.5-base:0.5b-f16 qwen2.5-base:0.5b-q8_0
ollama rm qwen2.5-fiches:0.5b-f16 qwen2.5-fiches:0.5b-q8_0
"""

import json
import os
import pathlib
import subprocess
import sys

import ollama
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from donnees_entrainement import CONSIGNE_JSON  # noqa: E402
from entrainer import BASE, SORTIE  # noqa: E402

from jobportal.donnees import ANNONCES, CHAMPS  # noqa: E402
from jobportal.fiche import CONSIGNE, SCHEMA_FICHE, champs_justes  # noqa: E402

# Le modèle fine-tuné a appris avec CONSIGNE_JSON ; le cours extrait avec CONSIGNE.
CONSIGNES = {"consigne_du_cours": CONSIGNE, "consigne_d_entrainement": CONSIGNE_JSON}

BASE_OLLAMA = "qwen2.5:0.5b-instruct-q4_K_M"
REFERENCE = "qwen2.5:1.5b-instruct-q4_K_M"  # le modèle des chapitres 3 et 4
PASSAGES = 2  # température 0 et graine fixe ne garantissent pas un résultat identique : on le vérifie
IMPORTS = {"qwen2.5-base:0.5b": pathlib.Path(__file__).with_name("base-hf"),
           "qwen2.5-fiches:0.5b": pathlib.Path(__file__).with_name("fusionne")}
RESULTATS = pathlib.Path(__file__).with_name("ollama.json")
LLAMA_CPP = pathlib.Path(os.environ.get("LLAMA_CPP", "C:/lcpp"))

sys.stdout.reconfigure(encoding="utf-8")


def en_gguf(dossier: pathlib.Path, format_: str) -> pathlib.Path:
    """Le convertisseur officiel de llama.cpp : safetensors → un fichier GGUF (f16 ou q8_0)."""
    sortie = dossier / f"modele-{format_}.gguf"
    env = {**os.environ, "PYTHONPATH": str(LLAMA_CPP / "gguf-py")}
    subprocess.run([sys.executable, str(LLAMA_CPP / "convert_hf_to_gguf.py"), str(dossier),
                    "--outtype", format_, "--outfile", str(sortie)], check=True, env=env,
                   stdout=subprocess.DEVNULL)
    return sortie


def ecrire_modeles() -> None:
    tokenizer = AutoTokenizer.from_pretrained(BASE)
    base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float16)
    base.save_pretrained(IMPORTS["qwen2.5-base:0.5b"])
    tokenizer.save_pretrained(IMPORTS["qwen2.5-base:0.5b"])
    fusion = PeftModel.from_pretrained(base, SORTIE).merge_and_unload()
    fusion.save_pretrained(IMPORTS["qwen2.5-fiches:0.5b"])
    tokenizer.save_pretrained(IMPORTS["qwen2.5-fiches:0.5b"])


def importer(client: ollama.Client, nom: str, dossier: pathlib.Path) -> list[str]:
    """Le même modèle en deux GGUF, f16 et q8_0, importés tels quels dans Ollama."""
    gabarit = client.show(BASE_OLLAMA).template  # le gabarit de conversation de Qwen2.5
    importes = []
    for format_ in ("f16", "q8_0"):
        modelfile = dossier / f"Modelfile.{format_}"
        modelfile.write_text(f'FROM {en_gguf(dossier, format_)}\nTEMPLATE """{gabarit}"""\n',
                             encoding="utf-8")
        subprocess.run(["ollama", "create", f"{nom}-{format_}", "-f", str(modelfile)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        importes.append(f"{nom}-{format_}")
    return importes


def evaluer(client: ollama.Client, modele: str, consigne: str) -> int:
    """Le banc du chapitre 4 (schéma JSON, température 0), avec la consigne donnée."""
    justes = 0
    for annonce in ANNONCES:
        r = client.chat(model=modele, format=SCHEMA_FICHE, options={"temperature": 0, "seed": 42},
                        messages=[{"role": "system", "content": consigne},
                                  {"role": "user", "content": annonce["texte"]}])
        justes += champs_justes(json.loads(r.message.content), annonce["attendu"])
    return justes


def main() -> int:
    client = ollama.Client()
    if BASE_OLLAMA not in {m.model for m in client.list().models}:
        print(f"Lancez d'abord : ollama pull {BASE_OLLAMA}")
        return 1
    if not (LLAMA_CPP / "convert_hf_to_gguf.py").exists():
        print(f"llama.cpp introuvable dans {LLAMA_CPP} : voir l'en-tête de ce fichier")
        return 1
    importes = [f"{nom}-{f}" for nom in IMPORTS for f in ("f16", "q8_0")]
    deja_la = {m.model for m in client.list().models}
    if "--refaire" in sys.argv or not all(m in deja_la for m in importes):
        print("modèle de base et modèle fusionné …")
        ecrire_modeles()
        for nom, dossier in IMPORTS.items():
            print(f"import dans Ollama : {nom} …")
            importer(client, nom, dossier)
    tailles = {m.model: m.size for m in client.list().models}
    resultats = {"champs_total": len(ANNONCES) * len(CHAMPS)}
    for modele in (REFERENCE, BASE_OLLAMA, *importes):
        resultats[modele] = {cle: [evaluer(client, modele, consigne) for _ in range(PASSAGES)]
                             for cle, consigne in CONSIGNES.items()}
        resultats[modele]["disque_mo"] = round(tailles[modele] / 1e6)
        print(f"   {modele:<30} " + ", ".join(f"{cle} {resultats[modele][cle]}" for cle in CONSIGNES)
              + f", {resultats[modele]['disque_mo']} Mo")
    RESULTATS.write_text(json.dumps(resultats, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nécrit : {RESULTATS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
