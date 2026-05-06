resource "aws_sns_topic" "fraud_alerts" {
  name = "fraud-detection-alerts"

  tags = {
    Name = "fraud-detection-alerts"
  }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.fraud_alerts.arn
  protocol  = "email"
  endpoint  = "cetin.er@northeastern.edu"
}
