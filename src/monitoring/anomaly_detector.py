# pyrefly: ignore [missing-import]
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    database=os.getenv("DB_NAME", "fintech_monitor"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT", "5432"),
)

cur = conn.cursor()

# Execute the anomaly detection SQL script
script_dir = os.path.dirname(os.path.abspath(__file__))
sql_path = os.path.join(script_dir, "..", "..", "sql", "detection.sql")
with open(sql_path, "r") as f:
    sql_script = f.read()

cur.execute(sql_script)
conn.commit()

# Fetch and display any detected anomalies
cur.execute("SELECT * FROM anomaly_alerts ORDER BY alert_time DESC")
rows = cur.fetchall()
if rows:
    print("New Anomalies detected:")
    for row in rows:
        print(row)
else:
    print("No Anomalies found in last hour")

cur.close()
conn.close()
