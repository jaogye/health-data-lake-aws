"""
Tests for Lambda ingestion layer.
Run with: pytest tests/ -v
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from sciensano_client import SciensanoClient
from who_client import WHOClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def lambda_env(monkeypatch):
    monkeypatch.setenv("BRONZE_BUCKET_NAME", "test-bronze-bucket")
    monkeypatch.setenv("ENV", "test")


@pytest.fixture
def sample_hospitalization_record():
    return {
        "DATE": "2024-01-15",
        "PROVINCE": "BrabantWallon",
        "REGION": "Wallonia",
        "NR_REPORTING": 5,
        "TOTAL_IN": 120,
        "TOTAL_IN_ICU": 18,
        "TOTAL_IN_RESP": 10,
        "TOTAL_IN_ECMO": 1,
        "NEW_IN": 15,
        "NEW_OUT": 12,
    }


@pytest.fixture
def sample_vaccination_record():
    return {
        "DATE": "2024-01-15",
        "REGION": "Flanders",
        "AGEGROUP": "25-34",
        "SEX": "F",
        "BRAND": "COM",
        "DOSE": "B",
        "COUNT": 1234,
    }


# ── Sciensano client tests ─────────────────────────────────────────────────────

class TestSciensanoClient:

    def test_fetch_dataset_success(self, sample_hospitalization_record):
        """Sciensano client parses JSON response correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = [sample_hospitalization_record]
        mock_response.raise_for_status.return_value = None

        with patch("requests.Session.get", return_value=mock_response):
            client = SciensanoClient()
            result = client.fetch_dataset("covid_hosp", "https://fake.url/data.json")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["DATE"] == "2024-01-15"
        assert result[0]["REGION"] == "Wallonia"

    def test_fetch_all_handles_partial_failures(self):
        """fetch_all() continues despite individual endpoint failures."""
        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise requests.RequestException("Network error")
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"DATE": "2024-01-15"}]
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        with patch("requests.Session.get", side_effect=mock_get):
            client = SciensanoClient()
            results = client.fetch_all()

        assert isinstance(results, dict)


# ── WHO client tests ───────────────────────────────────────────────────────────

class TestWHOClient:

    def test_fetch_global_covid_returns_csv(self):
        """WHO client returns CSV string."""
        csv_content = (
            "Date_reported,Country_code,Country,WHO_region,"
            "New_cases,Cumulative_cases,New_deaths,Cumulative_deaths\n"
            "2024-01-15,BE,Belgium,EURO,100,3000000,2,30000\n"
        )

        mock_response = MagicMock()
        mock_response.text = csv_content
        mock_response.content = csv_content.encode()
        mock_response.raise_for_status.return_value = None

        with patch("requests.Session.get", return_value=mock_response):
            client = WHOClient()
            result = client.fetch_global_covid()

        assert "Date_reported" in result
        assert "Belgium" in result
        assert isinstance(result, str)


# ── Lambda handler tests ───────────────────────────────────────────────────────

class TestLambdaHandler:

    def test_handler_returns_200_on_success(self, lambda_env, sample_hospitalization_record):
        """Lambda handler returns HTTP 200 on successful ingestion."""
        mock_s3 = MagicMock()
        mock_sciensano = MagicMock()
        mock_sciensano.fetch_all.return_value = {
            "covid_hospitalizations": [sample_hospitalization_record]
        }
        mock_who = MagicMock()
        mock_who.fetch_global_covid.return_value = "Date_reported,Country\n2024-01-15,Belgium\n"

        with patch("boto3.client", return_value=mock_s3), \
             patch("handler.SciensanoClient", return_value=mock_sciensano), \
             patch("handler.WHOClient", return_value=mock_who):

            import handler
            importlib.reload(handler)

            response = handler.lambda_handler({}, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "results" in body

    def test_handler_partial_failure_still_returns_200(self, lambda_env):
        """Lambda returns 200 even if one source fails, reporting partial results."""
        mock_s3 = MagicMock()
        mock_sciensano = MagicMock()
        mock_sciensano.fetch_all.side_effect = Exception("API timeout")
        mock_who = MagicMock()
        mock_who.fetch_global_covid.return_value = "Date_reported\n2024-01-15\n"

        import handler
        importlib.reload(handler)

        with patch.object(handler, "s3", mock_s3), \
             patch("handler.SciensanoClient", return_value=mock_sciensano), \
             patch("handler.WHOClient", return_value=mock_who):

            response = handler.lambda_handler({}, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        failed = [r for r in body["results"] if r["status"] == "failed"]
        assert len(failed) >= 1
