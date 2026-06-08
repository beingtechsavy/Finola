# 🏦 Finola — Fintech Transaction Anomaly Monitor

> **"Banks and fintechs lose millions to undetected payment outages and fraud spikes at 2 AM. Finola watches so you don't have to."**

Finola is a fully automated, SQL-powered transaction health monitor built on PostgreSQL and Python. It runs every hour, compares live transaction volumes against a historical baseline, and flags anomalies — no machine learning, no black boxes, no guesswork.

---

## The Problem It Solves

In payment infrastructure, silent failures are the most dangerous kind. A card processor going down at 2 AM might cut transaction volume by 80% — but without a monitoring system, nobody finds out until the 9 AM business review. Equally dangerous is a fraud spike that drives volume 15× above normal, silently draining accounts before any alert fires.

Finola was built to solve this. It answers one question every hour:

> *Is the number of transactions in the last hour statistically normal for this time of day?*

If not, it writes a severity-tagged alert to a PostgreSQL table — automatically, continuously, no human required.

---

## How It Works

### Architecture

```
PostgreSQL (WSL Ubuntu)
    └── transactions          ← raw transaction records
    └── hourly_txn_summary    ← pre-aggregated hourly metrics
    └── anomaly_alerts        ← output: flagged anomalies with severity

Python
    └── src/data_generation/generate_data.py   ← synthetic data generator
    └── src/monitoring/anomaly_detector.py      ← runs detection every hour

SQL
    └── sql/detection.sql     ← the core anomaly detection query (CTEs + window functions)

Cron (WSL)
    └── runs anomaly_detector.py every hour on the :00
```

### The Detection Logic

The heart of Finola is a single, composable SQL query using four CTEs:

```sql
WITH last_hour AS (
    -- Pin the target: the most recently completed hour
    SELECT date_trunc('hour', max(date::timestamp)) - INTERVAL '1 hour'
    FROM transactions
    WHERE date::timestamp < date_trunc('hour', NOW())
),

hourly_actual AS (
    -- Count real transactions per hour
    SELECT date_trunc('hour', date::timestamp) AS hour_start,
           count(*) AS txn_count
    FROM transactions
    GROUP BY 1
),

historical_baseline AS (
    -- What does a *normal* 3 PM Tuesday look like?
    -- Average transaction count for the same hour-of-day over the past 7 days
    SELECT extract(hour FROM date::timestamp) AS hour_of_day,
           avg(count(*)) OVER (PARTITION BY extract(hour FROM date::timestamp)) AS expected_count
    FROM transactions
    WHERE date::timestamp >= NOW() - INTERVAL '7 days'
    GROUP BY extract(hour FROM date::timestamp)
),

comparison AS (
    -- Join actual vs baseline, compute deviation %
    SELECT h.hour_start,
           h.txn_count AS actual_count,
           b.expected_count,
           ((h.txn_count - b.expected_count) / NULLIF(b.expected_count, 0)) * 100 AS deviation_pct
    FROM hourly_actual h
    CROSS JOIN historical_baseline b
    WHERE extract(hour FROM h.hour_start) = b.hour_of_day
)

-- Write only the anomalies, with severity
INSERT INTO anomaly_alerts (hour_start, actual_count, expected_count, deviation_percent, severity)
SELECT ...,
    CASE
        WHEN deviation_pct < -50 THEN 'High'
        WHEN deviation_pct < -30 THEN 'Medium'
        WHEN deviation_pct > 200 THEN 'High'
        WHEN deviation_pct > 100 THEN 'Medium'
        ELSE 'Low'
    END
FROM comparison
WHERE deviation_pct < -30 OR deviation_pct > 100;
```

No ML. No external dependencies. Just window functions and a CASE statement — readable by any SQL analyst, auditable by any engineer.

---

## Severity Thresholds

| Condition | Severity | Real-World Meaning |
|-----------|----------|--------------------|
| Volume drops > 50% | 🔴 High | Likely payment processor outage |
| Volume drops 30–50% | 🟡 Medium | Degraded throughput, warrants investigation |
| Volume spikes > 200% | 🔴 High | Possible fraud wave or DDoS |
| Volume spikes 100–200% | 🟡 Medium | Unusual load, could be a campaign or attack |

---

## The Data Generator

Real-world monitoring systems need realistic data. Rather than using a public Kaggle dataset (wrong timestamp format, too few rows), Finola generates its own — with full control over normal patterns and injected anomalies.

**Normal volume model** (transactions per hour):

| Time Window | Weekday Volume | Weekend Volume |
|-------------|---------------|----------------|
| 00:00–06:00 | ~10 txns/hr | ~7 txns/hr |
| 06:00–09:00 | ~40 txns/hr | ~28 txns/hr |
| 09:00–17:00 | ~120 txns/hr | ~84 txns/hr |
| 17:00–22:00 | ~100 txns/hr | ~70 txns/hr |
| 22:00–24:00 | ~40 txns/hr | ~28 txns/hr |

Each hour is also randomised ±20% to simulate natural jitter (`random.uniform(0.8, 1.2)`).

**Injected anomalies** (the ground truth for validation):

| Timestamp | Multiplier | Type |
|-----------|-----------|------|
| 2026-06-10 14:30 | 3.0× | Moderate spike |
| 2026-06-12 14:30 | **15.0×** | Severe fraud-like surge |
| 2026-06-15 14:30 | 0.2× | Severe drop (simulated outage) |
| 2026-06-20 14:30 | 0.5× | Moderate drop |
| 2026-06-25 14:30 | 6.5× | Large spike |

The generator produces ~**9,200 synthetic transactions** across 30 days — enough history for the baseline to be meaningful.

---

## Validation Results

After running the full pipeline against the generated dataset:

- **47 anomaly alerts** were produced
- All 5 injected anomalies were correctly caught
- Additional statistical anomalies were flagged at hours where random variation crossed the threshold — exactly as expected
- A **"cold start" effect** was observed: when there isn't enough historical data for a given hour-of-day, the baseline is thin and false positive rates rise — a real-world operational insight that no tutorial teaches

---

## Project Structure

```
finola/
├── src/
│   ├── data_generation/
│   │   └── generate_data.py        # Synthetic transaction generator
│   └── monitoring/
│       └── anomaly_detector.py     # Hourly detection runner
├── sql/
│   ├── create_tables.sql           # transactions table + index
│   ├── create_alerts_table.sql     # hourly_summary + anomaly_alerts tables
│   └── detection.sql               # Core CTE-based detection query
├── data/                           # Raw CSV (gitignored)
├── .env.example                    # Credential template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup & Usage

### Prerequisites
- Python 3.8+
- PostgreSQL (running locally or via WSL Ubuntu)

### 1. Clone & install dependencies
```bash
git clone https://github.com/beingtechsavy/Finola.git
cd Finola
pip install -r requirements.txt
```

### 2. Configure credentials
```bash
cp .env.example .env
# Edit .env with your PostgreSQL host, user, password, port
```

### 3. Set up the database
```bash
psql -U postgres -d fintech_monitor -f sql/create_tables.sql
psql -U postgres -d fintech_monitor -f sql/create_alerts_table.sql
```

### 4. Generate synthetic data
```bash
python src/data_generation/generate_data.py
```

### 5. Run anomaly detection once
```bash
python src/monitoring/anomaly_detector.py
```

### 6. Automate with cron (runs every hour)
```bash
crontab -e
# Add this line:
0 * * * * /usr/bin/python3 /path/to/src/monitoring/anomaly_detector.py
```

---

## Key Design Decisions

**Why no machine learning?**
ML models require training data, retraining pipelines, and explainability overhead. A threshold-based SQL approach is auditable, fast to deploy, and behaves predictably — exactly what a production on-call system needs.

**Why synthetic data over Kaggle?**
Public fintech datasets have messy timestamps, inconsistent formats, and no guarantee that anomalies exist. Generating data gave full control over the normal distribution *and* the ground truth anomalies needed for validation.

**Why WSL over native Windows PostgreSQL?**
Native PostgreSQL installation on Windows is error-prone (PATH conflicts, service manager quirks). WSL Ubuntu provides a clean Linux environment that mirrors how PostgreSQL runs in production.

**Why a single SQL file instead of Python logic?**
Pushing the aggregation and comparison into SQL keeps the Python layer thin and testable. Any analyst can open `detection.sql` and understand the detection logic without reading Python.

---

## What's Next

This project is intentionally scoped as a foundation. Natural next steps:

- [ ] **Email/Slack alerts** — pipe `anomaly_alerts` rows into a notification service
- [ ] **Grafana dashboard** — visualise hourly volume and alert history in real time  
- [ ] **Airflow DAG** — replace cron with a proper orchestrator for retries and observability
- [ ] **Kafka integration** — move from batch hourly detection to streaming, sub-minute anomaly detection
- [ ] **Dynamic thresholds** — replace fixed 30%/100% thresholds with rolling standard deviation bands

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL 14 (WSL Ubuntu) |
| Language | Python 3.x |
| DB Driver | psycopg2 |
| Config | python-dotenv |
| Scheduling | cron (WSL) |
| Query Style | CTEs + window functions |
| Version Control | Git + GitHub |

---

## About

Built as a portfolio project demonstrating end-to-end data engineering fundamentals: data modelling, synthetic data generation, SQL analytics, pipeline automation, and production-readiness practices (`.env`, `.gitignore`, structured project layout).

> *No ML. No dashboards. Just SQL, Python, and a cron job — doing exactly what they're supposed to do.*
