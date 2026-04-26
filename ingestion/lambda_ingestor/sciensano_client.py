"""
Client for Sciensano public health API (Belgium).
https://epistat.sciensano.be
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

SCIENSANO_BASE_URL = "https://epistat.sciensano.be/Data"

ENDPOINTS = {
    "covid_cases_by_age": f"{SCIENSANO_BASE_URL}/COVID19BE_CASES_AGESEX.json",
    "covid_cases_by_province": f"{SCIENSANO_BASE_URL}/COVID19BE_CASES_MUNI_CUM.json",
    "covid_hospitalizations": f"{SCIENSANO_BASE_URL}/COVID19BE_HOSP.json",
    "covid_vaccinations": f"{SCIENSANO_BASE_URL}/COVID19BE_VACC.json",
    "covid_mortality": f"{SCIENSANO_BASE_URL}/COVID19BE_MORT.json",
}


class SciensanoClient:
    """Fetches public health datasets from Sciensano (Belgian health institute)."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def fetch_dataset(self, name: str, url: str) -> Any:
        """Fetch a single dataset by URL."""
        logger.info(f"Fetching Sciensano dataset: {name}")
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_all(self) -> dict[str, Any]:
        """Fetch all configured Sciensano datasets."""
        results = {}
        for name, url in ENDPOINTS.items():
            try:
                results[name] = self.fetch_dataset(name, url)
                logger.info(f"Successfully fetched {name}: {len(results[name])} records")
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch {name}: {e}")
        return results
