# Job portal — projet de départ du cours **LLM open-weight en local**

L'assistant du portail d'emploi, servi par un modèle qui tourne sur votre
machine : Ollama et son client Python officiel (`ollama` 0.6), l'API
compatible OpenAI, la quantization mesurée, une évaluation sur un banc
d'annonces, un RAG local et un vrai fine-tuning LoRA.

Le modèle de données reprend celui de l'application **JobPortal**
(job-portal-ui) : offres avec titre, entreprise, catégorie, ville, contrat,
mode de travail et fourchette de salaire.

---

## Trois niveaux, trois besoins

| Ce que vous lancez | Il faut | Durée |
|---|---|---|
| `uv run --extra dev pytest -q` (14 tests) | rien : un faux serveur Ollama sous les vrais clients | quelques secondes |
| `chapitres/*.py`, `mesures/mesurer.py` | Ollama et les modèles ci-dessous | de quelques secondes à 15 min |
| `finetuning/*.py` | les paquets `--extra finetune` (torch, ~800 Mo) | ~25 min sur processeur |

```bash
uv sync --extra dev
uv run --extra dev pytest -q

ollama pull qwen2.5:1.5b-instruct-q4_K_M
ollama pull qwen2.5:1.5b-instruct-q8_0
ollama pull qwen2.5:1.5b-instruct-fp16
ollama pull bge-m3
uv run python chapitres/chapitre_1_premier_modele.py   # puis 2 à 6
uv run python mesures/mesurer.py                       # refait toutes les mesures
uv run python mesures/mesurer.py --comparer            # les refait et les compare

uv run --extra finetune python finetuning/entrainer.py   # LoRA, ~23 min
uv run --extra finetune python finetuning/evaluer.py     # avant / après
uv run --extra finetune python finetuning/vers_ollama.py # dans Ollama (voir son en-tête)
```

`jobportal/fausse_ollama.py` remplace **seulement le transport HTTP** des
clients `ollama` et `openai` : ils construisent leurs vraies requêtes, et les
tests mesurent ce qu'ils envoient (schéma JSON, options, `keep_alive`…).

## Ce qui a été mesuré

Le 6 octobre 2026, sur un Intel Core 7 240H (16 threads, 31,6 Go, **sans
GPU**), Ollama 0.35.0, avec un processeur déjà occupé de 26 à 80 % par
d'autres programmes. Les fichiers : `mesures/resultats.json` (passage 1),
`mesures/resultats-comparaison.json` (passage 2), `finetuning/resultats.json`,
`finetuning/ollama.json`, `finetuning/adaptateur/journal.json`.

**Quantization** — Qwen2.5 1,5B instruct, banc de 12 annonces (60 champs) :

| | disque | mémoire chargé | génération, médiane (min–max) | champs justes |
|---|---|---|---|---|
| q4_K_M | 986 Mo | 1 170 Mo | 22,4 jetons/s (15,1–36,3) | 54/60 |
| q8_0 | 1 647 Mo | 1 831 Mo | 15,2 jetons/s (10,9–18,4) | 55/60 |
| fp16 | 3 094 Mo | 3 278 Mo | 9,9 jetons/s (7,3–11,5) | 55/60 |

Les vitesses absolues dépendent de la charge ; les trois modèles sont donc
mesurés **en alternance**, et comparés tour par tour : q4 génère 1,55 fois
(passage 2 : 1,35) plus vite que q8, et q8 1,59 fois (1,60) plus vite que fp16.
Tailles, mémoire et qualité sont identiques d'un passage à l'autre.

**Pièges mesurés** :

| Piège | Mesure |
|---|---|
| Cache du prompt | le même prompt de 618 jetons relu en 54 ms au lieu de 3 765 ; `prompt_eval_count` affiche 618 dans les deux cas |
| Fenêtre de contexte | contexte par défaut 4 096 ; d'un prompt de 6 917 jetons, **2 050** sont lus, sans erreur |
| Mémoire et contexte (q4) | 1 109 Mo à `num_ctx` 2 048, 1 368 Mo à 8 192, 2 123 Mo à 32 768 |
| `OLLAMA_NUM_PARALLEL=1` | 4 requêtes simultanées arrivent en escalier (7,3 / 14,6 / 18,2 / 20,4 s) |
| `OLLAMA_NUM_PARALLEL=4` | elles arrivent ensemble ; 1,59 fois (passage 2 : 1,79) plus de jetons/s qu'en série |
| Serveurs différents | le même modèle à 15 jetons/s sur le serveur de l'application, 33 sur un `ollama serve` lancé à la main, à une minute d'intervalle |
| Client OpenAI | refuse de démarrer sans clé (« Missing credentials ») ; Ollama ne la lit pas |
| Déterminisme | température 0 et graine fixe : un modèle sur six a varié d'un champ (42 puis 43) |

**Fine-tuning** — Qwen2.5 0,5B instruct, LoRA rang 8 sur 240 annonces
générées (aucune ville ni phrase du banc), 60 pas en 23 min 07 s sur
processeur, 0,22 % des paramètres entraînés, adaptateur de 4,4 Mo :

| Banc de 12 annonces, dans Ollama, schéma JSON | consigne du cours | consigne d'entraînement |
|---|---|---|
| 1,5B de base, q4_K_M (986 Mo) | 54/60 | 56/60 |
| 0,5B de base, q8_0 (531 Mo) | 41/60 | 46/60 |
| **0,5B fine-tuné, q8_0 (531 Mo)** | 50/60 | **56/60** |

Dans transformers, sans schéma : 36/60 avant, 56/60 après.

**Import dans Ollama 0.35** : un dossier Hugging Face passe par le moteur MLX,
qui refuse Qwen2 (« unsupported MLX architecture ») ; `--quantize` n'y accepte
pas q4_K_M ; un GGUF doit arriver déjà quantizé. Chemin qui marche : le
convertisseur de llama.cpp (`convert_hf_to_gguf.py`, en f16 ou q8_0), puis
`ollama create`.

## Ce que le projet ne prouve pas

- **vLLM** : rien n'est mesuré, faute de GPU. Le cours le présente d'après sa
  documentation, et le dit.
- **Les vitesses sur votre machine** : elles dépendent du processeur, de la
  mémoire et de ce qui tourne à côté. Refaites-les (`mesures/mesurer.py`) ; ce
  qui doit se retrouver, ce sont les rapports et les constats, pas les chiffres.
- **Un fine-tuning qui généralise** : 12 annonces est un petit banc. Le résultat
  vaut pour cette tâche ; une autre tâche demande son propre banc.
- **Le 0,5B fine-tuné en q4_K_M** : il faudrait l'outil compilé de llama.cpp
  (`llama-quantize`), non utilisé ici.
