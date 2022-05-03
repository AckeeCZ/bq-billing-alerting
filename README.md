# Terraform BigQuery Alerting Module

This is a test case to execute BQ queries on exported billing dataset. Based on the results, the cloud function
compares the values from averages. Once an average of the recent day goes over an average of the past value range,
a message is generated. The message can be submitted to Slack and OpsGenie.

Cloud function compares SKU averages from yesterday and the day before yesterday with averages from past two weeks.
That is because plenty of SKUs are billed with delay in day or two. The comparison also adds a threshold in case
the SKU value is insignificant. The condition looks like this:

```python
{comparable_skus[r.sku_description]} > {ratio} * {r.avg_sku_cost} and {r.avg_sku_cost} > {THRESHOLD}
```

Where `ratio` is 2 for values twice as bigger as the values from the past two weeks and 1.5 for values one and
half bigger than values from the past two weeks.

Once any SKUs are breaching the condition, the message is generated and sent to Slack or OpsGenie.

## SA key and access to bigquery dataset

Due to issues with allowing SA of Cloud function, the function uses SA key file instead. This is a security issue
because users can access the source code and use the SA for malicious operations.

## Before you do anything in this module

Install pre-commit hooks by running following commands:

```shell script
brew install pre-commit
pre-commit install
```

<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_archive"></a> [archive](#provider\_archive) | n/a |
| <a name="provider_google"></a> [google](#provider\_google) | n/a |
| <a name="provider_random"></a> [random](#provider\_random) | n/a |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_cloud_scheduler_job.job](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_scheduler_job) | resource |
| [google_cloudfunctions_function.function](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloudfunctions_function) | resource |
| [google_cloudfunctions_function_iam_member.invoker](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloudfunctions_function_iam_member) | resource |
| [google_service_account.invoker](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/service_account) | resource |
| [google_storage_bucket.deploy_bucket](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket) | resource |
| [google_storage_bucket_object.archive](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket_object) | resource |
| [random_string.random_postfix](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/string) | resource |
| [archive_file.code_package](https://registry.terraform.io/providers/hashicorp/archive/latest/docs/data-sources/file) | data source |

## Inputs

| Name                                                                                                     | Description                                                                                                               | Type     | Default                                   | Required |
|----------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|----------|-------------------------------------------|:--------:|
| <a name="input_gcp_project_id"></a> [gcp\_project\_id](#input\_gcp\_project\_id)                         | GCP project ID of monitored project                                                                                       | `any`    | n/a                                       |   yes    |
| <a name="input_opsgenie_endpoint"></a> [opsgenie\_endpoint](#input\_opsgenie\_endpoint)                  | OpsGenie URL API endpoint                                                                                                 | `string` | `"https://api.eu.opsgenie.com/v2/alerts"` |    no    |
| <a name="input_opsgenie_token"></a> [opsgenie\_token](#input\_opsgenie\_token)                           | OpsGenie API token                                                                                                        | `string` | `""`                                      |    no    |
| <a name="input_project"></a> [project](#input\_project)                                                  | n/a                                                                                                                       | `any`    | n/a                                       |   yes    |
| <a name="input_region"></a> [region](#input\_region)                                                     | n/a                                                                                                                       | `string` | `"europe-west3"`                          |    no    |
| <a name="input_sa_file_content"></a> [sa\_file\_content](#input\_sa\_file\_content)                      | Due to constraints, functions currently loads SA key from give file, pass json SA key                                     | `string` | `""`                                      |    no    |
| <a name="input_schedule"></a> [schedule](#input\_schedule)                                               | Cron line for cloud function to be executed at                                                                            | `string` | `"0 8 * * *"`                             |    no    |
| <a name="input_slack_hook"></a> [slack\_hook](#input\_slack\_hook)                                       | Slack channel where to whine about the billing issues                                                                     | `any`    | n/a                                       |   yes    |
| <a name="input_table_with_billing"></a> [table\_with\_billing](#input\_table\_with\_billing)             | Full table name used in SQL query                                                                                         | `any`    | n/a                                       |   yes    |
| <a name="input_threshold"></a> [threshold](#input\_threshold)                                            | Given threshold for sku cost, let's say you are interested only in costs above 2 dollars, therefore threshold should be 2 | `string` | `"2.5"`                                   |    no    |
| <a name="input_second_alert_threshold"></a> [second\_alert\_threshold](#input\_second\_alert\_threshold) | If there is any sku cost over this threshold, second alert will be sent.                                                  | `string` | `"30"`                                    |    no    |
| <a name="input_time_zone"></a> [time\_zone](#input\_time\_zone)                                          | Time zone for cron evaluation                                                                                             | `string` | `"Europe/Prague"`                         |    no    |
| <a name="input_minimum_cost"></a> [minimum\_cost](#input\_minimum\_cost)                                 | Minimum amount of SKU cost per day to be included in average calculation                                                  | `string` | `"0.5"`                                   |    no    |

## Outputs

No outputs.
<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->
