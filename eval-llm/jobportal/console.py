"""Rendre la sortie lisible, y compris sous Windows.

La console Windows est en cp1252 par defaut : un simple accent, un tiret
cadratin ou une fleche suffit a faire planter un `print` avec une
UnicodeEncodeError — apres que le travail utile a ete fait, ce qui est le
pire moment pour echouer.

Appelez `utf8()` au debut de votre `main()`. Sous Linux et macOS, l'appel ne
fait rien : la sortie y est deja en UTF-8.
"""

import sys


def utf8() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:   # noqa: BLE001 — flux redirige, ou deja en UTF-8
            pass
