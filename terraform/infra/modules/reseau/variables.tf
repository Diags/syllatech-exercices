# Les ENTREES du module : son contrat d'utilisation.
#
# Celui qui appelle ce module n'a pas besoin de savoir ce qu'il y a
# dedans. Il fournit ces deux valeurs, et recupere les sorties.

variable "nom" {
  type = string
}

variable "plage" {
  type    = string
  default = "10.0.0.0/16"
}
