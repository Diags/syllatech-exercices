"""La console Windows est en cp1252 : un accent suffit a faire planter un
script. Deux lignes, une fois, et le probleme disparait."""

import sys


def utf8() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:   # noqa: BLE001 - deja en UTF-8, ou flux redirige
            pass
