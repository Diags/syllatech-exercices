"""Ce que le registre LANCE, quand le manifeste ne le dit pas.

`spec.source.package.launch` est facultatif. Absent, le resolveur derive la
commande de l'origine. Present, il ne derive plus rien :

    mcpserver.go, MCPPackageLaunch :
    « If Launch is nil, the resolver derives Command and Args from
      Origin.Type defaults (npm → "npx -y <id>@<ver>"; pypi →
      "uvx <id>==<ver>"; oci → image entrypoint). If Launch is set, the
      manifest owns Command and Args verbatim — no implicit identifier
      injection. Command may be empty only for oci. »

La derniere phrase est celle qui coute une soiree : poser `launch.command`
pour ajouter une option retire l'injection de l'identifiant, et le serveur
demarre sans savoir quel paquet lancer. Rien dans le manifeste ne le montre.

C'est aussi la reponse a la question du chapitre 2 : `npx` et `uvx` ne sont
pas des « runtimes » qu'on declare, ce sont des commandes DERIVEES.
"""

from __future__ import annotations

from typing import Any


def derivee(paquet: dict[str, Any]) -> tuple[str, str]:
    """La commande que le resolveur derive d'un paquet sans `launch`.

    Rend (commande, d'ou elle vient). La commande est une chaine lisible,
    pas un argv : ce projet ne lance rien, il montre ce qui serait lance.
    """
    origine = paquet.get("origin")
    if not isinstance(origine, dict):
        return "", "origine absente"
    # TODO : deriver la commande de l'origine — npx pour npm, uvx pour pypi, ENTRYPOINT pour oci
    return "", "a completer"


def effective(paquet: dict[str, Any]) -> tuple[str, str]:
    """La commande reellement lancee : `launch` si present, sinon derivee.

    Le second element dit lequel des deux a repondu — et c'est la seule
    chose que la fiche du catalogue ne montre pas.
    """
    lancement = paquet.get("launch")
    if not isinstance(lancement, dict):
        return derivee(paquet)
    commande = lancement.get("command") or ""
    arguments = []
    for a in lancement.get("args") or []:
        if not isinstance(a, dict):
            continue
        if a.get("type") == "named" and a.get("name"):
            arguments.append(f"{a['name']} {a.get('value', '')}".strip())
        else:
            arguments.append(str(a.get("value", "")))
    if not commande and (origine := paquet.get("origin")) \
            and isinstance(origine, dict) and origine.get("type") == "oci":
        # « Command may be empty only for oci. »
        return derivee(paquet)
    return " ".join([commande, *arguments]).strip(), "launch"


def variables_requises(paquet: dict[str, Any]) -> list[str]:
    """Les variables d'environnement que le manifeste declare obligatoires.

    `env[].isRequired` n'est pas un commentaire : c'est ce qu'une equipe lit
    pour savoir quels secrets fournir avant de deployer. Un serveur qui en a
    besoin et ne les declare pas demarre, puis echoue au premier appel.
    """
    lancement = paquet.get("launch")
    if not isinstance(lancement, dict):
        return []
    return [v["name"] for v in lancement.get("env") or []
            if isinstance(v, dict) and v.get("isRequired") and v.get("name")]
