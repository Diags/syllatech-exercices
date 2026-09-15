"""Bascule `HERMES_HOME` AVANT que pytest n'importe quoi que ce soit.

Importer un module de Hermes cree son dossier de travail — SOUL.md, state.db,
sessions/, logs/ — dans %LOCALAPPDATA%\\hermes ou ~/.hermes. Une suite de
tests ne doit pas laisser cela derriere elle.

`jobportal.commun` fait la meme bascule, mais un conftest est importe plus
tot : il couvre aussi le cas ou un test importerait Hermes sans passer par
`jobportal`.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HERMES_HOME",
                      tempfile.mkdtemp(prefix="hermes-tests-"))

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
