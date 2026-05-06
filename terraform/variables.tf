variable "region" {
  default = "us-east-1"
}

variable "cluster_name" {
  default = "fraud-detection-cluster"
}

variable "db_username" {
  default = "fraudadmin"
}

variable "db_password" {
  sensitive = true
}
