#!/usr/bin/env sh
# initializeCommand : la SEULE commande qui tourne sur votre machine.
# Elle sert a verifier un prerequis local avant que la construction parte.
set -e
command -v docker >/dev/null 2>&1 || {
  echo "Docker est introuvable sur l'hote." >&2
  exit 1
}
echo "hote verifie"
