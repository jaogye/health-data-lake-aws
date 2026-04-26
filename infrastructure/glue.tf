# ── AWS Glue Database & Crawlers ──────────────────────────────────────────────

resource "aws_glue_catalog_database" "health_datalake" {
  name        = "health_datalake_${var.env}"
  description = "Glue Data Catalog for Health Data Lake (Silver + Gold zones)"
}

# ── Glue ETL Jobs ─────────────────────────────────────────────────────────────

resource "aws_glue_job" "bronze_to_silver" {
  name         = "health-datalake-bronze-to-silver-${var.env}"
  role_arn     = aws_iam_role.glue.arn
  glue_version = "4.0"

  command {
    script_location = "s3://${aws_s3_bucket.glue_scripts.bucket}/glue_jobs/bronze_to_silver.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"             = "python"
    "--job-bookmark-option"      = "job-bookmark-enable"
    "--enable-metrics"           = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--BRONZE_BUCKET"            = aws_s3_bucket.datalake["bronze"].bucket
    "--SILVER_BUCKET"            = aws_s3_bucket.datalake["silver"].bucket
    "--TempDir"                  = "s3://${aws_s3_bucket.glue_scripts.bucket}/temp/"
  }

  number_of_workers = 2
  worker_type       = "G.1X"
  timeout           = 60
}

resource "aws_glue_job" "silver_to_gold" {
  name         = "health-datalake-silver-to-gold-${var.env}"
  role_arn     = aws_iam_role.glue.arn
  glue_version = "4.0"

  command {
    script_location = "s3://${aws_s3_bucket.glue_scripts.bucket}/glue_jobs/silver_to_gold.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"             = "python"
    "--job-bookmark-option"      = "job-bookmark-enable"
    "--enable-metrics"           = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--SILVER_BUCKET"            = aws_s3_bucket.datalake["silver"].bucket
    "--GOLD_BUCKET"              = aws_s3_bucket.datalake["gold"].bucket
    "--TempDir"                  = "s3://${aws_s3_bucket.glue_scripts.bucket}/temp/"
  }

  number_of_workers = 2
  worker_type       = "G.1X"
  timeout           = 60
}

# ── Glue Crawlers (auto-discover schema → Data Catalog) ───────────────────────

resource "aws_glue_crawler" "silver" {
  database_name = aws_glue_catalog_database.health_datalake.name
  name          = "health-datalake-silver-crawler-${var.env}"
  role          = aws_iam_role.glue.arn
  description   = "Crawls Silver zone and registers schemas in Glue Data Catalog"

  s3_target {
    path = "s3://${aws_s3_bucket.datalake["silver"].bucket}/silver/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  schedule = "cron(30 6 * * ? *)"  # Daily at 06:30 UTC (after Glue jobs)
}

resource "aws_glue_crawler" "gold" {
  database_name = aws_glue_catalog_database.health_datalake.name
  name          = "health-datalake-gold-crawler-${var.env}"
  role          = aws_iam_role.glue.arn
  description   = "Crawls Gold zone for Athena and QuickSight consumption"

  s3_target {
    path = "s3://${aws_s3_bucket.datalake["gold"].bucket}/gold/"
  }

  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }

  schedule = "cron(0 7 * * ? *)"  # Daily at 07:00 UTC
}
