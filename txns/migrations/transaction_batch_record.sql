CREATE TABLE transaction_batch_record (
    id serial,
    hash VARCHAR(255),
    block_number BIGINT,
    timestamp TIMESTAMP,
    fee FLOAT,
    PRIMARY KEY (hash, timestamp)
);

-- Step 2: Convert the table into a hypertable with 'block_number' as the partitioning column
SELECT create_hypertable('transaction_batch_record', 'timestamp');
