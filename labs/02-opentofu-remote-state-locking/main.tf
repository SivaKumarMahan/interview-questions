# Only local resources: nothing is created in any cloud.

variable "release_version" {
  description = "Change this value to create a change that needs an apply."
  type        = string
  default     = "1.0.0"
}

locals {
  # terraform.workspace is "default", "dev", "qa", ... so each workspace gets its own names.
  environment = terraform.workspace
}

resource "random_pet" "app" {
  prefix = local.environment
  length = 2
}

resource "random_password" "db" {
  length  = 20
  special = false
}

resource "terraform_data" "release" {
  input = {
    app         = random_pet.app.id
    environment = local.environment
    version     = var.release_version
  }
}

resource "local_file" "summary" {
  filename        = "${path.module}/out/${local.environment}.txt"
  content         = "app=${random_pet.app.id}\nenvironment=${local.environment}\n"
  file_permission = "0644"
}

output "app_name" {
  value = random_pet.app.id
}

output "db_password" {
  value     = random_password.db.result
  sensitive = true
}
