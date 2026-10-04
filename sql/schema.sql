-- Component 2: FreshMart database schema (MySQL 8, runs on AWS RDS)
-- Star schema: 2 dimension tables (who/what) + 1 fact table (the sales events)
-- Plus 2 support tables: anomalies (output) and etl_audit (pipeline bookkeeping)

CREATE DATABASE IF NOT EXISTS freshmart;
USE freshmart;

-- ---------- Dimensions ----------
CREATE TABLE IF NOT EXISTS dim_store (
    store_id      VARCHAR(10)  PRIMARY KEY,
    city          VARCHAR(50)  NOT NULL,
    region        VARCHAR(20)  NOT NULL,
    store_manager VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id    VARCHAR(10)  PRIMARY KEY,
    product_name  VARCHAR(100) NOT NULL,
    category      VARCHAR(50)  NOT NULL,
    list_price    DECIMAL(10,2) NOT NULL
);

-- ---------- Fact ----------
CREATE TABLE IF NOT EXISTS fact_sales (
    transaction_id VARCHAR(20)  PRIMARY KEY,          -- PK = duplicates rejected by the DB
    store_id       VARCHAR(10)  NOT NULL,
    product_id     VARCHAR(10)  NOT NULL,
    sale_date      DATE         NOT NULL,
    quantity       INT          NOT NULL CHECK (quantity > 0),
    unit_price     DECIMAL(10,2) NOT NULL,
    amount         DECIMAL(12,2) NOT NULL,            -- quantity * unit_price, precomputed
    payment_mode   VARCHAR(10),
    source_file    VARCHAR(200) NOT NULL,             -- lineage: which raw file it came from
    FOREIGN KEY (store_id)   REFERENCES dim_store(store_id),
    FOREIGN KEY (product_id) REFERENCES dim_product(product_id),
    INDEX idx_date_store (sale_date, store_id)        -- dashboard filters by date, then store
);

-- ---------- Outputs / bookkeeping ----------
CREATE TABLE IF NOT EXISTS sales_anomaly (
    store_id         VARCHAR(10)  NOT NULL,
    sale_date        DATE         NOT NULL,
    revenue          DECIMAL(14,2) NOT NULL,
    expected_revenue DECIMAL(14,2) NOT NULL,          -- mean of previous 14 days
    z_score          DECIMAL(6,2)  NOT NULL,
    direction        VARCHAR(5)    NOT NULL,          -- 'HIGH' or 'LOW'
    PRIMARY KEY (store_id, sale_date),
    FOREIGN KEY (store_id) REFERENCES dim_store(store_id)
);

CREATE TABLE IF NOT EXISTS etl_audit (
    file_name     VARCHAR(200) PRIMARY KEY,           -- same file is never processed twice
    rows_read     INT NOT NULL,
    rows_loaded   INT NOT NULL,
    rows_rejected INT NOT NULL,
    loaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
