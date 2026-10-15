terraform {
  required_version = ">= 1.10, < 2.0"
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
provider "aws" {
  region = "eu-west-2"
  default_tags {
    tags = { Project = "LedgerGuard", ManagedBy = "Terraform" }
  }
}
resource "aws_sqs_queue" "dead" {
  name = "ledgerguard-dead"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled = true
}
resource "aws_sqs_queue" "jobs" {
  name = "ledgerguard-jobs"
  visibility_timeout_seconds = 120
  message_retention_seconds = 345600
  sqs_managed_sse_enabled = true
  redrive_policy = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dead.arn, maxReceiveCount = 3 })
}
resource "aws_sqs_queue_redrive_allow_policy" "dead" {
  queue_url = aws_sqs_queue.dead.id
  redrive_allow_policy = jsonencode({ redrivePermission = "byQueue", sourceQueueArns = [aws_sqs_queue.jobs.arn] })
}
resource "aws_sqs_queue_policy" "jobs" {
  queue_url = aws_sqs_queue.jobs.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Sid = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "sqs:*", Resource = aws_sqs_queue.jobs.arn, Condition = { Bool = { "aws:SecureTransport" = "false" } } }] })
}
resource "aws_cloudwatch_metric_alarm" "dead" {
  alarm_name = "ledgerguard-dead-letter-messages"
  namespace = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  dimensions = { QueueName = aws_sqs_queue.dead.name }
  statistic = "Maximum"
  period = 60
  evaluation_periods = 1
  comparison_operator = "GreaterThanThreshold"
  threshold = 0
  treat_missing_data = "notBreaching"
}
output "job_queue_arn" { value = aws_sqs_queue.jobs.arn }
