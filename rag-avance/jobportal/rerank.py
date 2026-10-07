"""Le reclassement — recuperer large, puis trier fin.

Le principe du cours : la recherche ramene trente candidats, le reclasseur en
garde cinq. Pourquoi deux etapes plutot qu'une ? Parce qu'elles n'ont pas le
meme cout. La recherche compare la requete a TOUT le corpus : elle doit etre
rapide, donc grossiere. Le reclasseur ne voit que trente paires : il peut etre
lent, donc fin.

⚠️ SUBSTITUTION ASSUMEE. Un vrai systeme met ici un cross-encoder — un modele
qui lit la requete ET le passage ensemble. Celui-ci applique trois regles
lisibles. C'est moins bon, et c'est dit ; mais la MECANIQUE — recuperer large,
trier fin, couper court — est identique, et c'est elle qu'on apprend.
"""

from __future__ import annotations

from .recherche import Morceau, mots


def score_paire(requete: str, morceau: Morceau) -> float:
    """Trois signaux, et chacun corrige un defaut du precedent."""
    termes = [t for t in mots(requete) if len(t) > 2]
    if not termes:
        return 0.0
    contenu = mots(morceau.texte)
    presents = [t for t in termes if t in contenu]

    # 1. COUVERTURE : combien de termes de la requete sont presents.
    #    Un passage qui repond a la moitie de la question vaut moins qu'un
    #    passage qui repond a tout — ce que BM25, additif, ne dit pas.
    # >>> depart: ecrire les trois signaux du reclasseur : couverture, proximite, densite. Les tests disent ce qu'ils doivent produire.
    #     return 0.0
    couverture = len(presents) / len(termes)

    # 2. PROXIMITE : les termes sont-ils groupes ou eparpilles ?
    #    « Lyon » au debut et « Kubernetes » a la fin ne parlent pas de la
    #    meme chose ; cote a cote, si.
    proximite = 0.0
    if len(presents) > 1:
        positions = [i for i, m in enumerate(contenu) if m in presents]
        etendue = max(positions) - min(positions) + 1
        proximite = len(presents) / etendue

    # 3. DENSITE : un terme dans un passage court pese plus que dans un pave.
    densite = len(presents) / max(len(contenu), 1)

    return 0.6 * couverture + 0.3 * proximite + 0.1 * min(densite * 10, 1.0)
    # <<<


def reclasser(requete: str, candidats: list[Morceau], k: int = 5) -> list[Morceau]:
    notes = sorted(((score_paire(requete, m), i, m) for i, m in enumerate(candidats)),
                   key=lambda t: (-t[0], t[1]))
    return [m for _, _, m in notes][:k]
