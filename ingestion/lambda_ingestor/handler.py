"""
AWS Lambda handler for public health data ingestion.
Triggered daily by Amazon EventBridge.
Ingests data from Sciensano and WHO APIs → S3 Bronze Zone.
"""

import json
import logging
import os
from datetime import datetime, timezone

import boto3

from sciensano_client import SciensanoClient
from who_client import WHOClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["BRONZE_BUCKET_NAME"]
ENV = os.environ.get("ENV", "dev")


def lambda_handler(event: dict, context) -> dict:
    """
    Main Lambda entrypoint.
    Downloads health data from external APIs and stores in S3 Bronze zone.
    """
    now = datetime.now(timezone.utc)
    run_date = now.strftime("%Y-%m-%d")
    year, month, day = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")

    results = []

    # --- Sciensano: COVID-19 Belgium ---
    try:
        sciensano_client = SciensanoClient()
        datasets = sciensano_client.fetch_all()
        for name, data in datasets.items():
            key = f"bronze/sciensano/{name}/year={year}/month={month}/day={day}/data.json"
            _upload_to_s3(data, key)
            results.append({"source": f"sciensano/{name}", "status": "success", "key": key})
            logger.info(f"Uploaded {name} to s3://{BUCKET_NAME}/{key}")
    except Exception as e:
        logger.error(f"Sciensano ingestion failed: {e}")
        results.append({"source": "sciensano", "status": "failed", "error": str(e)})

    # --- WHO: Global COVID-19 ---
    try:
        who_client = WHOClient()
        data = who_client.fetch_global_covid()
        key = f"bronze/who/global_covid/year={year}/month={month}/day={day}/data.csv"
        _upload_to_s3(data, key, content_type="text/csv")
        results.append({"source": "who/global_covid", "status": "success", "key": key})
        logger.info(f"Uploaded WHO data to s3://{BUCKET_NAME}/{key}")
    except Exception as e:
        logger.error(f"WHO ingestion failed: {e}")
        results.append({"source": "who", "status": "failed", "error": str(e)})

    # --- Write ingestion manifest ---
    manifest = {
        "run_date": run_date,
        "run_timestamp": now.isoformat(),
        "env": ENV,
        "results": results,
    }
    manifest_key = f"bronze/_manifests/{run_date}/manifest.json"
    _upload_to_s3(json.dumps(manifest, indent=2), manifest_key)

    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(f"Ingestion complete: {success_count}/{len(results)} sources successful")

    return {
        "statusCode": 200,
        "body": json.dumps(manifest),
    }


def _upload_to_s3(data, key: str, content_type: str = "application/json") -> None:
    """Upload string data to S3."""
    if isinstance(data, (dict, list)):
        data = json.dumps(data, ensure_ascii=False)
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=data.encode("utf-8") if isinstance(data, str) else data,
        ContentType=content_type,
        ServerSideEncryption="aws:kms",
    )
