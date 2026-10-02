# Step 2: store this configuration's state in the bucket created by ../bootstrap.
# use_lockfile = true turns on native S3 locking (OpenTofu 1.10+ / Terraform 1.10+):
# a .tflock object is written next to the state while a plan or apply runs.

terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    bucket       = "lab-tofu-state"
    key          = "app/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true

    access_key                  = "test"
    secret_key                  = "test"
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    use_path_style              = true

    endpoints = {
      s3 = "http://localhost:4566"
    }
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
