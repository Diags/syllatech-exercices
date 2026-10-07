# Le contenu du module : un reseau, et le conteneur de sa passerelle.
#
# Un module n'est rien d'autre qu'un DOSSIER. Pas de syntaxe speciale,
# pas de declaration : des fichiers `.tf` comme les autres.

resource "reseau" "ce" {
  nom   = var.nom
  plage = var.plage
}

resource "conteneur" "passerelle" {
  nom   = "${var.nom}-passerelle"
  image = "passerelle:1.0.0"
}
