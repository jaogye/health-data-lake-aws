# ── S3 Buckets: Bronze / Silver / Gold ───────────────────────────────────────

locals {
  zones = ["bronze", "silver", "gold"]
}

resource "aws_s3_bucket" "datalake" {
  for_each = toset(local.zones)
  bucket   = "health-datalake-${each.key}-${var.env}-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_versioning" "datalake" {
  for_each = aws_s3_bucket.datalake
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datalake" {
  for_each = aws_s3_bucket.datalake
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.datalake.arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "datalake" {
  for_each                = aws_s3_bucket.datalake
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: Bronze retained 90 days, Silver/Gold 1 year
resource "aws_s3_bucket_lifecycle_configuration" "bronze" {
  bucket = aws_s3_bucket.datalake["bronze"].id
  rule {
    id     = "expire-bronze"
    status = "Enabled"
    filter {}
    expiration { days = 90 }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "silver_gold" {
  for_each = { for z in ["silver", "gold"] : z => aws_s3_bucket.datalake[z] }
  bucket   = each.value.id
  rule {
    id     = "expire-${each.key}"
    status = "Enabled"
    filter {}
    expiration { days = 365 }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}

# Scripts bucket for Glue jobs
resource "aws_s3_bucket" "glue_scripts" {
  bucket = "health-datalake-glue-scripts-${var.env}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_object" "bronze_to_silver" {
  bucket = aws_s3_bucket.glue_scripts.id
  key    = "glue_jobs/bronze_to_silver.py"
  source = "${path.root}/../transformation/glue_jobs/bronze_to_silver.py"
  etag   = filemd5("${path.root}/../transformation/glue_jobs/bronze_to_silver.py")
}

resource "aws_s3_object" "silver_to_gold" {
  bucket = aws_s3_bucket.glue_scripts.id
  key    = "glue_jobs/silver_to_gold.py"
  source = "${path.root}/../transformation/glue_jobs/silver_to_gold.py"
  etag   = filemd5("${path.root}/../transformation/glue_jobs/silver_to_gold.py")
}
