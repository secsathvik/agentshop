#!/usr/bin/env python
"""Create the agentshop database if it doesn't exist. Run before alembic upgrade."""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    parsed = urlparse(settings.database_sync_url)
    base_url = f"postgresql://{parsed.netloc}/postgres"
    db_name = parsed.path.strip("/") or "agentshop"

    try:
        conn = psycopg2.connect(base_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,),
        )
        exists = cur.fetchone()
        if exists:
            print(f"Database '{db_name}' already exists.")
        else:
            cur.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database '{db_name}'.")
        cur.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
