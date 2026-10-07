"""Chapitre 6 — Production : le cout, et ce qui le fait exploser.

    uv run python chapitres/chapitre_6_production.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.qdrant import COLLECTION, client_prepare, chercher   # noqa: E402
from jobportal.vecteurs import vectoriser              # noqa: E402
from qdrant_client import models                       # noqa: E402

SURCOUT_HNSW = 0.5      # l'index pese environ la moitie des vecteurs


def ram(n: int, dim: int, octets: int = 4) -> float:
    """En giga-octets. La formule du cours, appliquee."""
    return n * dim * octets * (1 + SURCOUT_HNSW) / 1e9


def main() -> None:
    console.utf8()
    print("1. MISE A JOUR INCREMENTALE — upsert idempotent\n")
    client = client_prepare()
    cible = chercher(client, "Kubernetes a Lyon", 1)[0]
    total_avant = client.count(COLLECTION).count
    print(f"   point {cible['id']} : « {cible['titre']} »")
    print(f"   points dans la collection : {total_avant}")

    # On rejoue DEUX FOIS le meme upsert : c'est la le test de l'idempotence.
    for _ in range(2):
        client.upsert(COLLECTION, points=[models.PointStruct(
            id=cible["id"], vector=vectoriser("Lead Kubernetes expert — Lyon"),
            payload={**cible, "titre": "Lead Kubernetes expert — Lyon"})])

    releve = client.retrieve(COLLECTION, ids=[cible["id"]])[0]
    total_apres = client.count(COLLECTION).count
    print(f"\n   apres deux upserts identiques :")
    print(f"   point {cible['id']} : « {releve.payload['titre']} »")
    print(f"   points dans la collection : {total_apres}")
    print(f"\n   Le titre a change, le NOMBRE de points n'a pas bouge "
          f"({total_avant} → {total_apres}).")
    print("   L'upsert remplace au meme identifiant : rejouer l'ingestion ne")
    print("   cree pas de doublons. C'est ce qui rend une reprise apres")
    print("   incident sans danger — et c'est pourquoi l'identifiant doit")
    print("   venir de VOS donnees, jamais d'un compteur.")

    print("\n2. SUPPRESSION — la conformite n'est pas optionnelle\n")
    client.delete(COLLECTION, points_selector=models.PointIdsList(points=[cible["id"]]))
    restant = client.retrieve(COLLECTION, ids=[cible["id"]])
    print(f"   point {cible['id']} apres suppression : "
          f"{'encore la' if restant else 'absent'}")
    print(f"   points dans la collection : {client.count(COLLECTION).count}")
    print("\n   Un droit a l'effacement porte AUSSI sur les vecteurs. Un")
    print("   embedding n'est pas anonyme : il est derive du texte, et il")
    print("   suffit souvent a le retrouver.")

    print("\n3. LE COUT EN MEMOIRE — la vraie contrainte\n")
    print(f"   {'vecteurs':>12} {'dim':>6} {'float32':>10} {'int8 (quantise)':>17}")
    for n, dim in ((100_000, 768), (1_000_000, 1536), (10_000_000, 1536), (100_000_000, 768)):
        print(f"   {n:>12,} {dim:>6} {ram(n, dim):>9.1f} Go {ram(n, dim, 1):>15.1f} Go"
              .replace(",", " "))

    print("\n   Trois leviers, dans l'ordre ou il faut y penser :\n")
    print("   · LA DIMENSION. Passer de 1536 a 768 divise la facture par deux,")
    print("     et beaucoup de modeles rendent des vecteurs tronquables sans")
    print("     perte notable. C'est le levier le moins connu et le plus")
    print("     rentable — et il se mesure : rappel avant, rappel apres.")
    print("   · LA QUANTIZATION. Un octet au lieu de quatre : RAM divisee par")
    print("     quatre, rappel presque intact. Mesurez-le quand meme.")
    print("   · LES VECTEURS FROIDS SUR DISQUE, pour ce qu'on interroge rarement.")

    print("\n4. REINDEXER, OU RE-EMBEDDER ? Ce n'est pas la meme facture :\n")
    print("   changement de m ou ef_construct → REINDEXATION locale, les")
    print("      vecteurs sont conserves ;")
    print("   changement de MODELE d'embedding → RE-EMBEDDING complet. Tous")
    print("      les vecteurs sont a recalculer, et les anciens ne sont pas")
    print("      comparables aux nouveaux. C'est une migration, pas un")
    print("      reglage : prevoyez de faire tourner les deux en parallele.")


if __name__ == "__main__":
    main()
