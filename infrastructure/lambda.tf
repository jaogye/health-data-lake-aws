# ── Lambda Function ───────────────────────────────────────────────────────────

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.root}/../ingestion/lambda_ingestor"
  output_path = "${path.root}/lambda_package.zip"
}

resource "aws_lambda_function" "ingestor" {
  function_name    = "health-datalake-ingestor-${var.env}"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 300
  memory_size      = 1024

  environment {
    variables = {
      BRONZE_BUCKET_NAME = aws_s3_bucket.datalake["bronze"].bucket
      ENV                = var.env
    }
  }

  tracing_config {
    mode = "Active"  # AWS X-Ray tracing
  }

  layers = [aws_lambda_layer_version.requests.arn]
}

resource "aws_lambda_layer_version" "requests" {
  filename            = "${path.root}/layers/requests_layer.zip"
  layer_name          = "health-datalake-requests-${var.env}"
  compatible_runtimes = ["python3.11"]
  description         = "requests library for Lambda"
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.ingestor.function_name}"
  retention_in_days = 30
}

# ── EventBridge Scheduler (daily trigger) ─────────────────────────────────────

resource "aws_cloudwatch_event_rule" "daily_ingestion" {
  name                = "health-datalake-daily-ingestion-${var.env}"
  description         = "Trigger health data ingestion Lambda daily at 02:00 UTC"
  schedule_expression = "cron(0 2 * * ? *)"
  is_enabled          = true
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.daily_ingestion.name
  target_id = "IngestorLambda"
  arn       = aws_lambda_function.ingestor.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_ingestion.arn
}

# ── CloudWatch Alarm: Lambda errors ──────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "health-datalake-lambda-errors-${var.env}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Alert when Lambda ingestion job fails"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.ingestor.function_name
  }
}

resource "aws_sns_topic" "alerts" {
  name = "health-datalake-alerts-${var.env}"
}
