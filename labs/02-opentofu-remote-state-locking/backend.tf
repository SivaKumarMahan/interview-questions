# Remote state in PostgreSQL. The pg backend stores each workspace as one row
# in terraform_remote_state.states and locks it with a PostgreSQL advisory lock.
#
# The connection details come from environment variables, so no password is in
# this file:
#   PG_CONN_STR = postgres://tofu@localhost:15432/tofu_state?sslmode=disable
#   PGPASSWORD  = the value from .env

terraform {
  required_version = ">= 1.6.0"

  backend "pg" {}

  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}
