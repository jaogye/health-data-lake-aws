# 🏥 Public Health Data Lake Pipeline on AWS

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![AWS](https://img.shields.io/badge/AWS-Cloud-orange?logo=amazon-aws)](https://aws.amazon.com)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-purple?logo=terraform)](https://terraform.io)
[![PySpark](https://img.shields.io/badge/PySpark-3.3-red?logo=apache-spark)](https://spark.apache.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-black?logo=github-actions)](/.github/workflows)

A production-grade, serverless **Data Lake Pipeline** built on AWS that ingests, transforms, and serves **Belgian and European public health data** from [Sciensano](https://epistat.sciensano.be) and the [WHO](https://www.who.int/data). Implements the **Medallion Architecture** (Bronze / Silver / Gold) with full Infrastructure as Code, data quality checks, and GDPR-compliant data handling.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                  │
│   Sciensano API  │  WHO Global Health API  │  Eurostat CSV           │
└────────┬────────────────────┬──────────────────────┬────────────────┘
         │                    │                      │
         ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                                  │
│         AWS Lambda (Python / boto3)  +  EventBridge Scheduler        │
│                   (daily trigger at 02:00 UTC)                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  S3 DATA LAKE  —  BRONZE ZONE                        │
│          s3://health-datalake-{env}/bronze/                          │
│          Partitioned by: source / year / month / day                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│               TRANSFORMATION LAYER  (AWS Glue ETL)                   │
│   PySpark Jobs:  schema validation, deduplication, normalization     │
│   Data Quality:  Great Expectations checks                           │
└──────────┬────────────────────────────────┬────────────────────────┘
           │                                │
           ▼                                ▼
┌──────────────────────┐       ┌────────────────────────────────────┐
│  S3 — SILVER ZONE    │       │        S3 — GOLD ZONE              │
│  Cleaned & typed     │──────▶│  Aggregated, analytics-ready       │
│  Parquet + Snappy    │       │  Parquet, partitioned by region    │
└──────────────────────┘       └──────────────────┬─────────────────┘
                                                  │
                           ┌──────────────────────┤
                           ▼                      ▼
              ┌─────────────────────┐  ┌──────────────────────┐
              │  AWS Glue Catalog   │  │   Amazon Athena       │
              │  (schema registry)  │  │   (serverless SQL)    │
              └─────────────────────┘  └──────────┬───────────┘
                                                  │
                                                  ▼
                                       ┌──────────────────────┐
                                       │  Amazon QuickSight   │
                                       │  (BI Dashboard)      │
                                       └──────────────────────┘
```

**Monitoring & Observability**: AWS CloudWatch (logs, metrics, alarms) + SNS alerts

---

## 🛠️ Technologies

| Layer | Technology |
|-------|-----------|
| **Ingestion** | AWS Lambda, Amazon EventBridge, Python boto3 |
| **Storage** | Amazon S3 (Bronze / Silver / Gold medallion architecture) |
| **Transformation** | AWS Glue ETL (PySpark 3.3), Glue Crawler |
| **Cataloging** | AWS Glue Data Catalog |
| **Querying** | Amazon Athena (serverless SQL) |
| **Visualization** | Amazon QuickSight |
| **Data Quality** | Great Expectations, custom PySpark checks |
| **IaC** | Terraform 1.5+ (AWS & Azure) |
| **CI/CD** | GitHub Actions |

---

## ☁️ Multi-Cloud Support

This project supports both **AWS** and **Azure** deployments using Terraform.

### AWS Infrastructure (`infrastructure/`)
- S3 buckets with KMS encryption
- Lambda + EventBridge for ingestion
- Glue ETL for transformations
- Athena + QuickSight for analytics

### Azure Infrastructure (`infrastructure/azure/`)
- ADLS Gen2 with hierarchical namespace
- Azure Functions + Timer Trigger for ingestion
- Azure Data Factory + Databricks Spark
- Synapse Analytics + Power BI

### Deploy Azure Infrastructure

```bash
cd infrastructure/azure
terraform init
terraform plan -var="env=dev"
terraform apply -var="env=dev"
```

---
| **Monitoring** | AWS CloudWatch, SNS |
| **Security** | IAM least-privilege roles, S3 bucket policies, KMS encryption |

---

## 📁 Repository Structure

```
health-data-lake-aws/
├── README.md
├── architecture/
│   └── diagram.png
├── infrastructure/              # Terraform IaC (AWS)
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── s3.tf
│   ├── glue.tf
│   ├── lambda.tf
│   ├── iam.tf
│   └── eventbridge.tf
├── infrastructure/azure/        # Terraform IaC (Azure)
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── data_lake.tf
│   ├── function_app.tf
│   └── data_factory.tf
├── ingestion/
│   ├── lambda_ingestor/         # AWS Lambda code
│   │   ├── handler.py
│   │   ├── sciensano_client.py
│   │   ├── who_client.py
│   │   └── requirements.txt
│   └── azure_function/          # Azure Functions code
│       ├── __init__.py
│       ├── function.json
│       ├── host.json
│       └── requirements.txt
├── transformation/
│   ├── glue_jobs/
│   │   ├── bronze_to_silver.py  # PySpark ETL: clean & type
│   │   └── silver_to_gold.py    # PySpark ETL: aggregate & enrich
│   └── data_quality/
│       └── checks.py            # Great Expectations suites
├── queries/
│   └── athena_examples.sql      # Ready-to-run Athena queries
├── tests/
│   ├── test_ingestion.py
│   ├── test_transformations.py
│   └── conftest.py
├── docs/
│   └── data_dictionary.md
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
└── requirements-dev.txt
```

---

## 🚀 Getting Started

### Prerequisites

- AWS Account with appropriate permissions
- [Terraform](https://terraform.io) >= 1.5
- Python 3.11+
- AWS CLI configured (`aws configure`)

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/health-data-lake-aws.git
cd health-data-lake-aws
```

### 2. Install dev dependencies

```bash
pip install -r requirements-dev.txt
```

### 3. Deploy infrastructure

```bash
cd infrastructure
terraform init
terraform plan -var="env=dev"
terraform apply -var="env=dev"
```

### 4. Deploy Lambda

```bash
cd ingestion/lambda_ingestor
pip install -r requirements.txt -t ./package
zip -r ../../infrastructure/lambda_package.zip .
```

### 5. Run tests

```bash
pytest tests/ -v
```

---

## 📊 Data Sources

| Source | Dataset | Update Frequency | Format |
|--------|---------|-----------------|--------|
| [Sciensano](https://epistat.sciensano.be/covid/) | COVID-19 Belgium | Daily | JSON/CSV |
| [Sciensano](https://epistat.sciensano.be) | Infectious diseases BE | Weekly | CSV |
| [WHO](https://covid19.who.int/data) | Global COVID-19 | Daily | CSV |
| [Eurostat](https://ec.europa.eu/eurostat) | Health statistics EU | Monthly | CSV |

---

## 🔒 GDPR & Security

- All data is **publicly available** and anonymized at source
- S3 buckets encrypted with **AWS KMS**
- IAM roles follow **least privilege principle**
- No PII stored in any layer
- Data retention policies configured per bucket (Bronze: 90 days, Silver/Gold: 1 year)

---

## 💰 Estimated AWS Cost (Dev Environment)

| Service | Usage | Estimated Cost |
|---------|-------|---------------|
| S3 | ~5 GB storage | ~$0.12/month |
| Lambda | ~30 invocations/month | Free tier |
| Glue ETL | ~2 DPU-hours/day | ~$2/month |
| Athena | ~1 GB scanned/month | ~$0.005 |
| CloudWatch | Logs & metrics | ~$0.50/month |
| **Total** | | **~$3/month** |

---

## 🗺️ Roadmap

- [x] ~~Add Azure Data Factory mirror (ADF + ADLS Gen2) for multi-cloud~~ ✅ Done
- [ ] Streaming ingestion with Amazon Kinesis
- [ ] dbt models for Gold layer transformations
- [ ] Apache Airflow (MWAA) for orchestration
- [ ] ML anomaly detection on health trends (SageMaker)

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
