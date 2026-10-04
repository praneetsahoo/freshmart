"""
Component 1: Generate realistic (and deliberately MESSY) FreshMart sales data.

Why: on hackathon day the SME gives only a few sample files. We need enough
data to (a) test our cleaning logic and (b) show anomalies in the demo.

Output:
  data/master/stores.csv     - store master
  data/master/products.csv   - product master
  data/raw/<date>/<store_id>.csv  - one sales file per store per day

Run:  python src/generate_data.py
"""
import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ---------------- settings (small for demo, can scale up) ----------------
NUM_STORES = 10          # real chain has 45; 10 keeps the demo fast
NUM_DAYS = 30
TX_PER_STORE_DAY = 300   # real is ~2,000-5,000; change for load testing
START_DATE = date(2026, 9, 1)
SEED = 42

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
random.seed(SEED)
np.random.seed(SEED)

REGIONS = {"Delhi": "North", "Gurugram": "North", "Noida": "North",
           "Chandigarh": "North", "Jaipur": "West", "Lucknow": "Central"}

PRODUCTS = [  # product_id, name, category, price
    ("P001", "Basmati Rice 5kg", "Grains", 650), ("P002", "Wheat Atta 10kg", "Grains", 480),
    ("P003", "Toor Dal 1kg", "Pulses", 160), ("P004", "Moong Dal 1kg", "Pulses", 140),
    ("P005", "Amul Milk 1L", "Dairy", 68), ("P006", "Paneer 200g", "Dairy", 90),
    ("P007", "Curd 400g", "Dairy", 45), ("P008", "Tomato 1kg", "Vegetables", 40),
    ("P009", "Onion 1kg", "Vegetables", 35), ("P010", "Potato 1kg", "Vegetables", 30),
    ("P011", "Banana Dozen", "Fruits", 60), ("P012", "Apple 1kg", "Fruits", 180),
    ("P013", "Sunflower Oil 1L", "Oils", 150), ("P014", "Mustard Oil 1L", "Oils", 170),
    ("P015", "Tea 500g", "Beverages", 260), ("P016", "Coffee 200g", "Beverages", 320),
    ("P017", "Biscuits Pack", "Snacks", 30), ("P018", "Chips 100g", "Snacks", 20),
    ("P019", "Detergent 1kg", "Household", 120), ("P020", "Soap Pack of 4", "Household", 110),
]


def make_masters():
    cities = list(REGIONS)
    stores = [{
        "store_id": f"S{i:03d}",
        "city": cities[(i - 1) % len(cities)],
        "region": REGIONS[cities[(i - 1) % len(cities)]],
        "store_manager": f"Manager {i}",
    } for i in range(1, NUM_STORES + 1)]
    pd.DataFrame(stores).to_csv(f"{BASE}/master/stores.csv", index=False)

    products = pd.DataFrame(PRODUCTS, columns=["product_id", "product_name", "category", "list_price"])
    products.to_csv(f"{BASE}/master/products.csv", index=False)
    return pd.DataFrame(stores), products


def messy_name(name):
    """Simulate stores typing product names differently."""
    return random.choice([name, name.upper(), name.lower(), f"  {name} ", name.replace(" ", "-")])


def messy_date(d):
    """Simulate different billing systems using different date formats."""
    return random.choice([d.strftime("%Y-%m-%d"), d.strftime("%d/%m/%Y"), d.strftime("%d-%m-%Y")])


def make_sales(stores, products):
    tx_counter = 0
    store_ids = list(stores["store_id"])
    # each store has its own "normal" size so z-score is per store
    store_scale = {s: np.random.uniform(0.7, 1.3) for s in store_ids}

    for day in range(NUM_DAYS):
        d = START_DATE + timedelta(days=day)
        os.makedirs(f"{BASE}/raw/{d}", exist_ok=True)

        for s in store_ids:
            n = int(TX_PER_STORE_DAY * store_scale[s] * np.random.uniform(0.9, 1.1))
            # planted anomalies for the demo (last day)
            if day == NUM_DAYS - 1 and s == "S003":
                n *= 3                      # spike: festival / data error?
            if day == NUM_DAYS - 1 and s == "S007":
                n = int(n * 0.2)            # dip: store outage?

            rows = []
            for _ in range(n):
                tx_counter += 1
                pid, pname, _, price = random.choice(PRODUCTS)
                rows.append({
                    "transaction_id": f"T{tx_counter:08d}",
                    "store_id": s,
                    "date": messy_date(d),
                    "product_id": pid if random.random() > 0.05 else "",   # 5% missing ID
                    "product_name": messy_name(pname),
                    "quantity": random.randint(1, 5) if random.random() > 0.01 else "",  # 1% missing qty
                    "unit_price": price if random.random() > 0.03 else "",               # 3% missing price
                    "payment_mode": random.choice(["UPI", "Cash", "Card"]),
                })
            df = pd.DataFrame(rows)
            # 2% duplicate rows (billing system exported twice)
            dupes = df.sample(frac=0.02, random_state=day)
            df = pd.concat([df, dupes]).sample(frac=1, random_state=day)
            df.to_csv(f"{BASE}/raw/{d}/{s}.csv", index=False)

    print(f"Generated {NUM_DAYS} days x {len(store_ids)} stores, {tx_counter:,} transactions")


if __name__ == "__main__":
    os.makedirs(f"{BASE}/master", exist_ok=True)
    stores, products = make_masters()
    make_sales(stores, products)
