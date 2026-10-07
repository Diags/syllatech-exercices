# L'infrastructure du portail de l'emploi.
#
# Tout est declaratif : on decrit l'etat VOULU, jamais la suite
# d'operations. Le moteur calcule le chemin le plus court entre ce
# fichier et ce qui existe deja.

terraform {
  required_providers {
    local = {
      source  = "syllatech/local"
      version = "1.0.0"
    }
  }
}

# Une instance par environnement, indexee par sa CLE.
resource "conteneur" "app" {
  for_each = var.environnements

  nom     = "${var.prefixe}-${each.key}"
  image   = "jobportal:${var.version_image}"
  memoire = var.memoire
}

output "conteneurs" {
  value = { for cle, instance in conteneur.app : cle => instance.nom }
}
