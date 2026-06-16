-- Demo dataset for the sales connection. Loaded automatically by the official
-- postgres image when this file is mounted under /docker-entrypoint-initdb.d/.
-- The platform connects to this database as the "sales_db" connection and the
-- analyst sees real rows (not fake_rows) when running SELECTs.

CREATE SCHEMA IF NOT EXISTS sales;
SET search_path = sales, public;

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price       NUMERIC(10, 2) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    phone       TEXT NOT NULL,
    rrn         TEXT NOT NULL,
    city        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE orders (
    id           SERIAL PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id),
    product_id   INTEGER NOT NULL REFERENCES products(id),
    amount       NUMERIC(10, 2) NOT NULL,
    status       TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_created ON orders(created_at);

-- 50 products
INSERT INTO products (name, category, price)
SELECT
    'Product-' || g                                                AS name,
    (ARRAY['Electronics','Books','Apparel','Home','Sports'])[(g % 5) + 1] AS category,
    (1000 + (g * 137) % 90000)::NUMERIC / 10                       AS price
FROM generate_series(1, 50) AS g;

-- 1500 customers with realistic-shaped PII fields
INSERT INTO customers (name, email, phone, rrn, city)
SELECT
    (ARRAY['Park Min-jun','Kim Ji-soo','Lee Seo-yeon','Choi Eun-woo',
           'Jung Ha-yoon','Kang Do-yoon','Yoon Si-ah','Han Yu-jin',
           'Cho Da-eun','Im Joon-ho','Seo Min-ji','Bae Hye-rin'])[(g % 12) + 1]
        || ' ' || (g)::TEXT                                                       AS name,
    'user' || lpad(g::TEXT, 6, '0') || '@customer.example'                        AS email,
    '010-' || lpad(((g * 37) % 10000)::TEXT, 4, '0')
        || '-' || lpad(((g * 73) % 10000)::TEXT, 4, '0')                          AS phone,
    lpad(((g % 999999) + 1)::TEXT, 6, '0')
        || '-' || lpad(((g * 17) % 10000000)::TEXT, 7, '0')                       AS rrn,
    (ARRAY['Seoul','Busan','Incheon','Daegu','Daejeon','Gwangju','Suwon','Ulsan'])
        [(g % 8) + 1]                                                              AS city
FROM generate_series(1, 1500) AS g;

-- 5000 orders with mixed statuses and dates over the last ~6 months
INSERT INTO orders (customer_id, product_id, amount, status, created_at)
SELECT
    ((g * 7) % 1500) + 1                                                   AS customer_id,
    ((g * 11) % 50) + 1                                                    AS product_id,
    (5000 + (g * 421) % 95000)::NUMERIC / 10                               AS amount,
    (ARRAY['pending','paid','shipped','delivered','cancelled'])[(g % 5) + 1] AS status,
    NOW() - ((g % 180) || ' days')::INTERVAL
         + ((g % 24) || ' hours')::INTERVAL                                AS created_at
FROM generate_series(1, 5000) AS g;

ANALYZE products;
ANALYZE customers;
ANALYZE orders;
