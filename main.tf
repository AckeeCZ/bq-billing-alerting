locals {
  name_prefix = "bg-billing-alerting"
}

data "archive_file" "code_package" {
  type        = "zip"
  output_path = "${path.module}/code.zip"

  source {
    content  = file("${path.module}/code/main.py")
    filename = "main.py"
  }
  source {
    content  = file("${path.module}/code/requirements.txt")
    filename = "requirements.txt"
  }
  source {
    content  = var.sa_file_content
    filename = "sa.json"
  }
}

resource "random_string" "random_postfix" {
  length  = 8
  special = false
  lower   = true
  upper   = false
}

resource "google_storage_bucket" "deploy_bucket" {
  name          = "${local.name_prefix}-cf-${random_string.random_postfix.result}"
  force_destroy = true
  location      = "EUROPE-WEST3"
}

resource "google_storage_bucket_object" "archive" {
  name   = "code.zip"
  bucket = google_storage_bucket.deploy_bucket.name
  source = "${path.module}/code.zip"
}

resource "google_cloudfunctions_function" "function" {
  name        = local.name_prefix
  description = "BigQuery cloud function executing multiple queries on exported billing to evaluate possible changes"
  runtime     = "python38"
  region      = var.region

  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.deploy_bucket.name
  source_archive_object = google_storage_bucket_object.archive.name
  trigger_http          = true
  timeout               = 30
  entry_point           = "main"
  ingress_settings      = "ALLOW_ALL"

  environment_variables = {
    GCP_PROJECT_ID     = var.gcp_project_id
    TABLE_WITH_BILLING = var.table_with_billing
    THRESHOLD          = var.threshold
    SLACK_HOOK         = var.slack_hook
    OPSGENIE_TOKEN     = var.opsgenie_token
    OPSGENIE_ENDPOINT  = var.opsgenie_endpoint
  }
}

resource "google_service_account" "invoker" {
  project      = var.project
  account_id   = "${local.name_prefix}-invoker"
  display_name = "SA used to execute ${local.name_prefix}"
}

resource "google_cloudfunctions_function_iam_member" "invoker" {
  project        = google_cloudfunctions_function.function.project
  region         = google_cloudfunctions_function.function.region
  cloud_function = google_cloudfunctions_function.function.name

  role   = "roles/cloudfunctions.invoker"
  member = "serviceAccount:${google_service_account.invoker.email}"
}

resource "google_cloud_scheduler_job" "job" {
  name             = "${local.name_prefix}-cron"
  description      = "Execute billing check"
  schedule         = var.schedule
  time_zone        = var.time_zone
  attempt_deadline = "60s"
  region           = var.region

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "GET"
    uri         = google_cloudfunctions_function.function.https_trigger_url

    oidc_token {
      service_account_email = google_service_account.invoker.email
    }
  }
}
