#!/usr/bin/env python3
"""Le verificateur de config.yaml — ce qui demarre et ne marche pas.

    uv run python outils/verifier_config.py config/a-corriger.yaml

Les defauts qu'il attrape ont tous la meme forme : le proxy DEMARRE, il
repond, les applications fonctionnent — et la regle ne fait pas ce qu'on
croit. Aucun n'est une erreur de syntaxe ; aucun n'apparait dans un journal.

Le seul qui exige litellm est la verification des prix : c'est sa table de
tarifs qui dit si un modele sera facture zero. L'import coute une trentaine
de secondes, et il est donc fait au dernier moment.
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.proxy import ENVIRONNEMENT, charger      # noqa: E402

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:      # noqa: BLE001
        pass


@dataclass
class Souci:
    gravite: str          # "erreur" ou "attention"
    ou: str
    message: str


def verifier(config: dict, avec_prix: bool = True) -> list[Souci]:
    soucis: list[Souci] = []
    modeles = config.get("model_list") or []
    reglages = config.get("litellm_settings") or {}
    general = config.get("general_settings") or {}
    alias = [m.get("model_name", "?") for m in modeles]

    if not modeles:
        return [Souci("erreur", "model_list",
                      "aucun modele : le proxy demarre et refuse tout")]

    # 1. Un secret en clair -------------------------------------------------
    for entree in modeles:
        params = entree.get("litellm_params") or {}
        for champ in ("api_key", "api_base"):
            valeur = params.get(champ)
            if champ == "api_key" and isinstance(valeur, str) \
                    and not ENVIRONNEMENT.match(valeur):
                soucis.append(Souci(
                    "erreur", f"{entree.get('model_name')} / {champ}",
                    "cle ecrite en clair. Elle part dans git, dans les "
                    "sauvegardes et dans les images du conteneur. Utilisez "
                    "« os.environ/NOM_DE_LA_VARIABLE » : le proxy la lit au "
                    "demarrage, et la rotation ne demande aucun redeploiement."))
    if isinstance(general.get("master_key"), str) \
            and not ENVIRONNEMENT.match(general["master_key"]):
        soucis.append(Souci(
            "erreur", "general_settings / master_key",
            "la cle MAITRE en clair. C'est celle qui genere et revoque les "
            "cles virtuelles : elle contourne tous les budgets."))

    # 2. Un alias declare deux fois ----------------------------------------
    for nom, combien in Counter(alias).items():
        if combien > 1:
            soucis.append(Souci(
                "erreur", f"model_list / {nom}",
                f"declare {combien} fois. LiteLLM n'ecrase pas le premier : "
                "il y voit plusieurs deploiements du meme alias et REPARTIT "
                "la charge entre eux (simple-shuffle par defaut). Une part "
                "des requetes part donc vers l'autre modele, avec l'autre "
                "prix et l'autre qualite."))

    # 3. Un fallback vers un alias jamais declare --------------------------
    for regle in reglages.get("fallbacks") or []:
        for source, cibles in regle.items():
            if source not in alias:
                soucis.append(Souci("erreur", f"fallbacks / {source}",
                                    f"« {source} » n'est pas dans model_list : "
                                    "cette regle ne peut jamais s'appliquer."))
            for cible in cibles:
                if cible not in alias:
                    soucis.append(Souci(
                        "erreur", f"fallbacks / {source} → {cible}",
                        f"« {cible} » n'est declare nulle part. La bascule "
                        "echoue, et l'erreur rendue au client est celle du "
                        "modele PRINCIPAL — on cherche la panne du mauvais "
                        "cote. Le Router accepte pourtant cette regle a la "
                        "construction, sans un mot."))

    # 4. Le prix des reessais ----------------------------------------------
    reessais = reglages.get("num_retries", 0)
    if reessais and reglages.get("fallbacks"):
        soucis.append(Souci(
            "attention", "litellm_settings / num_retries",
            f"{reessais} reessai(s) AVANT la bascule. Mesure sur ce projet : "
            "~130 ms pour basculer sans reessai, ~4,7 s avec deux. Sur un "
            "appel interactif, c'est la difference entre une hesitation et un "
            "abandon — et la bascule existe justement pour ce cas."))

    # 5. Le cout invisible --------------------------------------------------
    if avec_prix:
        for entree in modeles:
            modele = (entree.get("litellm_params") or {}).get("model", "")
            if modele and not _a_un_prix(modele):
                soucis.append(Souci(
                    "erreur", f"{entree.get('model_name')} / {modele}",
                    "absent de la table de prix de litellm : chaque appel "
                    "sera facture 0,00 $. Rien n'est leve, rien n'est "
                    "journalise — le modele disparait simplement du tableau "
                    "de bord des couts. Declarez son prix dans "
                    "« model_info » (input_cost_per_token / "
                    "output_cost_per_token)."))

    # 6. Ce qui manque ------------------------------------------------------
    if not reglages.get("fallbacks"):
        soucis.append(Souci("attention", "litellm_settings / fallbacks",
                            "aucune bascule : une panne de fournisseur est "
                            "une panne du job portal."))
    if not general.get("master_key"):
        soucis.append(Souci("attention", "general_settings / master_key",
                            "sans cle maitre, l'administration du proxy n'est "
                            "pas protegee."))
    if not reglages.get("success_callback"):
        soucis.append(Souci("attention", "litellm_settings / success_callback",
                            "aucun rappel : ni cout, ni latence, ni trace. La "
                            "premiere facture sera la premiere mesure."))
    return soucis


CHAMPS_DE_PRIX = ("input_cost_per_token", "output_cost_per_token",
                  "input_cost_per_second", "output_cost_per_second")


def _a_un_prix(modele: str) -> bool:
    """Le modele a-t-il un tarif CONNU ?

    ⚠️ Tester la presence de la cle ne suffit pas, et c'est un piege mesure :
    apres un seul appel vers un modele inconnu, litellm INSERE sa cle dans
    `model_cost` — avec un dictionnaire VIDE. Un verificateur qui se contente
    de `modele in model_cost` est donc juste au demarrage et faux des le
    premier appel, ce qui est la pire des deux situations.

    On exige donc un champ de tarif. Une entree a 0,00 $ reste valide : un
    modele auto-heberge ne coute effectivement rien au jeton, et « ollama/
    llama3 » est dans la table avec des zeros explicites.
    """
    from litellm import model_cost

    # >>> depart: chercher le modele dans model_cost SOUS SES DEUX FORMES (avec et sans prefixe de fournisseur) et n'accepter que si l'entree porte un CHAMPS_DE_PRIX non nul. Tester la seule presence de la cle rendrait vrai des le premier appel, litellm inserant une entree VIDE pour un modele inconnu. Deux tests le verifient.
    #     return True
    for cle in (modele, modele.split("/")[-1]):
        infos = model_cost.get(cle)
        if infos and any(infos.get(champ) is not None
                         for champ in CHAMPS_DE_PRIX):
            return True
    return False
    # <<<


def main() -> int:
    chemins = [a for a in sys.argv[1:] if not a.startswith("--")]
    chemin = chemins[0] if chemins else "config/passerelle.yaml"
    soucis = verifier(charger(chemin), avec_prix="--sans-prix" not in sys.argv)
    erreurs = [s for s in soucis if s.gravite == "erreur"]

    print(f"\n  {chemin}\n")
    for souci in soucis:
        etiquette = "ERREUR    " if souci.gravite == "erreur" else "attention "
        print(f"  {etiquette} {souci.ou}")
        for ligne in _plier(souci.message, 64):
            print(f"             {ligne}")
    if not soucis:
        print("  Aucun probleme detecte.")
    print(f"\n  {len(erreurs)} erreur(s), "
          f"{len(soucis) - len(erreurs)} avertissement(s)\n")
    return 1 if erreurs else 0


def _plier(texte: str, largeur: int) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    if courante:
        lignes.append(courante)
    return lignes


if __name__ == "__main__":
    sys.exit(main())
