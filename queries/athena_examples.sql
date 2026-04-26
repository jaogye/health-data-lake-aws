-- ============================================================
-- Health Data Lake — Amazon Athena Example Queries
-- Database: health_datalake_{env}
-- ============================================================

-- ── 1. Belgium ICU occupancy trend (last 30 days) ─────────────────────────────
SELECT
    date,
    region,
    total_hospitalized,
    total_icu,
    ROUND(icu_rate * 100, 2)        AS icu_rate_pct,
    ROUND(7day_avg_admissions, 1)   AS avg_daily_admissions_7d
FROM be_hospitalizations_summary
WHERE date >= DATE_ADD('day', -30, CURRENT_DATE)
ORDER BY date DESC, region;


-- ── 2. Vaccination coverage by age group and dose in Flanders ─────────────────
SELECT
    agegroup,
    dose,
    SUM(doses_administered)   AS total_doses,
    MAX(cumulative_doses)     AS cumulative_total
FROM be_vaccination_coverage
WHERE region = 'Flanders'
GROUP BY agegroup, dose
ORDER BY agegroup, dose;


-- ── 3. Belgium vs EU neighbors — new cases comparison ────────────────────────
SELECT
    date_reported,
    country,
    new_cases,
    new_deaths,
    ROUND(case_fatality_rate, 3) AS cfr_pct
FROM who_global_trends
WHERE country_code IN ('BE', 'NL', 'DE', 'FR', 'LU')
  AND date_reported >= DATE_ADD('month', -3, CURRENT_DATE)
ORDER BY date_reported DESC, country;


-- ── 4. Weekly aggregate: BE hospitalizations ─────────────────────────────────
SELECT
    DATE_TRUNC('week', date)        AS week_start,
    region,
    AVG(total_hospitalized)         AS avg_hospitalized,
    AVG(total_icu)                  AS avg_icu,
    SUM(new_admissions)             AS total_new_admissions
FROM be_hospitalizations_summary
GROUP BY DATE_TRUNC('week', date), region
ORDER BY week_start DESC, region;


-- ── 5. Data freshness check (pipeline monitoring) ────────────────────────────
SELECT
    '_ingestion_date'               AS metric,
    MAX(_ingestion_date)            AS latest_ingestion,
    COUNT(*)                        AS total_records,
    COUNT(DISTINCT region)          AS regions_count
FROM be_hospitalizations_summary
GROUP BY 1;
