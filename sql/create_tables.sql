create table transactions(
    T_id varchar(50),
    date varchar(30),
    amount numeric(10,2),
    type varchar(10)
);

CREATE INDEX idx_transactions_hour ON transactions(date);
