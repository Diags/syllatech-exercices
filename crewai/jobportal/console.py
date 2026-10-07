"""La console Windows est en cp1252 : un accent suffit a faire planter un
script. Deux lignes, une fois, et le probleme disparait."""

import sys


def utf8() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:   # noqa: BLE001 - deja en UTF-8, ou flux redirige
            pass


import contextlib
import io as _io


@contextlib.contextmanager
def sans_bruit():
    """Avale les cadres « Flow Execution » que CrewAI dessine a chaque etape.

    Ce n'est pas de la coquetterie : un chapitre dont la sortie utile est
    noyee sous trente lignes de cadres ne s'enseigne pas. Le bruit revient
    d'une ligne — retirez ce gestionnaire et relancez pour le voir.
    """
    tampon = _io.StringIO()
    with contextlib.redirect_stdout(tampon), contextlib.redirect_stderr(tampon):
        yield tampon
