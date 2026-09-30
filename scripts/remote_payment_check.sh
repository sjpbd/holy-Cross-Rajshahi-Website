#!/bin/bash
# Runs ON the VPS (piped over SSH by: scripts/deploy.sh payment-check).
# Clears the cached gateway token, expires unfinished sandbox attempts, checks the
# live JanataPay connection from this (whitelisted) server, and installs the cron jobs.
set -euo pipefail

APP=/home/holycross/holycross
APP_USER=holycross
PY="$APP/venv/bin/python"
LOG_DIR=/home/holycross/logs

as_app() { sudo -u "$APP_USER" "$@"; }
cd "$APP"

echo "=== SETTINGS ==="
as_app "$PY" manage.py shell -c "
from django.conf import settings as s
print('DEBUG           =', s.DEBUG)
print('PAYMENT_GATEWAY =', s.PAYMENT_GATEWAY)
print('BASE_URL        =', s.JANATAPAY_BASE_URL)
print('MERCHANT_UID    =', s.JANATAPAY_MERCHANT_UID)
print('SECRET_KEY set  =', not s.SECRET_KEY.startswith('django-insecure'))
"

echo "=== RESET GATEWAY STATE ==="
as_app "$PY" manage.py shell -c "
from django.conf import settings
from admissions.models import GatewayAuthToken, PaymentAttempt
print('cached tokens cleared:', GatewayAuthToken.objects.all().delete()[0])
if 'sandbox' not in settings.JANATAPAY_BASE_URL:
    n = PaymentAttempt.objects.filter(gateway='janatapay', status='started', verified_at__isnull=True).update(status='expired')
    print('unfinished sandbox attempts expired:', n)
"

echo "=== LIVE CONNECTION CHECK ==="
as_app "$PY" manage.py janatapay_check

echo "=== CRON ==="
mkdir -p "$LOG_DIR"
chown "$APP_USER:$APP_USER" "$LOG_DIR"
CURRENT=$(crontab -u "$APP_USER" -l 2>/dev/null || true)
NEW="$CURRENT"
if ! grep -q reconcile_payments <<<"$CURRENT"; then
  NEW="$NEW"$'\n'"*/5 * * * * cd $APP && $PY manage.py reconcile_payments >> $LOG_DIR/payments.log 2>&1"
fi
if ! grep -q expire_admission_holds <<<"$CURRENT"; then
  NEW="$NEW"$'\n'"*/10 * * * * cd $APP && $PY manage.py expire_admission_holds >> $LOG_DIR/holds.log 2>&1"
fi
if [ "$NEW" != "$CURRENT" ]; then
  printf '%s\n' "$NEW" | sed '/^$/d' | crontab -u "$APP_USER" -
  echo "cron jobs installed"
fi
crontab -u "$APP_USER" -l

echo "=== DONE ==="
