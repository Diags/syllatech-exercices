"""Chapitre 5 — Authentifier, autoriser, filtrer : trois défauts qui coûtent.

    uv run python chapitres/chapitre_5_securite.py

C'est le chapitre où le schéma publié cesse d'être une formalité. Trois
valeurs par défaut y décident du niveau de sécurité réel, et aucune des
trois ne s'écrit dans un fichier de configuration :

    jwtAuth.mode          = optional  « allows requests without a JWT »
    regex.action          = mask      (et non `reject`)
    mcpAuthorization      composition des règles allow / require / deny

Les règles CEL sont évaluées ici pour de bon, par `cel-python`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import autorisation, gardes, schema_publie        # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    CONFIGS, EXEMPLES_AMONT, PORTAIL, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import charger                             # noqa: E402
from jobportal.modeles import ErreurDeCEL                        # noqa: E402

# La regle exacte du support de cours.
REGLE_DU_SUPPORT = 'jwt.team == "data" && mcp.tool.name.startsWith("postgres_")'

# La meme, ecrite defensivement.
REGLE_DEFENSIVE = ('has(jwt.team) && jwt.team == "data" '
                   '&& mcp.tool.name.startsWith("postgres_")')

CORPUS = [
    ("Le candidat paiera par carte 4539 1488 0343 6467.", True),
    ("SSN du candidat : 123-45-6789.", True),
    ("Contacter le candidat au 06 12 34 56 78.", True),
    ("Poste 4539 de la convention collective, article 1488.", False),
    ("Reference de l'offre : 2026-09-14-RH.", False),
    ("Le candidat a 3 ans d'experience.", False),
    ("Numero de dossier 4539148803436467.", True),
    ("Budget : 1 488 034 euros sur 3 ans.", False),
]


def principal() -> None:
    utf8()

    titre(1, "LA CONFIGURATION DU SUPPORT, PASSEE AU SCHEMA")
    du_cours = charger(CONFIGS / "du-cours" / "ch5-securite.yaml")
    erreurs = schema_publie.verifier(du_cours)
    ligne("erreurs", str(len(erreurs)), 26)
    print()
    for chemin, message in erreurs:
        print(f"      {chemin}")
        print(f"        {message.split('  [dans')[0]}")
    print()
    for l in plier(
        "Deux refus, et le second est le plus grave : un `jwtAuth` sans "
        "source de cles ne peut verifier aucune signature. Le schema le "
        "refuse — il exige soit `providers`, soit `issuer` AVEC `jwks`."):
        print(f"   {l}")

    titre(2, "LE DEFAUT QUI ANNULE L'AUTHENTIFICATION")
    print("   `jwtAuth.mode`, dans le schema publie :\n")
    for valeur in schema_publie.constantes("Mode"):
        marque = "  ← le defaut" if valeur == "optional" else ""
        print(f"      {valeur}{marque}")
        for l in plier(schema_publie.description("Mode", valeur), 58):
            print(f"           {l}")
    print()
    for l in plier(
        "« Warning: this allows requests without a JWT. » C'est ecrit dans le "
        "contrat que le proxy publie, et c'est la valeur par defaut. Une "
        "route qui pose `jwtAuth` sans `mode` n'exige donc RIEN : elle "
        "verifie le jeton de ceux qui en presentent un, et laisse entrer les "
        "autres."):
        print(f"   {l}")
    print()
    amont = charger(EXEMPLES_AMONT / "mcp-authorization.yaml")
    jwt_amont = (amont.brut.get("mcp") or {}).get("policies", {}).get("jwtAuth", {})
    ligne("l'exemple amont pose-t-il `mode` ?",
          "oui" if "mode" in jwt_amont else "non", 40)
    ligne("la configuration du support ?",
          "oui" if "mode" in (du_cours.routes()[0].politiques.get("jwtAuth") or {})
          else "non", 40)
    ligne("configs/portail/03-securite.yaml ?",
          (charger(PORTAIL / "03-securite.yaml").routes()[0]
           .politiques["jwtAuth"].get("mode", "non")), 40)

    titre(3, "TROIS FORMES DE REGLE, ET UNE MISE EN GARDE")
    for forme in ("allow", "require", "deny"):
        print(f"   {forme}")
        for b in schema_publie.definitions()["RuleSerde"]["anyOf"][0]["oneOf"]:
            if forme in (b.get("required") or []):
                for l in plier(" ".join(b.get("description", "").split()), 58):
                    print(f"        {l}")
    print()
    for l in plier(
        "La mise en garde sur `deny` n'est pas une precaution de style : "
        "« expression failures fail to deny ». Une regle `deny` dont "
        "l'expression LEVE laisse passer. Une regle `allow` dont l'expression "
        "leve refuse. La meme faute d'ecriture a donc deux effets opposes "
        "selon la forme choisie."):
        print(f"   {l}")

    titre(4, "LA REGLE DU SUPPORT, EVALUEE POUR DE BON")
    print(f"   {REGLE_DU_SUPPORT}\n")
    regles = [autorisation.Regle("allow", REGLE_DU_SUPPORT)]
    jetons = [
        ("equipe data", {"sub": "u1", "team": "data"}),
        ("equipe rh", {"sub": "u2", "team": "rh"}),
        ("sans revendication `team`", {"sub": "u3"}),
    ]
    outils = ["postgres_query", "offres_chercher"]
    tableau(["jeton", "outil", "verdict"],
            [[etiquette, outil,
              str(autorisation.decider(
                  regles, autorisation.contexte_mcp(outil, claims=claims)))[:44]]
             for etiquette, claims in jetons for outil in outils],
            [26, 18, 48])
    print()
    for l in plier(
        "Les quatre premieres lignes sont celles qu'on attend. Les deux "
        "dernieres sont celles qui apprennent quelque chose : un jeton "
        "VALIDE mais sans revendication `team` fait LEVER l'expression. Sur "
        "une regle `allow`, cela refuse — le bon comportement, obtenu par "
        "accident plutot que par ecriture."):
        print(f"   {l}")

    titre(5, "LA MEME REGLE, EN `deny`")
    print("   On inverse la forme, sans toucher a l'expression :\n")
    inversee = [autorisation.Regle(
        "deny", 'jwt.team != "data" && mcp.tool.name.startsWith("postgres_")')]
    tableau(["jeton", "outil", "verdict"],
            [[etiquette, "postgres_query",
              str(autorisation.decider(
                  inversee,
                  autorisation.contexte_mcp("postgres_query", claims=claims)))[:44]]
             for etiquette, claims in jetons], [26, 18, 48])
    print()
    for l in plier(
        "La derniere ligne est le piege annonce par le schema. Le jeton sans "
        "`team` ne devrait PAS acceder a `postgres_query` — mais l'expression "
        "leve, le `deny` ne se declenche pas, et rien d'autre ne s'y oppose. "
        "L'acces est accorde. C'est exactement ce que veut dire « expression "
        "failures fail to deny »."):
        print(f"   {l}")

    titre(6, "LA FORME DEFENSIVE, ET CE QU'ELLE CHANGE")
    print(f"   {REGLE_DEFENSIVE}\n")
    tableau(["jeton", "expression", "resultat"],
            [[etiquette, forme,
              _resultat(regle, claims)]
             for etiquette, claims in jetons
             for forme, regle in (("du support", REGLE_DU_SUPPORT),
                                  ("defensive", REGLE_DEFENSIVE))],
            [26, 16, 40])
    print()
    ligne("la regle du support est-elle defensive ?",
          "oui" if autorisation.defensive(REGLE_DU_SUPPORT) else "non", 42)
    ligne("la regle corrigee ?",
          "oui" if autorisation.defensive(REGLE_DEFENSIVE) else "non", 42)
    print()
    for l in plier(
        "Cinq lignes sur six rendent la meme chose. La sixieme est la "
        "difference : avec `has(...)`, l'expression rend FAUX ; sans lui, "
        "elle LEVE. Le verdict final se trouve etre le meme sur un `allow` — "
        "et c'est l'inverse sur un `deny`, comme la section precedente vient "
        "de le montrer."):
        print(f"   {l}")
    print()
    for l in plier(
        "Et la regle qui rattrape tout, celle que `configs/portail/"
        "03-securite.yaml` pose : `require: has(jwt.sub)`. Elle ne depend "
        "d'aucune revendication metier, elle refuse toute requete sans jeton "
        "— et c'est elle, pas `jwtAuth`, qui rend l'authentification "
        "obligatoire quand `mode` est reste au defaut."):
        print(f"   {l}")

    titre(7, "LE NOM D'OUTIL QUE LA REGLE REGARDE")
    for champ in ("mcp.tool.name", "mcp.tool.target"):
        description = _cel_md(champ)
        ligne(champ, description[:58], 20)
    print()
    portail = charger(PORTAIL / "01-mcp.yaml")
    prefixe = (portail.routes()[0].backends[0]["mcp"]).get("prefixMode")
    ligne("prefixMode du portail", str(prefixe), 30)
    print()
    for l in plier(
        "`mcp.tool.name` est « the RESOLVED tool name sent to the upstream "
        "target » — le nom APRES resolution du multiplexage, donc sans le "
        "prefixe de cible. Une regle ecrite sur `offres_chercher` regarde "
        "donc le mauvais champ quand `prefixMode: always` est pose : c'est "
        "`mcp.tool.target == \"offres\"` qu'il faut croiser avec "
        "`mcp.tool.name == \"chercher\"`."):
        print(f"   {l}")
    print()
    for l in plier(
        "⚠️ Ce projet n'a pas de serveur MCP branche : il ne peut pas "
        "MESURER quel nom arrive dans le contexte. Ce qui precede est lu dans "
        "`amont/cel.md`, et c'est une raison de verifier ses regles sur un "
        "vrai proxy plutot que de les croire."):
        print(f"   {l}")

    titre(8, "LES GUARDRAILS : L'ACTION QUE PERSONNE N'ECRIT")
    action = schema_publie.definitions()["RegexRules"]["properties"]["action"]
    ligne("RegexRules.action, defaut", str(action.get("default")), 30)
    ligne("builtins reconnus",
          ", ".join(schema_publie.constantes("Builtin")), 30)
    ligne("ce que le support ecrit", "builtin: credit_card", 30)
    print()
    for l in plier(
        "`credit_card` n'est pas dans l'enumeration : c'est `creditCard`. Le "
        "schema refuse, donc le proxy ne demarre pas — une faute bruyante, "
        "c'est la bonne sorte. L'`action` par defaut, elle, est silencieuse : "
        "un garde sans `action` MASQUE la donnee et laisse passer la requete."):
        print(f"   {l}")
    print()
    for etiquette, bloc in [
        ("sans action (defaut)", {"rules": [{"builtin": "creditCard"}]}),
        ("action: reject", {"action": "reject",
                            "rules": [{"builtin": "creditCard"}]}),
    ]:
        constat = gardes.appliquer(bloc, CORPUS[0][0])
        ligne(etiquette,
              f"declenche={constat.declenche}  bloque={constat.bloque}", 26)
        print(f"        texte transmis : {constat.texte}")

    titre(9, "CE QU'UNE EXPRESSION REGULIERE RATE, COMPTE")
    print("   ⚠️ Les motifs des builtins ne sont PAS publies : ceux-ci sont")
    print("   ceux de ce projet. Ce qu'on mesure n'est donc pas la qualite")
    print("   d'agentgateway — c'est celle d'un garde-fou par motif.\n")
    bloc = {"action": "reject",
            "rules": [{"builtin": "creditCard"}, {"builtin": "ssn"},
                      {"builtin": "phoneNumber"}]}
    tableau(["texte", "sensible ?", "declenche ?"],
            [[texte[:44], "oui" if sensible else "non",
              "oui" if gardes.appliquer(bloc, texte).declenche else "non"]
             for texte, sensible in CORPUS], [46, 12, 14])
    print()
    compte = gardes.mesurer(bloc, CORPUS)
    for quoi, combien in compte.items():
        ligne(f"  {quoi}", str(combien), 22)
    print()
    for l in plier(
        "Les faux positifs bloquent du travail legitime ; les faux negatifs "
        "laissent partir la donnee qu'on voulait retenir. Aucun reglage ne "
        "supprime les deux — c'est la nature d'un filtre par motif, et c'est "
        "la raison pour laquelle un guardrail regex est une PREMIERE ligne, "
        "pas une garantie."):
        print(f"   {l}")

    titre(10, "LA ROUTE PROTEGEE DU PORTAIL, EN ENTIER")
    securite = charger(PORTAIL / "03-securite.yaml")
    route = securite.routes()[0]
    ligne("erreurs du schema", str(len(schema_publie.verifier(securite))), 30)
    ligne("politiques posees", ", ".join(sorted(route.politiques)), 30)
    print()
    regles_portail = autorisation.lire(route.politiques["mcpAuthorization"])
    for regle in regles_portail:
        ok, message = autorisation.compile_t_elle(regle.expression)
        defensive_ = "defensive" if autorisation.defensive(regle.expression) \
            else "NON defensive"
        print(f"   {regle.forme:8} {defensive_:14} "
              f"{'compile' if ok else 'NE COMPILE PAS'}")
        for l in plier(regle.expression, 58):
            print(f"            {l}")
    print()
    tableau(["jeton", "outil", "verdict"],
            [[etiquette, outil,
              str(autorisation.decider(
                  regles_portail,
                  autorisation.contexte_mcp(outil, claims=claims)))[:46]]
             for etiquette, claims in
             [("rh", {"sub": "u1", "team": "rh"}),
              ("data", {"sub": "u2", "team": "data"}),
              ("sans jeton", None)]
             for outil in ("offres_chercher", "annuaire_verifier")],
            [14, 20, 48])
    print()
    for l in plier(
        "La ligne « sans jeton » est celle qui justifie la regle `require`. "
        "Sans elle, une requete non authentifiee n'aurait aucune regle `allow` "
        "vraie — donc un refus — mais seulement par effet de bord. Avec elle, "
        "le refus est ECRIT."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : mettre tout cela devant l'existant.\n")


def _resultat(expression: str, claims: dict) -> str:
    from jobportal.modeles import evaluer
    try:
        return str(evaluer(expression,
                           autorisation.contexte_mcp("postgres_query",
                                                     claims=claims)))
    except ErreurDeCEL as erreur:
        return f"LEVE — {str(erreur)[:26]}"


def _cel_md(champ: str) -> str:
    """La description d'un champ, lue dans `amont/cel.md`."""
    for ligne_ in (EXEMPLES_AMONT.parent / "cel.md").read_text(
            encoding="utf-8").splitlines():
        if ligne_.startswith(f"|`{champ}`|"):
            return ligne_.split("|")[3].replace("<br>", " ")
    return "(absent de cel.md)"


if __name__ == "__main__":
    principal()
