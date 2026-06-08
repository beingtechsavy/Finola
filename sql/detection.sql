with last_hour as (
    select 
    date_trunc('hour',max(date::timestamp)) - INTERVAL '1 hour' as target_hour
    from transactions
    where date::timestamp < date_trunc('hour',NOW())
),

hourly_actual as (
    select date_trunc('hour',date::timestamp) as hour_start,
    count(*) as txn_count,
    sum(amount) as total_amount
    from transactions
    where date::timestamp < date_trunc('hour',NOW())
    group by 1
),

historical_baseline as (
    select 
    extract(hour from date::timestamp) as hour_of_day,
    avg(count(*)) over (partition by extract(hour from date::timestamp)) as expected_count
    from transactions 
    where date::timestamp >= Now() - interval '1 days'
    and date::timestamp < date_trunc('hour',NOW())  
    group by extract(hour from date::timestamp)

),
comparison as (

    select
    h.hour_start,
    h.txn_count as actual_count,
    b.expected_count,
    ((h.txn_count-b.expected_count) / nullif(b.expected_count,0)) * 100 as deviation_pct
   from hourly_actual h cross join historical_baseline b
    where extract(hour from h.hour_start)=b.hour_of_day
)


insert into anomaly_alerts(hour_start,actual_count,expected_count,deviation_percent,severity)
select hour_start, actual_count, expected_count, deviation_pct,
case
    when deviation_pct < -50 then 'High'
    when deviation_pct < -30 THEN 'Medium'
    when deviation_pct > 200 THEN 'High'
    when deviation_pct > 100 THEN 'Medium'
        else 'Low'
    end
    from comparison
    where deviation_pct<-30 or deviation_pct>100;