provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  s3_use_path_style           = true

  endpoints {
    s3  = "http://localhost:4566"
    sts = "http://localhost:4566"
  }

  default_tags {
    tags = {
      project    = "devops-labs"
      managed_by = "opentofu"
    }
  }
}

variable "environment" {
  description = "Environment name used in the bucket name."
  type        = string
  default     = "dev"
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "lab-${var.environment}-artifacts"
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_object" "readme" {
  bucket  = aws_s3_bucket.artifacts.id
  key     = "hello.txt"
  content = "Created by OpenTofu against LocalStack.\n"
}

output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}
