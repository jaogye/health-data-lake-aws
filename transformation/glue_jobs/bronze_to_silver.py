"""
AWS Glue ETL Job: Bronze → Silver
Reads raw JSON/CSV from Bronze S3 zone, applies:
  - Schema enforcement & type casting
  - Deduplication
  - Null handling & data quality filters
  - Normalization (column names, date formats)
Writes cleaned Parquet (Snappy compressed) to Silver zone.
"""

import sys
from datetime import datetime

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, IntegerType, StringType, StructField, StructType

# ── Job parameters ────────────────────────────────────────────────────────────
args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "BRONZE_BUCKET", "SILVER_BUCKET", "SOURCE", "RUN_DATE"],
)

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

BRONZE_BUCKET = args["BRONZE_BUCKET"]
SILVER_BUCKET = args["SILVER_BUCKET"]
SOURCE = args["SOURCE"]          # e.g. "sciensano/covid_hospitalizations"
RUN_DATE = args["RUN_DATE"]      # e.g. "2024-01-15"

year, month, day = RUN_DATE.split("-")

print(f"[bronze_to_silver] Processing source={SOURCE} date={RUN_DATE}")


# ── Schema definitions ────────────────────────────────────────────────────────

SCHEMAS = {
    "sciensano/covid_hospitalizations": StructType([
        StructField("DATE", StringType(), True),
        StructField("PROVINCE", StringType(), True),
        StructField("REGION", StringType(), True),
        StructField("NR_REPORTING", IntegerType(), True),
        StructField("TOTAL_IN", IntegerType(), True),
        StructField("TOTAL_IN_ICU", IntegerType(), True),
        StructField("TOTAL_IN_RESP", IntegerType(), True),
        StructField("TOTAL_IN_ECMO", IntegerType(), True),
        StructField("NEW_IN", IntegerType(), True),
        StructField("NEW_OUT", IntegerType(), True),
    ]),
    "sciensano/covid_vaccinations": StructType([
        StructField("DATE", StringType(), True),
        StructField("REGION", StringType(), True),
        StructField("AGEGROUP", StringType(), True),
        StructField("SEX", StringType(), True),
        StructField("BRAND", StringType(), True),
        StructField("DOSE", StringType(), True),
        StructField("COUNT", IntegerType(), True),
    ]),
    "who/global_covid": StructType([
        StructField("Date_reported", StringType(), True),
        StructField("Country_code", StringType(), True),
        StructField("Country", StringType(), True),
        StructField("WHO_region", StringType(), True),
        StructField("New_cases", IntegerType(), True),
        StructField("Cumulative_cases", IntegerType(), True),
        StructField("New_deaths", IntegerType(), True),
        StructField("Cumulative_deaths", IntegerType(), True),
    ]),
}


# ── Helper functions ──────────────────────────────────────────────────────────

def read_bronze(source: str) -> DataFrame:
    """Read raw data from Bronze zone based on source type."""
    path = f"s3://{BRONZE_BUCKET}/bronze/{source}/year={year}/month={month}/day={day}/"
    if source.endswith("global_covid"):
        return spark.read.option("header", "true").option("inferSchema", "false").csv(path)
    return spark.read.option("multiline", "true").json(path)


def normalize_columns(df: DataFrame) -> DataFrame:
    """Lowercase and snake_case all column names."""
    for col in df.columns:
        df = df.withColumnRenamed(col, col.lower().replace(" ", "_").replace("-", "_"))
    return df


def cast_schema(df: DataFrame, schema: StructType) -> DataFrame:
    """Cast columns to the defined schema types."""
    for field in schema.fields:
        col_name = field.name.lower().replace(" ", "_")
        if col_name in [c.lower() for c in df.columns]:
            df = df.withColumn(col_name, F.col(col_name).cast(field.dataType))
    return df


def add_metadata(df: DataFrame) -> DataFrame:
    """Add pipeline metadata columns."""
    return (
        df
        .withColumn("_ingestion_date", F.lit(RUN_DATE).cast(DateType()))
        .withColumn("_source", F.lit(SOURCE))
        .withColumn("_processed_at", F.lit(datetime.utcnow().isoformat()))
    )


def apply_quality_filters(df: DataFrame, source: str) -> DataFrame:
    """Drop rows that fail basic quality checks."""
    date_col = "date_reported" if "who" in source else "date"
    if date_col in [c.lower() for c in df.columns]:
        df = df.filter(F.col(date_col).isNotNull())
    return df.dropDuplicates()


def write_silver(df: DataFrame, source: str) -> None:
    """Write cleaned DataFrame to Silver zone as Parquet."""
    output_path = (
        f"s3://{SILVER_BUCKET}/silver/{source}/"
        f"year={year}/month={month}/day={day}/"
    )
    (
        df.write
        .mode("overwrite")
        .option("compression", "snappy")
        .parquet(output_path)
    )
    print(f"[bronze_to_silver] Written {df.count()} rows to {output_path}")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run():
    schema = SCHEMAS.get(SOURCE)
    if not schema:
        raise ValueError(f"No schema defined for source: {SOURCE}. Add it to SCHEMAS dict.")

    df = read_bronze(SOURCE)
    print(f"[bronze_to_silver] Read {df.count()} raw rows from Bronze")

    df = normalize_columns(df)
    df = cast_schema(df, schema)
    df = apply_quality_filters(df, SOURCE)
    df = add_metadata(df)

    write_silver(df, SOURCE)
    print(f"[bronze_to_silver] Job complete for source={SOURCE}")


run()
job.commit()
