"""
Azure Function handler for public health data ingestion.
Triggered daily by timer schedule (02:00 UTC).
Ingests data from Sciensano and WHO APIs → ADLS Gen2 Bronze Zone.
"""

import json
import logging
import os
from datetime import datetime, timezone
import azure.functions as func
from azure.storage.blob import BlobServiceClient, ContentSettings

from ..sciensano_client import SciensanoClient
from ..who_client import WHOClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

STORAGE_ACCOUNT_NAME = os.environ["STORAGE_ACCOUNT_NAME"]
STORAGE_ACCOUNT_KEY = os.environ["AzureWebJobsStorage"]
BRONZE_CONTAINER_NAME = os.environ["BRONZE_CONTAINER_NAME"]
ENV = os.environ.get("ENV", "dev")

blob_service_client = BlobServiceClient(
    account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=STORAGE_ACCOUNT_KEY
)


def main(mytimer: func.TimerRequest = None) -> dict:
    """
    Azure Functions entrypoint (timer trigger).
    Downloads health data from external APIs and stores in ADLS Gen2 Bronze zone.
    """
    now = datetime.now(timezone.utc)
    run_date = now.strftime("%Y-%m-%d")
    year, month, day = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")

    results = []

    container_client = blob_service_client.get_container_client(BRONZE_CONTAINER_NAME)

    # --- Sciensano: COVID-19 Belgium ---
    try:
        sciensano_client = SciensanoClient()
        datasets = sciensano_client.fetch_all()
        for name, data in datasets.items():
            key = f"sciensano/{name}/year={year}/month={month}/day={day}/data.json"
            _upload_to_adls(container_client, data, key)
            results.append({"source": f"sciensano/{name}", "status": "success", "key": key})
            logger.info(f"Uploaded {name} to {STORAGE_ACCOUNT_NAME}/{BRONZE_CONTAINER_NAME}/{key}")
    except Exception as e:
        logger.error(f"Sciensano ingestion failed: {e}")
        results.append({"source": "sciensano", "status": "failed", "error": str(e)})

    # --- WHO: Global COVID-19 ---
    try:
        who_client = WHOClient()
        data = who_client.fetch_global_covid()
        key = f"who/global_covid/year={year}/month={month}/day={day}/data.csv"
        _upload_to_adls(container_client, data, key, content_type="text/csv")
        results.append({"source": "who/global_covid", "status": "success", "key": key})
        logger.info(f"Uploaded WHO data to {STORAGE_ACCOUNT_NAME}/{BRONZE_CONTAINER_NAME}/{key}")
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
    manifest_key = f"_manifests/{run_date}/manifest.json"
    _upload_to_adls(container_client, json.dumps(manifest, indent=2), manifest_key)

    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(f"Ingestion complete: {success_count}/{len(results)} sources successful")

    return {
        "statusCode": 200,
        "body": json.dumps(manifest),
    }


def _upload_to_adls(container_client, data, blob_name: str, content_type: str = "application/json") -> None:
    """Upload string data to ADLS Gen2."""
    if isinstance(data, (dict, list)):
        data = json.dumps(data, ensure_ascii=False)
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(
        data.encode("utf-8") if isinstance(data, str) else data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type)
    )