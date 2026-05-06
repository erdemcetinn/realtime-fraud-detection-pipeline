resource "aws_cloudwatch_log_group" "scoring_service" {
  name              = "/fraud-detection/scoring-service"
  retention_in_days = 7
}

resource "aws_cloudwatch_metric_alarm" "sqs_queue_depth" {
  alarm_name          = "fraud-detection-queue-depth"
  alarm_description   = "SQS queue depth is high — scoring service may be falling behind"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions = {
    QueueName = aws_sqs_queue.transactions.name
  }
  statistic           = "Average"
  period              = 60
  evaluation_periods  = 3
  threshold           = 1000
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.fraud_alerts.arn]
}

resource "aws_cloudwatch_dashboard" "fraud_detection" {
  dashboard_name = "fraud-detection"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          title  = "SQS Messages Sent (Transactions Streamed)"
          period = 60
          stat   = "Sum"
          metrics = [
            ["AWS/SQS", "NumberOfMessagesSent", "QueueName", aws_sqs_queue.transactions.name]
          ]
        }
      },
      {
        type = "metric"
        properties = {
          title  = "SQS Messages Deleted (Transactions Processed)"
          period = 60
          stat   = "Sum"
          metrics = [
            ["AWS/SQS", "NumberOfMessagesDeleted", "QueueName", aws_sqs_queue.transactions.name]
          ]
        }
      },
      {
        type = "metric"
        properties = {
          title  = "SQS Queue Depth (Backlog)"
          period = 60
          stat   = "Average"
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.transactions.name]
          ]
        }
      },
      {
        type = "metric"
        properties = {
          title  = "SNS Fraud Alerts Published"
          period = 60
          stat   = "Sum"
          metrics = [
            ["AWS/SNS", "NumberOfMessagesPublished", "TopicName", aws_sns_topic.fraud_alerts.name]
          ]
        }
      }
    ]
  })
}
