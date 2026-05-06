output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "rds_endpoint" {
  value = aws_db_instance.main.endpoint
}

output "sqs_transactions_url" {
  value = aws_sqs_queue.transactions.url
}

output "sns_topic_arn" {
  value = aws_sns_topic.fraud_alerts.arn
}

output "cloudwatch_dashboard_url" {
  value = "https://${var.region}.console.aws.amazon.com/cloudwatch/home#dashboards:name=${aws_cloudwatch_dashboard.fraud_detection.dashboard_name}"
}
