create table hourly_transaction_summary(
    hour_start timestamp primary key,
    txn_count integer not null,
    total_amount decimal(12,2) not null,
    avg_amount decimal(12,2) not null,
    created_at timestamp default current_timestamp
);

create table anomaly_alerts(
    alert_id uuid primary key default gen_random_uuid(),
    hour_start timestamp not null,
    actual_count decimal(12,2) not null,
    expected_count decimal(12,2) not null,
    deviation_percent decimal(8,2) not null,
    severity varchar(20) check (severity in ('Low','Medium','High')),
    alert_time timestamp default current_timestamp
);
