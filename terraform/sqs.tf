resource "aws_sqs_queue" "transactions" {
  name                      = "fraud-detection-transactions"
  message_retention_seconds = 86400
  visibility_timeout_seconds = 30

  tags = {
    Name = "fraud-detection-transactions"
  }
}

resource "aws_sqs_queue" "fraud_alerts" {
  name                      = "fraud-detection-alerts"
  message_retention_seconds = 86400

  tags = {
    Name = "fraud-detection-alerts"
  }
}
