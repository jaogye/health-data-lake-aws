output "bronze_bucket_name" {
  description = "S3 Bronze zone bucket name"
  value       = aws_s3_bucket.datalake["bronze"].bucket
}

output "silver_bucket_name" {
  description = "S3 Silver zone bucket name"
  value       = aws_s3_bucket.datalake["silver"].bucket
}

output "gold_bucket_name" {
  description = "S3 Gold zone bucket name"
  value       = aws_s3_bucket.datalake["gold"].bucket
}

output "glue_database_name" {
  description = "Glue Data Catalog database name"
  value       = aws_glue_catalog_database.health_datalake.name
}

output "lambda_function_name" {
  description = "Lambda ingestor function name"
  value       = aws_lambda_function.ingestor.function_name
}
