"""
Component 4: Flag unusual store-days using a z-score.

For each store and day:
    expected = mean revenue of that store's previous 14 days
    z        = (today - expected) / std of those 14 days
    |z| > 3 AND at least 30% away from expected -> anomaly (HIGH / LOW)

Why the 30% rule: if a store's history is very flat, std is tiny and even a 1%
wobble gives a huge z-score. The % rule keeps alerts to changes a manager cares about.

Why per store: a big store's normal day would look like a "spike" for a small store.
Why previous days only (shift 1): today must not be part of its own baseline.
"""
import numpy as np
import pandas as pd
from sqlalchemy import text

import config


def compute_anomalies(daily, window=config.ANOMALY_WINDOW_DAYS,
                      min_history=config.ANOMALY_MIN_HISTORY,
                      threshold=config.ANOMALY_Z_THRESHOLD,
                      min_pct=config.ANOMALY_MIN_PCT):
    """
    Input : DataFrame [store_id, sale_date, revenue] - one row per store per day
    Output: only the anomalous rows, with expected_revenue, z_score, direction
    Pure function (no DB) so it can be unit tested.
    """
    daily = daily.sort_values(["store_id", "sale_date"]).copy()
    grouped = daily.groupby("store_id")["revenue"]
    baseline = grouped.transform(lambda s: s.shift(1).rolling(window, min_periods=min_history).mean())
    spread = grouped.transform(lambda s: s.shift(1).rolling(window, min_periods=min_history).std())

    daily["expected_revenue"] = baseline
    daily["z_score"] = (daily["revenue"] - baseline) / spread.replace(0, np.nan)
    pct_change = (daily["revenue"] - baseline) / baseline
    flagged = daily[(daily["z_score"].abs() > threshold) & (pct_change.abs() >= min_pct)].copy()
    flagged["direction"] = np.where(flagged["z_score"] > 0, "HIGH", "LOW")
    flagged["expected_revenue"] = flagged["expected_revenue"].round(2)
    flagged["z_score"] = flagged["z_score"].round(2)
    return flagged[["store_id", "sale_date", "revenue", "expected_revenue", "z_score", "direction"]]


def run(engine):
    daily = pd.read_sql("""
        SELECT store_id, sale_date, SUM(amount) AS revenue
        FROM fact_sales GROUP BY store_id, sale_date""", engine)
    daily["revenue"] = daily["revenue"].astype(float)
    flagged = compute_anomalies(daily)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sales_anomaly"))   # recompute fully each run (small table)
        if len(flagged):
            conn.execute(text("""
                INSERT INTO sales_anomaly (store_id, sale_date, revenue, expected_revenue, z_score, direction)
                VALUES (:store_id, :sale_date, :revenue, :expected_revenue, :z_score, :direction)"""),
                flagged.to_dict("records"))

    print(f"Anomalies flagged: {len(flagged)}")
    for r in flagged.itertuples():
        print(f"  {r.store_id} {r.sale_date}: revenue {r.revenue:,.0f} vs expected "
              f"{r.expected_revenue:,.0f} (z={r.z_score}, {r.direction})")
    return flagged
