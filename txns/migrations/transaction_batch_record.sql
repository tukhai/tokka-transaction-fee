CREATE TABLE transaction_batch_record (
    hash VARCHAR(255),
    block_number INTEGER,
    fee FLOAT,
    PRIMARY KEY (hash, block_number)
);

-- Step 2: Convert the table into a hypertable with 'block_number' as the partitioning column
SELECT create_hypertable('transaction_batch_record', 'block_number');
