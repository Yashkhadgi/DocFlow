#!/bin/sh
set -e

# If starting the API server via uvicorn, wait for DB and apply migrations
if [ "$1" = "uvicorn" ] || echo "$*" | grep -q "uvicorn"; then
    echo "Waiting for database connection..."
    python - <<'EOF'
import sys
import time
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)
retries = 30
while retries > 0:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            break
    except Exception as e:
        retries -= 1
        if retries == 0:
            print(f"Database connection failed after 30 retries: {e}", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
EOF
    echo "Database is ready. Applying Alembic migrations..."
    alembic upgrade head
    echo "Alembic migrations completed successfully."
fi

exec "$@"
