#!/bin/bash
set -e

echo "=========================================="
echo "  RIHAN PLATFORM - Starting Container"
echo "=========================================="

cd /app/src 2>/dev/null || cd /app

echo "[1/6] Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

until python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "ERROR: PostgreSQL did not become ready in time"
        exit 1
    fi
    echo "  PostgreSQL not ready yet. Retrying in 2 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done
echo "  ✓ PostgreSQL is ready"

echo "[2/6] Running database migrations..."
python manage.py migrate --noinput
echo "  ✓ Migrations completed"

echo "[3/6] Collecting static files..."
python manage.py collectstatic --noinput --clear 2>/dev/null || echo "  ⚠ Static collection skipped"
echo "  ✓ Static files processed"

echo "[4/6] Loading seed data (if available)..."
if [ -f "fixtures/initial_data.json" ]; then
    python manage.py loaddata initial_data --ignorenonexistent 2>/dev/null || echo "  ⚠ Seed data load skipped"
else
    echo "  ⚠ No fixtures/initial_data.json found - skipping seed data"
fi

echo "[5/6] Ensuring admin superuser exists..."
python manage.py shell << 'SHELL_EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('ADMIN_USERNAME', 'admin')
email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
phone = os.environ.get('ADMIN_PHONE', '09120000000')
password = os.environ.get('ADMIN_BACKUP_PASSWORD')

try:
    if not User.objects.filter(username=username).exists():
        if password and password != 'CHANGE_ME_STRONG_ADMIN_PASSWORD':
            try:
                User.objects.create_superuser(username=username, email=email, password=password)
            except TypeError:
                User.objects.create_superuser(username=username, email=email, password=password, phone=phone)
            print(f"  ✓ Admin superuser '{username}' created successfully")
        else:
            print("  ⚠ WARNING: ADMIN_BACKUP_PASSWORD not set. Skipping auto-creation.")
    else:
        print(f"  ✓ Admin user '{username}' already exists")
except Exception as e:
    print(f"  ⚠ Admin check note: {e}")
SHELL_EOF
echo "  ✓ Admin user check completed"

echo "[6/6] Starting Gunicorn server..."
echo "=========================================="
echo "  RIHAN PLATFORM - Ready!"
echo "  Listening on 0.0.0.0:8000"
echo "=========================================="

exec gunicorn rihan.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
