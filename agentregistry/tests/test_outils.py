"""Les deux outils, appeles comme en ligne de commande.

Un outil dont le code de sortie ment ne sert a rien en CI : c'est
exactement ce que ces tests fixent.
"""

from __future__ import annotations

from jobportal.commun import CATALOGUE, EXEMPLES_AMONT
from outils import fiches, verifier_manifeste

A_CORRIGER = str(CATALOGUE / "a-corriger.yaml")
PORTAIL = str(CATALOGUE / "portail")
AMONT = str(EXEMPLES_AMONT)


def test_le_portail_passe_les_trois_couches(capsys):
    """Les sept manifestes du portail, verifies contre eux-memes."""
    from pathlib import Path
    fichiers = [str(p) for p in sorted(Path(PORTAIL).glob("*.yaml"))]
    code = verifier_manifeste.principal([*fichiers, "--registre", PORTAIL])
    assert code == 0
    assert "0 document(s) refuse(s)" in capsys.readouterr().out


def test_a_corriger_refuse_huit_documents_sur_onze(capsys):
    code = verifier_manifeste.principal([A_CORRIGER, "--registre", PORTAIL])
    assert code == 8
    sortie = capsys.readouterr().out
    assert "A schema publie" in sortie
    assert "B validateur" in sortie
    assert "C references" in sortie


def test_sans_registre_l_agent_fantome_passe(capsys):
    """Sans catalogue, la troisieme couche n'a rien a comparer — et l'outil
    le DIT plutot que de rendre un OK trompeur.
    """
    code = verifier_manifeste.principal([A_CORRIGER])
    assert code == 7
    assert "references NON VERIFIEES" in capsys.readouterr().out


def test_les_exemples_amont_passent_l_outil(capsys):
    from pathlib import Path
    fichiers = [str(p) for p in sorted(Path(AMONT).glob("*.yaml"))]
    assert verifier_manifeste.principal(fichiers) == 0
    capsys.readouterr()


def test_le_mode_muet_ne_dit_que_le_compte(capsys):
    verifier_manifeste.principal([A_CORRIGER, "--registre", PORTAIL, "--muet"])
    sortie = capsys.readouterr().out.strip()
    assert sortie == "8 document(s) refuse(s)"


def test_fiches_du_portail(capsys):
    """Zero repli : les trois serveurs du portail publient ce qu'ils disent."""
    assert fiches.principal([PORTAIL]) == 0
    sortie = capsys.readouterr().out
    assert "1.4.0" in sortie and "0.6.2" in sortie


def test_fiches_d_a_corriger(capsys):
    assert fiches.principal([A_CORRIGER]) == 5
    sortie = capsys.readouterr().out
    assert "0.0.0" in sortie
    assert "MCP server forme-a-plat" in sortie


def test_fiches_sur_un_fichier_sans_serveur(capsys):
    chemin = str(CATALOGUE / "portail" / "prompt-entretien.yaml")
    assert fiches.principal([chemin]) == 0
    assert "aucun MCPServer" in capsys.readouterr().out
