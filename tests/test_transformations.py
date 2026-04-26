"""
Tests for data quality checks module.
Uses PySpark local session to test transformations.
"""

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

from checks import check_allowed_values, check_no_duplicates, check_not_null, check_value_range


@pytest.fixture(scope="session")
def spark():
    """Create a local Spark session for testing."""
    return (
        SparkSession.builder
        .master("local[1]")
        .appName("health-datalake-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )


@pytest.fixture
def hosp_schema():
    return StructType([
        StructField("date", StringType(), True),
        StructField("province", StringType(), True),
        StructField("region", StringType(), True),
        StructField("total_in", IntegerType(), True),
        StructField("total_in_icu", IntegerType(), True),
        StructField("new_in", IntegerType(), True),
        StructField("new_out", IntegerType(), True),
    ])


@pytest.fixture
def clean_hosp_df(spark, hosp_schema):
    data = [
        ("2024-01-15", "Antwerp", "Flanders", 200, 30, 25, 20),
        ("2024-01-15", "Ghent", "Flanders", 150, 20, 18, 15),
        ("2024-01-15", "Brussels", "Brussels", 80, 15, 10, 8),
        ("2024-01-15", "Liège", "Wallonia", 120, 18, 12, 10),
    ]
    return spark.createDataFrame(data, hosp_schema)


@pytest.fixture
def dirty_hosp_df(spark, hosp_schema):
    data = [
        ("2024-01-15", "Antwerp", "Flanders", 200, 30, 25, 20),
        ("2024-01-15", "Antwerp", "Flanders", 200, 30, 25, 20),  # duplicate
        (None, "Ghent", "Flanders", 150, 20, 18, 15),            # null date
        ("2024-01-15", "Brussels", "Brussels", -10, 15, 10, 8),  # negative value
    ]
    return spark.createDataFrame(data, hosp_schema)


class TestNotNullCheck:

    def test_passes_when_no_nulls(self, clean_hosp_df):
        result = check_not_null(clean_hosp_df, "date")
        assert result["passed"] is True
        assert result["actual"] == 1.0

    def test_fails_when_nulls_exceed_threshold(self, dirty_hosp_df):
        result = check_not_null(dirty_hosp_df, "date", threshold=0.95)
        assert result["passed"] is False
        assert result["actual"] < 0.95


class TestNoDuplicatesCheck:

    def test_passes_with_clean_data(self, clean_hosp_df):
        result = check_no_duplicates(clean_hosp_df, ["date", "province", "region"])
        assert result["passed"] is True
        assert result["total_rows"] == result["distinct_rows"]

    def test_fails_with_duplicates(self, dirty_hosp_df):
        result = check_no_duplicates(dirty_hosp_df, ["date", "province", "region"])
        assert result["passed"] is False
        assert result["total_rows"] > result["distinct_rows"]


class TestValueRangeCheck:

    def test_passes_within_range(self, clean_hosp_df):
        result = check_value_range(clean_hosp_df, "total_in", 0, 100_000)
        assert result["passed"] is True
        assert result["out_of_range_rows"] == 0

    def test_fails_with_negative_values(self, dirty_hosp_df):
        result = check_value_range(dirty_hosp_df, "total_in", 0, 100_000)
        assert result["passed"] is False
        assert result["out_of_range_rows"] >= 1


class TestAllowedValuesCheck:

    def test_passes_with_valid_regions(self, clean_hosp_df):
        result = check_allowed_values(
            clean_hosp_df, "region", {"Flanders", "Wallonia", "Brussels"}
        )
        assert result["passed"] is True

    def test_fails_with_unknown_region(self, spark, hosp_schema):
        data = [("2024-01-15", "Unknown", "UnknownRegion", 100, 10, 5, 4)]
        df = spark.createDataFrame(data, hosp_schema)

        result = check_allowed_values(
            df, "region", {"Flanders", "Wallonia", "Brussels"}
        )
        assert result["passed"] is False
        assert result["invalid_rows"] == 1
