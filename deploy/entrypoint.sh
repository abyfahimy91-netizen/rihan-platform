#!/bin/bash
# =============================================================================
# RIHAN PLATFORM - Docker Entrypoint Script
# =============================================================================
# این اسکریپت هنگام شروع کانتینر web اجرا می‌شود و Cold Start خودکار را انجام می‌دهد.
# مطابق الزام ناظر: اپراتور غیربرنامه‌نویس نباید درگیر دستورات دستی شود.
# =============================================================================

set -e  # توقف در صورت خطا

echo "=========================================="
echo "  RIHAN PLATFORM - Starting Container"
echo "=========================================="

# -----------------------------------------------------------------------------
# مرحله ۱: انتظار برای آماده شدن دیتابیس
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# مرحله ۲: اجرای Migrations (ADR-002 / ADR-008)
# -----------------------------------------------------------------------------
echo "[2/6] Running database migrations..."
python manage.py migrate --noinput
echo "  ✓ Migrations completed"

# -----------------------------------------------------------------------------
# مرحله ۳: جمع‌آوری فایل‌های استاتیک (ADR-007)
# -----------------------------------------------------------------------------
echo "[3/6] Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "  ✓ Static files collected"

# -----------------------------------------------------------------------------
# مرحله ۴: بارگذاری داده‌های اولیه (Seed Data)
# -----------------------------------------------------------------------------
echo "[4/6] Loading seed data (if available)..."
if [ -f "fixtures/initial_data.json" ]; then
    python manage.py loaddata initial_data --ignorenonexistent 2>/dev/null || echo "  ⚠ Seed data load skipped (already exists or error)"
else
    echo "  ⚠ No fixtures/initial_data.json found - skipping seed data"
fi

# -----------------------------------------------------------------------------
# مرحله ۵: ایجاد Superuser اولیه (فقط اگر وجود نداشته باشد)
# -----------------------------------------------------------------------------
echo "[5/6] Ensuring admin superuser exists..."
python manage.py shell << 'SHELL_EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('ADMIN_USERNAME', 'admin')
email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
phone = os.environ.get('ADMIN_PHONE', '09120000000')
password = os.environ.get('ADMIN_BACKUP_PASSWORD')

# بررسی وجود کاربر
try:
    user = User.objects.get(username=username)
    print(f"  ✓ Admin user '{username}' already exists")
except User.DoesNotExist:
    if not password or password == 'CHANGE_ME_STRONG_ADMIN_PASSWORD':
        print("  ⚠ WARNING: ADMIN_BACKUP_PASSWORD not set or is default. Skipping auto-creation.")
        print("    Please set a strong password in .env and restart, or create manually with:")
        print("    docker-compose exec web python manage.py createsuperuser")
    else:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            phone=phone,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        print(f"  ✓ Admin superuser '{username}' created successfully")
SHELL_EOF
echo "  ✓ Admin user check completed"

# -----------------------------------------------------------------------------
# مرحله ۶: شروع Gunicorn (Web Server)
# -----------------------------------------------------------------------------
echo "[6/6] Starting Gunicorn server..."
echo "=========================================="
echo "  RIHAN PLATFORM - Ready!"
echo "  Listening on 0.0.0.0:8000"
echo "=========================================="

# اجرای Gunicorn با exec برای جایگزینی shell (سیگنال‌ها درست کار می‌کنند)
exec gunicorn rihan.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
