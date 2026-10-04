"""
Create the database and tables by running sql/schema.sql through Python.
Means the EC2 server does not need a MySQL client installed.
Run:  python src/init_db.py
"""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

import config

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")


def main():
    url = make_url(config.DB_URL)
    server = create_engine(url.set(database=""))   # connect without a database first
    sql = open(SCHEMA).read()
    statements = []
    for stmt in sql.split(";"):
        lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    with server.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    print(f"Schema ready ({len(statements)} statements) on {url.host}")


if __name__ == "__main__":
    main()
