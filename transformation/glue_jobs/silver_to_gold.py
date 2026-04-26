"""
AWS Glue ETL Job: Silver → Gold
Reads cleaned Parquet from Silver zone and produces:
  - Aggregated summaries by region, age group, date
  - Analytics-ready Gold tables for Athena / QuickSight
Writes partitioned Parquet to Gold zone.
"""

import sys
from datetime import datetime

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "SILVER_BUCKET", "GOLD_BUCKET", "RUN_DATE"],
)

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

SILVER_BUCKET = args["SILVER_BUCKET"]
GOLD_BUCKET = args["GOLD_BUCKET"]
RUN_DATE = args["RUN_DATE"]
year, month, day = RUN_DATE.split("-")

print(f"[silver_to_gold] Building Gold tables for date={RUN_DATE}")


# ── Read helpers ──────────────────────────────────────────────────────────────

def read_silver(source: str) -> DataFrame:
    path = f"s3://{SILVER_BUCKET}/silver/{source}/"
    return spark.read.parquet(path)


def write_gold(df: DataFrame, table: str) -> None:
    output_path = f"s3://{GOLD_BUCKET}/gold/{table}/"
    (
        df.write
        .mode("overwrite")
        .option("compression", "snappy")
        .partitionBy("region")
        .parquet(output_path)
    )
    print(f"[silver_to_gold] Written {df.count()} rows → gold/{table}/")


# ── Gold table: Belgium hospitalizations summary ──────────────────────────────

def build_be_hospitalizations_summary():
    df = read_silver("sciensano/covid_hospitalizations")

    window_region = Window.partitionBy("region").orderBy("date")

    summary = (
        df
        .withColumn("date", F.to_date("date", "yyyy-MM-dd"))
        .groupBy("date", "region")
        .agg(
            F.sum("total_in").alias("total_hospitalized"),
            F.sum("total_in_icu").alias("total_icu"),
            F.sum("new_in").alias("new_admissions"),
            F.sum("new_out").alias("new_discharges"),
        )
        .withColumn(
            "7day_avg_admissions",
            F.avg("new_admissions").over(window_region.rowsBetween(-6, 0)),
        )
        .withColumn("icu_rate", F.col("total_icu") / F.col("total_hospitalized"))
        .withColumn("_gold_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    write_gold(summary, "be_hospitalizations_summary")


# ── Gold table: Belgium vaccination coverage ──────────────────────────────────

def build_be_vaccination_coverage():
    df = read_silver("sciensano/covid_vaccinations")

    coverage = (
        df
        .withColumn("date", F.to_date("date", "yyyy-MM-dd"))
        .groupBy("date", "region", "agegroup", "dose")
        .agg(F.sum("count").alias("doses_administered"))
        .withColumn(
            "cumulative_doses",
            F.sum("doses_administered").over(
                Window.partitionBy("region", "agegroup", "dose").orderBy("date").rowsBetween(Window.unboundedPreceding, 0)
            ),
        )
        .withColumn("_gold_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    write_gold(coverage, "be_vaccination_coverage")


# ── Gold table: WHO global trends (Belgium in context) ────────────────────────

def build_who_global_trends():
    df = read_silver("who/global_covid")

    trends = (
        df
        .withColumn("date_reported", F.to_date("date_reported", "yyyy-MM-dd"))
        .groupBy("date_reported", "who_region", "country_code", "country")
        .agg(
            F.sum("new_cases").alias("new_cases"),
            F.sum("new_deaths").alias("new_deaths"),
            F.max("cumulative_cases").alias("cumulative_cases"),
            F.max("cumulative_deaths").alias("cumulative_deaths"),
        )
        .withColumn(
            "case_fatality_rate",
            F.when(F.col("cumulative_cases") > 0,
                   F.col("cumulative_deaths") / F.col("cumulative_cases") * 100
            ).otherwise(None),
        )
        .withColumnRenamed("who_region", "region")
        .withColumn("_gold_processed_at", F.lit(datetime.utcnow().isoformat()))
    )

    write_gold(trends, "who_global_trends")


# ── Run all Gold builds ───────────────────────────────────────────────────────

build_be_hospitalizations_summary()
build_be_vaccination_coverage()
build_who_global_trends()

print("[silver_to_gold] All Gold tables built successfully.")
job.commit()
