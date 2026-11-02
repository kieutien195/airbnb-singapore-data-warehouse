"""Check the local .env connection to the Airbnb MySQL database safely."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    import os

    host = os.getenv("MYSQL_HOST", "localhost")
    port_text = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "airbnb_sg_2026")

    if not user or not password:
        print("FAIL: MYSQL_USER and MYSQL_PASSWORD must be set in the local .env file.")
        return 1

    try:
        port = int(port_text)
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print("FAIL: MYSQL_PORT must be an integer between 1 and 65535.")
        return 1

    url = URL.create(
        "mysql+pymysql",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"charset": "utf8mb4"},
    )
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})

    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT VERSION(), DATABASE(), "
                    "@@character_set_connection, @@collation_connection"
                )
            ).one()
        print(f"PASS: Connected to {row[1]} on MySQL {row[0]}.")
        print(f"PASS: Connection charset/collation: {row[2]} / {row[3]}.")
        return 0
    except Exception as exc:  # Never print the driver exception; it can include URL details.
        print(
            "FAIL: MySQL connection check failed "
            f"({type(exc).__name__}). Check that MySQL is running and the local .env "
            "contains the correct host, port, user, password, and database."
        )
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
