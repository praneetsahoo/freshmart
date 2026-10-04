"""
Component 6: Management dashboard (Streamlit).

Reads ONLY from MySQL (RDS on AWS) - never from raw files.
Run:  streamlit run dashboard/app.py
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import config  # noqa: E402

st.set_page_config(page_title="FreshMart Store Performance", layout="wide")


@st.cache_resource
def get_engine():
    return create_engine(config.DB_URL, pool_pre_ping=True)


@st.cache_data(ttl=300)   # cache query results for 5 min so the dashboard stays fast
def q(sql, **params):
    return pd.read_sql(sql, get_engine(), params=params)


# ---------------- filters ----------------
dates = q("SELECT DISTINCT sale_date FROM fact_sales ORDER BY sale_date")["sale_date"]
if dates.empty:
    st.warning("No data loaded yet. Run the ETL first: python src/etl.py")
    st.stop()

regions = ["All"] + q("SELECT DISTINCT region FROM dim_store ORDER BY region")["region"].tolist()
st.sidebar.header("Filters")
day = st.sidebar.date_input("Business date", value=dates.max(),
                            min_value=dates.min(), max_value=dates.max())
region = st.sidebar.selectbox("Region", regions)
region_sql = "" if region == "All" else "AND s.region = %(region)s"
params = {"day": day, "region": region}

st.title("🛒 FreshMart Store Performance")
st.caption(f"Business date: {day} · Region: {region} · Source: AWS RDS MySQL")

# ---------------- anomaly alerts first: the most actionable thing ----------------
alerts = q(f"""SELECT a.store_id, s.city, a.revenue, a.expected_revenue, a.z_score, a.direction
               FROM sales_anomaly a JOIN dim_store s USING (store_id)
               WHERE a.sale_date = %(day)s {region_sql}""", **params)
for r in alerts.itertuples():
    change = (r.revenue - r.expected_revenue) / r.expected_revenue * 100
    msg = (f"**{r.store_id} ({r.city})**: revenue ₹{r.revenue:,.0f} vs normal "
           f"₹{r.expected_revenue:,.0f} ({change:+.0f}%)")
    (st.error if r.direction == "LOW" else st.warning)(("🔻 Unusual DROP — " if r.direction == "LOW"
                                                        else "🔺 Unusual SPIKE — ") + msg)

# ---------------- KPIs vs previous day ----------------
kpi_sql = f"""SELECT f.sale_date, SUM(f.amount) revenue, COUNT(*) txns, COUNT(DISTINCT f.store_id) stores
              FROM fact_sales f JOIN dim_store s USING (store_id)
              WHERE f.sale_date IN (%(day)s, DATE_SUB(%(day)s, INTERVAL 1 DAY)) {region_sql}
              GROUP BY f.sale_date ORDER BY f.sale_date"""
kpi = q(kpi_sql, **params).set_index("sale_date")
today = kpi.iloc[-1]
prev = kpi.iloc[0] if len(kpi) == 2 else None


def delta(col):
    return None if prev is None else f"{(today[col] - prev[col]) / prev[col] * 100:+.1f}% vs prev day"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"₹{today.revenue:,.0f}", delta("revenue"))
c2.metric("Transactions", f"{int(today.txns):,}", delta("txns"))
c3.metric("Avg bill", f"₹{today.revenue / today.txns:,.0f}")
c4.metric("Stores reporting", int(today.stores))

# ---------------- breakdowns ----------------
left, right = st.columns(2)
with left:
    st.subheader("Revenue by region")
    by_region = q(f"""SELECT s.region, SUM(f.amount) revenue FROM fact_sales f
                      JOIN dim_store s USING (store_id)
                      WHERE f.sale_date = %(day)s {region_sql}
                      GROUP BY s.region ORDER BY revenue DESC""", **params)
    st.bar_chart(by_region, x="region", y="revenue", horizontal=True)
with right:
    st.subheader("Revenue by category")
    by_cat = q(f"""SELECT p.category, SUM(f.amount) revenue FROM fact_sales f
                   JOIN dim_product p USING (product_id) JOIN dim_store s USING (store_id)
                   WHERE f.sale_date = %(day)s {region_sql}
                   GROUP BY p.category ORDER BY revenue DESC""", **params)
    st.bar_chart(by_cat, x="category", y="revenue", horizontal=True)

left, right = st.columns(2)
with left:
    st.subheader("Top 10 products")
    top = q(f"""SELECT p.product_name AS product, p.category, SUM(f.quantity) units,
                       SUM(f.amount) revenue
                FROM fact_sales f JOIN dim_product p USING (product_id) JOIN dim_store s USING (store_id)
                WHERE f.sale_date = %(day)s {region_sql}
                GROUP BY p.product_name, p.category ORDER BY revenue DESC LIMIT 10""", **params)
    st.dataframe(top, hide_index=True, width="stretch",
                 column_config={"revenue": st.column_config.NumberColumn(format="₹%d")})
with right:
    st.subheader("Store league table")
    stores = q(f"""SELECT s.store_id, s.city, s.region, SUM(f.amount) revenue, COUNT(*) txns
                   FROM fact_sales f JOIN dim_store s USING (store_id)
                   WHERE f.sale_date = %(day)s {region_sql}
                   GROUP BY s.store_id, s.city, s.region ORDER BY revenue DESC""", **params)
    st.dataframe(stores, hide_index=True, width="stretch",
                 column_config={"revenue": st.column_config.NumberColumn(format="₹%d")})

# ---------------- trend with anomaly markers (Matplotlib) ----------------
st.subheader("Daily revenue trend")
store_ids = stores["store_id"].tolist()
default = alerts["store_id"].tolist() or store_ids[:3]
chosen = st.multiselect("Stores", store_ids, default=default)
if chosen:
    trend = q("""SELECT store_id, sale_date, SUM(amount) revenue FROM fact_sales
                 WHERE sale_date <= %(day)s GROUP BY store_id, sale_date""", day=day)
    flags = q("SELECT store_id, sale_date, revenue FROM sales_anomaly WHERE sale_date <= %(day)s", day=day)
    fig, ax = plt.subplots(figsize=(11, 3.6))
    for sid in chosen:
        t = trend[trend.store_id == sid].sort_values("sale_date")
        ax.plot(t.sale_date, t.revenue / 1000, marker="o", markersize=3, label=sid)
        f = flags[flags.store_id == sid]
        ax.scatter(f.sale_date, f.revenue.astype(float) / 1000, s=160, facecolors="none",
                   edgecolors="red", linewidths=2, zorder=5)
    ax.set_ylabel("Revenue (₹ thousand)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", ncols=len(chosen))
    ax.set_title("Red circles = flagged anomalies", fontsize=10, loc="right", color="red")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    st.pyplot(fig)

# ---------------- pipeline health: proves the data can be trusted ----------------
with st.expander("Pipeline health (ETL audit)"):
    audit = q("""SELECT COUNT(*) files, SUM(rows_read) rows_read, SUM(rows_loaded) rows_loaded,
                        SUM(rows_rejected) rows_rejected, MAX(loaded_at) last_load FROM etl_audit""")
    a = audit.iloc[0]
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Files processed", int(a.files))
    d2.metric("Rows loaded", f"{int(a.rows_loaded):,}")
    d3.metric("Rows rejected", f"{int(a.rows_rejected):,}")
    d4.metric("Duplicates removed", f"{int(a.rows_read - a.rows_loaded - a.rows_rejected):,}")
    st.caption(f"Last load: {a.last_load}. Rejected rows are kept in rejected/ with a reason.")
