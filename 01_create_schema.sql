-- ============================================================
-- SCHEMA: E-Commerce Analytics Database
-- Run this after loading the CSVs (see load_data.py)
-- ============================================================

DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    customer_id     TEXT PRIMARY KEY,
    customer_name   TEXT,
    customer_state  TEXT,
    customer_city   TEXT,
    signup_date     DATE
);

DROP TABLE IF EXISTS products;
CREATE TABLE products (
    product_id        TEXT PRIMARY KEY,
    product_category  TEXT,
    price              REAL,
    weight_g           INTEGER
);

DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    order_id            TEXT PRIMARY KEY,
    customer_id         TEXT,
    order_purchase_ts   DATETIME,
    order_status        TEXT,
    delivered_ts         DATETIME,
    delivery_days        INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

DROP TABLE IF EXISTS order_items;
CREATE TABLE order_items (
    order_item_id  INTEGER PRIMARY KEY,
    order_id       TEXT,
    product_id     TEXT,
    quantity       INTEGER,
    unit_price     REAL,
    freight_value  REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

DROP TABLE IF EXISTS order_payments;
CREATE TABLE order_payments (
    order_id       TEXT,
    payment_type   TEXT,
    installments   INTEGER,
    payment_value  REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

DROP TABLE IF EXISTS order_reviews;
CREATE TABLE order_reviews (
    order_id      TEXT,
    review_score  INTEGER,
    review_ts     DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);
