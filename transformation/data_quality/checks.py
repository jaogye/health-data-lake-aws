"""
Data Quality checks for the Health Data Lake pipeline.
Uses Great Expectations for validation suites on Silver-zone DataFrames.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    source: str
    passed: bool
    checks: list[dict] = field(default_factory=list)
    failed_checks: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        total = len(self.checks)
        passed = total - len(self.failed_checks)
        return f"[{self.source}] Quality: {passed}/{total} checks passed"


def check_not_null(df: DataFrame, column: str, threshold: float = 0.95) -> dict:
    """Assert that at least `threshold` fraction of rows are non-null for a column."""
    total = df.count()
    non_null = df.filter(F.col(column).isNotNull()).count()
    ratio = non_null / total if total > 0 else 0.0
    passed = ratio >= threshold
    return {
        "check": f"not_null_{column}",
        "column": column,
        "threshold": threshold,
        "actual": round(ratio, 4),
        "passed": passed,
    }


def check_no_duplicates(df: DataFrame, key_columns: list[str]) -> dict:
    """Assert there are no duplicate rows based on key columns."""
    total = df.count()
    distinct = df.dropDuplicates(key_columns).count()
    passed = total == distinct
    return {
        "check": "no_duplicates",
        "key_columns": key_columns,
        "total_rows": total,
        "distinct_rows": distinct,
        "passed": passed,
    }


def check_value_range(df: DataFrame, column: str, min_val: Any, max_val: Any) -> dict:
    """Assert all non-null values in a column fall within [min_val, max_val]."""
    out_of_range = df.filter(
        F.col(column).isNotNull()
        & ((F.col(column) < min_val) | (F.col(column) > max_val))
    ).count()
    passed = out_of_range == 0
    return {
        "check": f"value_range_{column}",
        "column": column,
        "min": min_val,
        "max": max_val,
        "out_of_range_rows": out_of_range,
        "passed": passed,
    }


def check_allowed_values(df: DataFrame, column: str, allowed: set) -> dict:
    """Assert all non-null values in a column are in the allowed set."""
    invalid = df.filter(
        F.col(column).isNotNull() & ~F.col(column).isin(list(allowed))
    ).count()
    passed = invalid == 0
    return {
        "check": f"allowed_values_{column}",
        "column": column,
        "allowed_count": len(allowed),
        "invalid_rows": invalid,
        "passed": passed,
    }
