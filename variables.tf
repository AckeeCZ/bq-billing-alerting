variable "sa_file_content" {
  description = "Due to constraints, functions currently loads SA key from give file, pass json SA key"
  default     = ""
}
variable "gcp_project_id" {
  description = "GCP project ID of monitored project"
}
variable "table_with_billing" {
  description = "Full table name used in SQL query"
}
variable "threshold" {
  description = "Given threshold for sku cost, let's say you are interested only in costs above 2 dollars, therefore threshold should be 2"
  default     = "2.5"
}
variable "slack_hook" {
  description = "Slack channel where to whine about the billing issues"
}
variable "opsgenie_token" {
  description = "OpsGenie API token"
  default     = ""
}
variable "opsgenie_endpoint" {
  description = "OpsGenie URL API endpoint"
  default     = "https://api.eu.opsgenie.com/v2/alerts"
}
variable "region" {
  default = "europe-west3"
}

variable "project" {
}

variable "schedule" {
  description = "Cron line for cloud function to be executed at"
  default     = "0 8 * * *"
}

variable "time_zone" {
  description = "Time zone for cron evaluation"
  default     = "Europe/Prague"
}