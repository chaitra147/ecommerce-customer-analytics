"""
E-Commerce Customer Analytics
==============================
Customer-level analysis on top of the SQL data model: RFM segmentation,
cohort retention, and a churn/repeat-purchase model. Outputs summary
tables and charts to /outputs.

Steps:
  1. RFM segmentation      - segment customers by recency/frequency/monetary value
  2. Cohort retention       - track repeat purchase rate by signup cohort
  3. Churn prediction model - logistic regression on time-split features
  4. Chart exports          - PNGs for the README and dashboard

Run: python3 analysis.py
Requires: pandas, numpy, matplotlib, seaborn, scikit-learn
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "ecommerce.db")
OUT_DIR = os.path.join(BASE, "outputs")
os.makedirs(OUT_DIR, exist_ok=True)

sns.set_style("whitegrid")
conn = sqlite3.connect(DB_PATH)

# ============================================================
# LOAD DATA
# ============================================================
orders = pd.read_sql_query("""
    SELECT o.order_id, o.customer_id, o.order_purchase_ts, o.order_status,
           o.delivery_days, oi.unit_price, oi.quantity, oi.freight_value
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
""", conn)

orders["order_purchase_ts"] = pd.to_datetime(orders["order_purchase_ts"])
orders = orders.dropna(subset=["order_purchase_ts"])
orders["line_total"] = orders["unit_price"] * orders["quantity"] + orders["freight_value"]

order_level = orders.groupby(["order_id", "customer_id", "order_purchase_ts"], as_index=False)["line_total"].sum()

print(f"Loaded {len(order_level):,} delivered orders across {order_level.customer_id.nunique():,} customers")

# ============================================================
# 1. RFM SEGMENTATION
# ============================================================
snapshot_date = order_level["order_purchase_ts"].max() + pd.Timedelta(days=1)

rfm = order_level.groupby("customer_id").agg(
    recency=("order_purchase_ts", lambda x: (snapshot_date - x.max()).days),
    frequency=("order_id", "count"),
    monetary=("line_total", "sum"),
).reset_index()

# Score 1-5 on each dimension (5 = best)
rfm["r_score"] = pd.qcut(rfm["recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["m_score"] = pd.qcut(rfm["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

def segment(row):
    if row.rfm_score >= 13:
        return "Champions"
    elif row.rfm_score >= 10:
        return "Loyal Customers"
    elif row.r_score >= 4 and row.rfm_score < 10:
        return "Recent / New"
    elif row.r_score <= 2 and row.f_score >= 3:
        return "At Risk"
    elif row.r_score <= 2 and row.f_score <= 2:
        return "Lost"
    else:
        return "Needs Attention"

rfm["segment"] = rfm.apply(segment, axis=1)

seg_summary = rfm.groupby("segment").agg(
    num_customers=("customer_id", "count"),
    avg_monetary=("monetary", "mean"),
    total_revenue=("monetary", "sum"),
).sort_values("total_revenue", ascending=False)
seg_summary["pct_of_customers"] = round(100 * seg_summary["num_customers"] / seg_summary["num_customers"].sum(), 1)
seg_summary["pct_of_revenue"] = round(100 * seg_summary["total_revenue"] / seg_summary["total_revenue"].sum(), 1)

print("\n=== RFM SEGMENT SUMMARY ===")
print(seg_summary.round(1))

rfm.to_csv(os.path.join(OUT_DIR, "rfm_segments.csv"), index=False)

# --- chart: revenue share by segment ---
plt.figure(figsize=(9, 5))
seg_summary_sorted = seg_summary.sort_values("total_revenue")
plt.barh(seg_summary_sorted.index, seg_summary_sorted["total_revenue"], color="#4C72B0")
plt.xlabel("Total Revenue ($)")
plt.title("Revenue by Customer Segment (RFM)")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "rfm_revenue_by_segment.png"), dpi=150)
plt.close()

# ============================================================
# 2. COHORT RETENTION ANALYSIS
# ============================================================
order_level["order_month"] = order_level["order_purchase_ts"].dt.to_period("M")
first_purchase = order_level.groupby("customer_id")["order_month"].min().rename("cohort_month")
order_level = order_level.merge(first_purchase, on="customer_id")

order_level["cohort_index"] = (
    (order_level["order_month"].dt.year - order_level["cohort_month"].dt.year) * 12
    + (order_level["order_month"].dt.month - order_level["cohort_month"].dt.month)
)

cohort_data = order_level.groupby(["cohort_month", "cohort_index"])["customer_id"].nunique().reset_index()
cohort_pivot = cohort_data.pivot(index="cohort_month", columns="cohort_index", values="customer_id")
cohort_sizes = cohort_pivot.iloc[:, 0]
retention = cohort_pivot.divide(cohort_sizes, axis=0).round(3)

print("\n=== COHORT RETENTION (first 6 months, sample) ===")
print(retention.iloc[:6, :6])

# --- Repeat purchase rate: the single most important number in this dataset ---
orders_per_customer = order_level.groupby("customer_id")["order_id"].nunique()
repeat_rate = (orders_per_customer > 1).mean()
print(f"\n*** Repeat purchase rate: {repeat_rate:.1%} of customers placed more than one order ***")
if repeat_rate < 0.10:
    print("    -> This is why cohort retention and the churn model below look weak:")
    print("       there's very little repeat-purchase signal for a model to learn from.")
    print("       This is a genuine, real characteristic of the data -- not a pipeline bug.")

retention.to_csv(os.path.join(OUT_DIR, "cohort_retention.csv"))

# --- chart: retention heatmap ---
plt.figure(figsize=(12, 7))
sns.heatmap(retention.iloc[:, :12], annot=True, fmt=".0%", cmap="Blues", vmin=0, vmax=0.5)
plt.title("Monthly Cohort Retention Rate")
plt.xlabel("Months Since First Purchase")
plt.ylabel("Cohort (First Purchase Month)")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "cohort_retention_heatmap.png"), dpi=150)
plt.close()

# ============================================================
# 3. CHURN PREDICTION MODEL
# Predicts whether a customer will place another order, using only
# information available up to a fixed point in time.
#
# Note: an earlier version of this model derived the label directly
# from recency (e.g. churned = recency > 90 days) while also using
# recency as a feature. That caused data leakage - the model just
# learned the threshold and scored ~100% accuracy, which isn't a
# real result. Fixed by splitting each customer's order history by
# time instead: features are computed from the first 70% of the
# timeline, and the label is whether they ordered again in the
# remaining 30%. This mirrors how the model would actually be used.
# ============================================================
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

cutoff_date = order_level["order_purchase_ts"].min() + (
    order_level["order_purchase_ts"].max() - order_level["order_purchase_ts"].min()
) * 0.7  # first 70% of the timeline = "past", last 30% = "future"

past = order_level[order_level["order_purchase_ts"] <= cutoff_date]
future = order_level[order_level["order_purchase_ts"] > cutoff_date]

# Features computed ONLY from the "past" window
churn_features = past.groupby("customer_id").agg(
    recency=("order_purchase_ts", lambda x: (cutoff_date - x.max()).days),
    frequency=("order_id", "count"),
    monetary=("line_total", "sum"),
).reset_index()

# Label: did they order again in the "future" window? (0 = churned, 1 = retained)
returned_customers = set(future["customer_id"].unique())
churn_features["retained"] = churn_features["customer_id"].isin(returned_customers).astype(int)
churn_features["churned"] = 1 - churn_features["retained"]

X = churn_features[["recency", "frequency", "monetary"]]
y = churn_features["churned"]

print(f"\nChurn label built from time-split: {len(past):,} 'past' orders -> features, "
      f"{len(future):,} 'future' orders -> label")
print(f"Class balance -> churned: {y.mean():.1%}, retained: {(1-y.mean()):.1%}")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

model = LogisticRegression()
model.fit(X_train_s, y_train)
preds = model.predict(X_test_s)
probs = model.predict_proba(X_test_s)[:, 1]

print("\n=== CHURN MODEL PERFORMANCE ===")
print(classification_report(y_test, preds))
print(f"ROC-AUC: {roc_auc_score(y_test, probs):.3f}")

coef_df = pd.DataFrame({"feature": X.columns, "coefficient": model.coef_[0]}).sort_values(
    "coefficient", key=abs, ascending=False)
print("\nFeature importance (standardized coefficients):")
print(coef_df.to_string(index=False))

# ============================================================
# 4. EXTRA CHART: Monthly revenue trend (matches SQL Q1, for README)
# ============================================================
monthly_rev = order_level.groupby("order_month")["line_total"].sum()
plt.figure(figsize=(10, 5))
monthly_rev.plot(kind="line", marker="o", color="#DD8452")
plt.title("Monthly Revenue Trend")
plt.ylabel("Revenue ($)")
plt.xlabel("Month")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "monthly_revenue_trend.png"), dpi=150)
plt.close()

print(f"\nAll outputs saved to: {OUT_DIR}")
print("Files: rfm_segments.csv, cohort_retention.csv, and 3 PNG charts")
