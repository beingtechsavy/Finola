# Fintech Transaction Monitor

A Python + PostgreSQL project that generates synthetic fintech transaction data with realistic volume patterns and detects anomalies in hourly transaction counts.

## Project Structure

```
fintech-transaction-monitor/
├── data/                        # Raw CSV data files (excluded from git)
├── sql/
│   ├── create_tables.sql        # Transactions table schema
│   ├── create_alerts_table.sql  # Anomaly alerts table schema
│   └── detection.sql            # Anomaly detection SQL query
├── src/
│   ├── data_generation/
│   │   └── generate_data.py     # Generates synthetic transaction data
│   └── monitoring/
│       └── anomaly_detector.py  # Runs anomaly detection and prints alerts
├── .env.example                 # Template for environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

### 1. Prerequisites
- Python 3.8+
- PostgreSQL running locally

### 2. Clone and install dependencies
```bash
git clone <your-repo-url>
cd fintech-transaction-monitor
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in your PostgreSQL credentials:
```
DB_HOST=localhost
DB_NAME=fintech_monitor
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_PORT=5432
```

### 4. Set up the database
Connect to PostgreSQL and run the schema scripts in order:
```bash
psql -U postgres -d fintech_monitor -f sql/create_tables.sql
psql -U postgres -d fintech_monitor -f sql/create_alerts_table.sql
```

### 5. Generate synthetic data
```bash
python src/data_generation/generate_data.py
```
This inserts ~30 days of hourly transaction data with embedded anomalies.

### 6. Run anomaly detection
```bash
python src/monitoring/anomaly_detector.py
```
This executes `sql/detection.sql` against the database and prints any detected anomalies.

## How it Works

- **Data Generation**: Simulates realistic transaction volumes by time of day (busy business hours, quiet nights) and day of week (lower on weekends). Specific hours have injected anomalies at different multipliers.
- **Anomaly Detection**: Uses a CTE-based SQL query to compare the current hour's transaction count against a historical baseline and flags deviations beyond ±30% or +100%.
- **Alerts**: Detected anomalies are inserted into the `anomaly_alerts` table with a severity rating (`Low`, `Medium`, `High`).

## Anomaly Severity Thresholds

| Condition | Severity |
|-----------|----------|
| deviation < -50% | High |
| deviation < -30% | Medium |
| deviation > 200% | High |
| deviation > 100% | Medium |
