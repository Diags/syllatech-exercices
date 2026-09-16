#!/usr/bin/env python3
"""Verifie qu'une migration porte bien un « up » ET un « down ».

Appele par la skill migration. Volontairement severe : une migration sans
rollback passe les tests, part en production, et ne se remarque que le jour
ou il faut revenir en arriere.
"""

import re
import sys


def verifier(texte: str) -> list[str]:
    soucis = []
    if not re.search(r"^\s*--\s*up\b", texte, re.IGNORECASE | re.MULTILINE):
        soucis.append("section « -- up » absente")
    # TODO : refuser une migration sans section « -- down ». C'est l'invariant que la skill grave : une migration sans rollback passe les tests, part en production, et ne se remarque que le jour ou il faut revenir en arriere.
    pass

    bas = texte.lower()
    if "drop table" in bas and "create table" not in bas.split("-- down")[-1]:
        soucis.append("DROP TABLE sans CREATE TABLE dans le down : "
                      "la donnee serait perdue sans retour possible")
    return soucis


def main() -> int:
    if len(sys.argv) < 2:
        print("usage : verifier_migration.py <fichier.sql>")
        return 2
    soucis = verifier(open(sys.argv[1], encoding="utf-8").read())
    for s in soucis:
        print(f"  REFUSE : {s}")
    if not soucis:
        print("  migration valide : up et down presents")
    return 1 if soucis else 0


if __name__ == "__main__":
    sys.exit(main())
