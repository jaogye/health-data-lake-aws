# Data Dictionary — Health Data Lake

## Gold Zone Tables

### `be_hospitalizations_summary`
Aggregated daily COVID-19 hospitalization statistics for Belgium by region.

| Column | Type | Description |
|--------|------|-------------|
| `date` | DATE | Reference date |
| `region` | STRING | Belgian region (Flanders, Wallonia, Brussels) |
| `total_hospitalized` | INTEGER | Total patients hospitalized |
| `total_icu` | INTEGER | Total patients in ICU |
| `new_admissions` | INTEGER | New hospital admissions that day |
| `new_discharges` | INTEGER | Discharges that day |
| `7day_avg_admissions` | DOUBLE | 7-day rolling average of new admissions |
| `icu_rate` | DOUBLE | ICU patients as fraction of total hospitalized |
| `_ingestion_date` | DATE | Pipeline ingestion date |
| `_gold_processed_at` | STRING | Timestamp of Gold ETL processing |

**Source**: Sciensano `COVID19BE_HOSP.json` → Bronze → Silver → Gold  
**Partitioned by**: `region`  
**Update frequency**: Daily

---

### `be_vaccination_coverage`
Cumulative COVID-19 vaccination doses administered in Belgium.

| Column | Type | Description |
|--------|------|-------------|
| `date` | DATE | Administration date |
| `region` | STRING | Belgian region |
| `agegroup` | STRING | Age group (e.g., 18-34, 35-44) |
| `dose` | STRING | Dose type (A=first, B=second, C=booster, E=additional) |
| `doses_administered` | INTEGER | Doses given that day |
| `cumulative_doses` | LONG | Running total of doses |
| `_gold_processed_at` | STRING | Timestamp of Gold ETL processing |

**Source**: Sciensano `COVID19BE_VACC.json`  
**Partitioned by**: `region`

---

### `who_global_trends`
Global COVID-19 case and death trends from WHO, Belgium in EU context.

| Column | Type | Description |
|--------|------|-------------|
| `date_reported` | DATE | Report date |
| `country_code` | STRING | ISO 2-letter country code |
| `country` | STRING | Country name |
| `region` | STRING | WHO region (EURO, AMRO, etc.) |
| `new_cases` | INTEGER | New confirmed cases |
| `new_deaths` | INTEGER | New confirmed deaths |
| `cumulative_cases` | INTEGER | Total cases since start |
| `cumulative_deaths` | INTEGER | Total deaths since start |
| `case_fatality_rate` | DOUBLE | Deaths / Cases × 100 (%) |
| `_gold_processed_at` | STRING | Timestamp of Gold ETL processing |

**Source**: WHO `WHO-COVID-19-global-data.csv`  
**Partitioned by**: `region`

---

## Data Lineage

```
Sciensano API ──► Bronze (JSON, raw) ──► Silver (Parquet, typed) ──► Gold (Parquet, aggregated)
WHO API       ──► Bronze (CSV, raw)  ──► Silver (Parquet, typed) ──► Gold (Parquet, aggregated)
                                                                         │
                                                                    Athena / QuickSight
```

## GDPR Notes

All datasets used are **publicly available** and fully anonymized at source. No personally identifiable information (PII) is stored at any layer of the data lake. Data is retained per the lifecycle policies defined in Terraform (Bronze: 90 days, Silver/Gold: 365 days).
