# Les entrees de la configuration.
#
# Une valeur en dur n'est reutilisable qu'une fois. Les variables la
# sortent du code ; le TYPE et la VALIDATION transforment une faute de
# saisie en message clair, avant meme le plan.

variable "prefixe" {
  type    = string
  default = "jobportal"
}

variable "environnements" {
  type    = set(string)
  default = ["dev", "staging", "prod"]
}

variable "version_image" {
  type    = string
  default = "1.4.0"
}

variable "memoire" {
  type    = number
  default = 512
}

variable "taille" {
  type    = string
  default = "small"

  validation {
    condition     = contains(["small", "medium"], var.taille)
    error_message = "taille doit valoir small ou medium."
  }
}
