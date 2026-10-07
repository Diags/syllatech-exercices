# Une ressource que l'on refuse de detruire par accident.
#
# `prevent_destroy` est un garde-fou de DERNIER recours : il fait
# echouer le plan plutot que de laisser passer une destruction. On le
# pose sur ce qui ne se recree pas — une base de donnees, un bucket de
# sauvegardes, un enregistrement DNS de production.

resource "conteneur" "base" {
  nom   = "jobportal-base"
  image = "postgres:17"

  lifecycle {
    prevent_destroy = true
  }
}

resource "conteneur" "cache" {
  nom   = "jobportal-cache"
  image = "valkey:8"
}
