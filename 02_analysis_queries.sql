-- ============================================================
-- ANALYSIS QUERIES
-- Each query answers a specific business question.
-- Run against ecommerce.db (created by load_data.py)
-- ============================================================

-- --------------------------------------------------------------
-- Q1. Monthly revenue trend
-- (Total revenue = item price*qty + freight, delivered orders only)
-- --------------------------------------------------------------
SELECT
    strftime('%Y-%m', o.order_purchase_ts) AS order_month,
    ROUND(SUM(oi.unit_price * oi.quantity + oi.freight_value), 2) AS revenue,
    COUNT(DISTINCT o.order_id) AS num_orders
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY order_month
ORDER BY order_month;


-- --------------------------------------------------------------
-- Q2. Top 10 product categories by revenue
-- --------------------------------------------------------------
SELECT
    p.product_category,
    ROUND(SUM(oi.unit_price * oi.quantity), 2) AS category_revenue,
    COUNT(DISTINCT oi.order_id) AS num_orders
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY p.product_category
ORDER BY category_revenue DESC
LIMIT 10;


-- --------------------------------------------------------------
-- Q3. Customer lifetime value ranking (window function)
-- Ranks every customer by total spend, and shows their rank
-- within their own state too.
-- --------------------------------------------------------------
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_state,
    ROUND(SUM(oi.unit_price * oi.quantity + oi.freight_value), 2) AS lifetime_value,
    RANK() OVER (ORDER BY SUM(oi.unit_price * oi.quantity + oi.freight_value) DESC) AS overall_rank,
    RANK() OVER (PARTITION BY c.customer_state
                 ORDER BY SUM(oi.unit_price * oi.quantity + oi.freight_value) DESC) AS state_rank
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_id, c.customer_name, c.customer_state
ORDER BY lifetime_value DESC
LIMIT 25;


-- --------------------------------------------------------------
-- Q4. Delivery speed vs review score
-- (Does shipping slowly actually hurt customer satisfaction?)
-- --------------------------------------------------------------
SELECT
    CASE
        WHEN o.delivery_days <= 7 THEN '1. Fast (<=7 days)'
        WHEN o.delivery_days <= 14 THEN '2. Medium (8-14 days)'
        ELSE '3. Slow (15+ days)'
    END AS delivery_bucket,
    ROUND(AVG(r.review_score), 2) AS avg_review_score,
    COUNT(*) AS num_orders
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY delivery_bucket
ORDER BY delivery_bucket;


-- --------------------------------------------------------------
-- Q5. Repeat vs one-time customers (running total, window function)
-- --------------------------------------------------------------
WITH order_counts AS (
    SELECT customer_id, COUNT(*) AS num_orders
    FROM orders
    WHERE order_status = 'delivered'
    GROUP BY customer_id
)
SELECT
    CASE WHEN num_orders = 1 THEN 'One-time' ELSE 'Repeat' END AS customer_type,
    COUNT(*) AS num_customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_customers
FROM order_counts
GROUP BY customer_type;


-- --------------------------------------------------------------
-- Q6. Payment method breakdown by revenue share
-- --------------------------------------------------------------
SELECT
    payment_type,
    COUNT(*) AS num_payments,
    ROUND(SUM(payment_value), 2) AS total_value,
    ROUND(100.0 * SUM(payment_value) / SUM(SUM(payment_value)) OVER (), 1) AS pct_of_revenue
FROM order_payments
GROUP BY payment_type
ORDER BY total_value DESC;


-- --------------------------------------------------------------
-- Q7. Month-over-month revenue growth (LAG window function)
-- --------------------------------------------------------------
WITH monthly AS (
    SELECT
        strftime('%Y-%m', o.order_purchase_ts) AS order_month,
        SUM(oi.unit_price * oi.quantity + oi.freight_value) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY order_month
)
SELECT
    order_month,
    ROUND(revenue, 2) AS revenue,
    ROUND(revenue - LAG(revenue) OVER (ORDER BY order_month), 2) AS mom_change,
    ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
          / LAG(revenue) OVER (ORDER BY order_month), 1) AS mom_pct_change
FROM monthly
ORDER BY order_month;
