import logging
from pprint import pprint
from typing import List
import requests
from itertools import chain

from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
from breakout import breakout
import os

import matplotlib.pyplot as plt
import numpy as np

LOG_LEVEL = os.environ.get('LOG_LEVEL', "INFO")
logging.basicConfig(level=LOG_LEVEL)

GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', None)
GCP_SA_KEY_FILE = os.environ.get('GCP_SA_KEY_FILE', "sa.json")
FUNCTION_REGION = os.environ.get('FUNCTION_REGION', "europe-west3")
FUNCTION_NAME = os.environ.get('FUNCTION_NAME', "bg-billing-alerting")
OPSGENIE_TOKEN = os.environ.get('OPSGENIE_TOKEN', "")
OPSGENIE_ENDPOINT = os.environ.get('OPSGENIE_ENDPOINT', "https://api.eu.opsgenie.com/v2/alerts")
TABLE_WITH_BILLING = os.environ.get('TABLE_WITH_BILLING', None)
THRESHOLD = int(os.environ.get("THRESHOLD", 0))
SLACK_HOOK = os.environ.get("SLACK_HOOK", None)
SECOND_ALERT_THRESHOLD = os.environ.get("SECOND_ALERT_THRESHOLD", 30)
MINIMUM_COST = os.environ.get("MINIMUM_COST", 0.5)


def main(_):

    credentials = service_account.Credentials.from_service_account_file(
        GCP_SA_KEY_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    client = bigquery.Client(credentials=credentials, project=credentials.project_id,)

    datetime_now = datetime.now()
    three_days_before_yesterday = (datetime_now - timedelta(days=3)).strftime("%Y-%m-%d")
    past_two_weeks = (datetime_now - timedelta(days=17)).strftime("%Y-%m-%d")

    # query_past_data = """
    # SELECT DISTINCT sku_description,
    # VAR_SAMP (sku_cost) OVER (windows_sku_description) AS var_sku_cost,
    # AVG (sku_cost) OVER (windows_sku_description) AS avg_sku_cost,
    # MAX (sku_cost) OVER (windows_sku_description) AS max_sku_cost,
    # MIN (sku_cost) OVER (windows_sku_description) AS min_sku_cost,
    # VAR_SAMP (sku_cost_with_credits) OVER (windows_sku_description) AS var_sku_cost_with_credits,
    # AVG (sku_cost_with_credits) OVER (windows_sku_description) AS avg_sku_cost_with_credits,
    # MAX (sku_cost_with_credits) OVER (windows_sku_description) AS max_sku_cost_with_credits,
    # MIN (sku_cost_with_credits) OVER (windows_sku_description) AS min_sku_cost_with_credits,
    # FROM (
    #     SELECT sku.description AS sku_description, SUM (cost) OVER (PARTITION BY sku.id, _PARTITIONTIME) AS sku_cost,
    #     (SUM (cost) OVER (PARTITION BY sku.id, _PARTITIONTIME) + SUM(IFNULL((
    #           SELECT
    #             SUM(c.amount)
    #           FROM
    #             UNNEST(credits) c),
    #           0)) OVER (PARTITION BY sku.id, _PARTITIONTIME)) AS sku_cost_with_credits
    #     FROM `{TABLE_WITH_BILLING}`
    #     WHERE DATE(_PARTITIONTIME) > "{past_two_weeks}" AND DATE(_PARTITIONTIME) < "{three_days_before_yesterday}" AND project.id = "{GCP_PROJECT_ID}"
    # )
    # WHERE (sku_cost > {MINIMUM_COST}) # Filter out values which we know are surely bellow average
    # WINDOW windows_sku_description AS (
    #     PARTITION BY sku_description
    # )
    # ORDER BY avg_sku_cost DESC
    # """.format(
    #     three_days_before_yesterday=three_days_before_yesterday,
    #     past_two_weeks=past_two_weeks,
    #     GCP_PROJECT_ID=GCP_PROJECT_ID,
    #     TABLE_WITH_BILLING=TABLE_WITH_BILLING,
    #     MINIMUM_COST=MINIMUM_COST
    # )

    query_past_data = """
        SELECT sku.description AS sku_description, cost
        FROM `{TABLE_WITH_BILLING}`
        WHERE DATE(_PARTITIONTIME) > "{past_two_weeks}" AND DATE(_PARTITIONTIME) < "{three_days_before_yesterday}" AND project.id = "{GCP_PROJECT_ID}"
    """.format(
        three_days_before_yesterday=three_days_before_yesterday,
        past_two_weeks=past_two_weeks,
        GCP_PROJECT_ID=GCP_PROJECT_ID,
        TABLE_WITH_BILLING=TABLE_WITH_BILLING,
        MINIMUM_COST=MINIMUM_COST
    )

    job_config = bigquery.QueryJobConfig()

    query_past_data_job = client.query(query_past_data, job_config=job_config)

    pprint(query_past_data_job.result())
    results = {}
    for r in query_past_data_job.result():
        results[r.sku_description] = results.get(r.sku_description, []) + [r.cost]
    pprint(results)
    for k in results:
        print(k)
        breakout_data = breakout(
            results[k],
            min_size=5,  # minimum observations between breakouts
            method='multi',  # multi or amoc (at most one change)
            degree=1,  # degree of the penalization polynomial (multi only)
            beta=0.001,  # penalization term (multi only)
            percent=None,  # minimum percent change in goodness of fit statistic (multi only)
            # alpha=2,  # weight of the distance between observations (amoc only)
            exact=True  # exact or approximate median (amoc only)
        )
        pprint(breakout_data)
        if len(breakout_data):
            plt.figure(figsize=(10, 5))
            for i in breakout_data:
                plt.axvline(x=i, color='b')
            plt.plot(results[k])
            # rendering plot
            plt.show()
        print("=======================")
    return ""

    query_day_before_yesterday_job = client.query(query_day_before_yesterday, job_config=job_config)
    query_day_yesterday_job = client.query(query_yesterday, job_config=job_config)

    # Get difference in avg as twice as much to avg of past data
    comparable_skus = {
      i.sku_description: i.avg_sku_cost for i in
      chain(query_day_yesterday_job.result(), query_day_before_yesterday_job.result())
    }

    def get_rising_avg_by_ratio(ratio) -> List[str]:
        worst_skus = []
        for r in query_past_data_job.result():
            if r.sku_description in comparable_skus:
                if comparable_skus[r.sku_description] > ratio * r.avg_sku_cost and r.avg_sku_cost > THRESHOLD:
                    logging.info(
                        f"{r.sku_description}: {comparable_skus[r.sku_description]}" +
                        f" > {ratio} * {r.avg_sku_cost} and {r.avg_sku_cost} > {THRESHOLD}"
                        f" cost amount with credits included {r.avg_sku_cost_with_credits}"
                    )

                    if r.sku_description not in worst_skus:
                        worst_skus.append(r.sku_description)
                    del comparable_skus[r.sku_description]
        return worst_skus

    error_msg = ""

    worst_skus = get_rising_avg_by_ratio(2)

    if len(worst_skus):
        error_msg += "Following SKUs' averages are at least twice as high as averages from the past two weeks:\n  * "
        error_msg += "\n  * ".join(worst_skus)
        error_msg += "\n"

    # For those which are not twice as high, check 1.5 higher

    worst_skus = get_rising_avg_by_ratio(1.5)
    if len(worst_skus):
        error_msg += "Following SKUs' averages are at least half as high as averages from the past two weeks:\n  * "
        error_msg += "\n  * ".join(worst_skus)
        error_msg += "\n"

    if len(error_msg):
        error_msg += "For further details, go to https://console.cloud.google.com/billing/linkedaccount?project={project}".format(
            project=GCP_PROJECT_ID
        )
        error_msg += "\nIn case you need further logs, go to "
        error_msg += "https://console.cloud.google.com/functions/details/"
        error_msg += f"{FUNCTION_REGION}/{FUNCTION_NAME}?project={GCP_PROJECT_ID}&tab=logs"
        error_msg += "\nNOTE: this alert won't close itself, inspect the issue and close it"
        send_alert(f'Billing alert on {GCP_PROJECT_ID}', error_msg)

        comparable_skus = {
            i.sku_description: i.avg_sku_cost for i in
            chain(query_day_yesterday_job.result(), query_day_before_yesterday_job.result())
        }
        for sku in worst_skus:
            if comparable_skus[sku] > SECOND_ALERT_THRESHOLD:
                msg = f"{sku} is at least half as high as average from the past two weeks and is above {SECOND_ALERT_THRESHOLD}."
                msg += f"\n - Current price for {sku} is {comparable_skus[sku]}."
                msg += f"\nPlease investigate thoroughly last reports for this SKU."
                msg += "\nIn case you need further logs, go to "
                msg += "https://console.cloud.google.com/functions/details/"
                msg += f"{FUNCTION_REGION}/{FUNCTION_NAME}?project={GCP_PROJECT_ID}&tab=logs"
                msg += "\nNOTE: this alert won't close itself, inspect the issue and close it"
                send_alert(f'Billing alert on {GCP_PROJECT_ID} - {sku}', msg, "P1")
                logging.warning(msg)

    return error_msg


def send_alert(title, error_msg, priority="P3"):
    if SLACK_HOOK is not None and len(SLACK_HOOK):
        requests.post(SLACK_HOOK, json={'text': error_msg})
    if len(OPSGENIE_TOKEN):
        requests.post(
            OPSGENIE_ENDPOINT,
            headers={
                'Content-Type': "application/json",
                'Authorization': f'GenieKey {OPSGENIE_TOKEN}'
            },
            json={
                "message": title,
                "description": error_msg,
                "priority": priority
            }
        )


if __name__ == '__main__':
    pprint(main(""))
