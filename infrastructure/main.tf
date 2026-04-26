terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "health-datalake-tfstate"
    key    = "health-data-lake/terraform.tfstate"
    region = "eu-west-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "health-data-lake"
      Environment = var.env
      ManagedBy   = "terraform"
      Owner       = "data-engineering"
    }
  }
}

# ── KMS key for S3 encryption ─────────────────────────────────────────────────
resource "aws_kms_key" "datalake" {
  description             = "KMS key for health data lake encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
}

resource "aws_kms_alias" "datalake" {
  name          = "alias/health-datalake-${var.env}"
  target_key_id = aws_kms_key.datalake.key_id
}
