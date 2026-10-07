"""Un fine-tuning LoRA de Qwen2.5-0.5B-Instruct, sur processeur.

    uv run --extra finetune python finetuning/entrainer.py

LoRA n'entraîne pas le modèle : il ajoute à quelques couches de petites
matrices (rang 8) et n'entraîne qu'elles. Le modèle de base reste figé ; ce
qu'on obtient est un « adaptateur » de quelques mégaoctets, écrit dans
finetuning/adaptateur/, avec le journal de l'entraînement (durée, perte).

On n'apprend que la RÉPONSE : les jetons de la consigne et de l'annonce sont
masqués (étiquette -100), le modèle n'est corrigé que sur le JSON qu'il écrit.
"""

import json
import pathlib
import random
import statistics
import sys
import time

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from donnees_entrainement import en_conversation, generer, verifier_separation  # noqa: E402

BASE = "Qwen/Qwen2.5-0.5B-Instruct"
SORTIE = pathlib.Path(__file__).with_name("adaptateur")
EPOQUES, LOT, TAUX = 2, 8, 2e-4

sys.stdout.reconfigure(encoding="utf-8")


def encoder(tokenizer, exemple: dict) -> tuple[list[int], list[int]]:
    """Les identifiants de jetons, et les étiquettes : -100 sur tout ce qui précède la réponse."""
    conversation = en_conversation(exemple)
    complet = tokenizer.apply_chat_template(conversation, tokenize=False)
    debut = tokenizer.apply_chat_template(conversation[:2], tokenize=False, add_generation_prompt=True)
    ids = tokenizer(complet, add_special_tokens=False)["input_ids"]
    n = len(tokenizer(debut, add_special_tokens=False)["input_ids"])
    return ids, [-100] * n + ids[n:]


def lot_rembourre(paires, remplissage: int):
    longueur = max(len(ids) for ids, _ in paires)
    ids = torch.full((len(paires), longueur), remplissage)
    etiquettes = torch.full((len(paires), longueur), -100)
    masque = torch.zeros((len(paires), longueur), dtype=torch.long)
    for i, (x, y) in enumerate(paires):
        ids[i, :len(x)], etiquettes[i, :len(y)], masque[i, :len(x)] = torch.tensor(x), torch.tensor(y), 1
    return ids, etiquettes, masque


def main() -> int:
    torch.manual_seed(0)
    exemples = generer()
    verifier_separation(exemples)
    tokenizer = AutoTokenizer.from_pretrained(BASE)
    modele = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float32)
    modele = get_peft_model(modele, LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    ))
    entraines = sum(p.numel() for p in modele.parameters() if p.requires_grad)
    total = sum(p.numel() for p in modele.parameters())
    print(f"{len(exemples)} exemples ; paramètres entraînés : {entraines:,} sur {total:,} "
          f"({100 * entraines / total:.2f} %)".replace(",", " "))

    donnees = [encoder(tokenizer, e) for e in exemples]
    optimiseur = torch.optim.AdamW([p for p in modele.parameters() if p.requires_grad], lr=TAUX)
    hasard = random.Random(0)
    pertes, debut = [], time.perf_counter()
    modele.train()
    for epoque in range(EPOQUES):
        hasard.shuffle(donnees)
        for i in range(0, len(donnees), LOT):
            ids, etiquettes, masque = lot_rembourre(donnees[i:i + LOT], tokenizer.pad_token_id)
            perte = modele(input_ids=ids, attention_mask=masque, labels=etiquettes).loss
            perte.backward()
            optimiseur.step()
            optimiseur.zero_grad()
            pertes.append(round(perte.item(), 4))
            if len(pertes) % 10 == 1:
                print(f"   époque {epoque + 1}, pas {len(pertes)} : perte {pertes[-1]:.3f} "
                      f"({time.perf_counter() - debut:.0f} s)")
    duree = time.perf_counter() - debut

    modele.save_pretrained(SORTIE)
    taille = sum(f.stat().st_size for f in SORTIE.glob("*.safetensors"))
    journal = {
        "base": BASE, "exemples": len(exemples), "epoques": EPOQUES, "lot": LOT, "taux": TAUX,
        "rang_lora": 8, "pas": len(pertes), "duree_s": round(duree), "threads": torch.get_num_threads(),
        "perte_premiers_pas": statistics.mean(pertes[:5]), "perte_derniers_pas": statistics.mean(pertes[-5:]),
        "parametres_entraines": entraines, "parametres_total": total,
        "taille_adaptateur_mo": round(taille / 1e6, 1), "pertes": pertes,
    }
    (SORTIE / "journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8")
    print(f"\n{len(pertes)} pas en {duree:.0f} s ; perte {journal['perte_premiers_pas']:.3f} → "
          f"{journal['perte_derniers_pas']:.3f} ; adaptateur {journal['taille_adaptateur_mo']} Mo dans {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
