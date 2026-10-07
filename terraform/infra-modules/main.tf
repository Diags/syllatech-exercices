# La MEME configuration, plus deux instances d'un module.
#
# Le module `reseau` est ecrit une fois, dans `../infra/modules/reseau`,
# et instancie deux fois avec des entrees differentes. C'est le principe
# de la fonction : on definit une fois, on appelle autant qu'on veut.

terraform {
  required_providers {
    local = {
      source  = "syllatech/local"
      version = "1.0.0"
    }
  }
}

module "reseau_prod" {
  source = "../infra/modules/reseau"

  nom   = "jobportal-prod"
  plage = "10.0.0.0/16"
}

module "reseau_staging" {
  source = "../infra/modules/reseau"

  nom   = "jobportal-staging"
  plage = "10.1.0.0/16"
}

output "reseaux" {
  value = [module.reseau_prod.nom_du_reseau, module.reseau_staging.nom_du_reseau]
}
