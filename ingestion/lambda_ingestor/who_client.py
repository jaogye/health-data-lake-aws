"""
Client for WHO Global Health Observatory data.
https://covid19.who.int/data
"""

import logging

import requests

logger = logging.getLogger(__name__)

WHO_COVID_URL = "https://covid19.who.int/WHO-COVID-19-global-data.csv"


class WHOClient:
    """Fetches global health datasets from WHO."""

    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.session = requests.Session()

    def fetch_global_covid(self) -> str:
        """Fetch WHO global COVID-19 dataset as CSV string."""
        logger.info("Fetching WHO global COVID-19 data")
        response = self.session.get(WHO_COVID_URL, timeout=self.timeout)
        response.raise_for_status()
        logger.info(f"Fetched WHO data: {len(response.content)} bytes")
        return response.text
