# pyrefly: ignore [missing-import]
import psycopg2
import uuid
import random
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

con = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "fintech_monitor"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "port":     os.getenv("DB_PORT", "5432"),
}


def normal_volume(day_of_week, hour):
    if hour >= 0 and hour < 6:
        base = 10
    if hour >= 6 and hour < 9:
        base = 40
    if hour >= 9 and hour < 17:
        base = 120
    if hour >= 17 and hour < 22:
        base = 100
    if hour >= 22 and hour < 24:
        base = 40

    if day_of_week in [5, 6]:
        base = base * 0.7

    variation = random.uniform(0.8, 1.2)
    return max(1, int(base * variation))


def generate_amount():
    chance = random.random()
    if chance < 0.7:
        return round(random.uniform(5, 100), 2)
    elif chance < 0.9:
        return round(random.uniform(100, 500), 2)
    else:
        return round(random.uniform(500, 1000), 2)


def main():
    conn = psycopg2.connect(**con)
    cur = conn.cursor()
    start_date = datetime.datetime(2026, 6, 1, 0, 0, 0)
    end_date = datetime.datetime(2026, 6, 30, 0, 0, 0)
    anomalies = {
        "2026-06-10 14:30:00": 3.0,
        "2026-06-12 14:30:00": 15.0,
        "2026-06-15 14:30:00": 0.2,
        "2026-06-20 14:30:00": 0.5,
        "2026-06-25 14:30:00": 6.5,
    }

    current = start_date
    total_inserted = 0
    while current <= end_date:
        hour = current.strftime("%Y-%m-%d %H:00:00")
        day_of_week = current.weekday()
        normal_vol = normal_volume(current.hour, day_of_week)
        if hour in anomalies:
            multiplier = anomalies[hour]
            txn_count = max(1, int(normal_vol * multiplier))
            print(f"Anomaly at {hour}: {normal_vol} -> {txn_count}")
        else:
            txn_count = normal_vol

        for _ in range(txn_count):
            seconds_offset = random.randint(0, 3599)
            txn_date = current + datetime.timedelta(seconds=seconds_offset)
            txn_id = f"TX_({uuid.uuid4().hex[:8]})"
            amount = generate_amount()
            txn_type = random.choices(['Debit', 'Credit'], weights=[0.8, 0.2])[0]
            cur.execute(
                "INSERT INTO transactions(T_id,date,amount,type) VALUES(%s,%s,%s,%s)",
                (txn_id, txn_date, amount, txn_type)
            )
            total_inserted += 1

        conn.commit()
        print(f"Inserted {txn_count} transactions for {hour}")
        current += datetime.timedelta(hours=1)

    cur.close()
    conn.close()
    print(f"Done! Generated {total_inserted} transactions.")


if __name__ == "__main__":
    main()
