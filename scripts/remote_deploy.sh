#!/bin/bash
# Runs ON the VPS (piped over SSH by scripts/deploy.sh).
# Deploys code only: db.sqlite3, media/ and .env are never touched by git.
set -euo pipefail

APP=/home/holycross/holycross
APP_USER=holycross
PY="$APP/venv/bin/python"
PIP="$APP/venv/bin/pip"
BRANCH="${BRANCH:-main}"
SITE=holycrossrajshahi.edu.bd
STAMP=$(date -u +%Y%m%d-%H%M%S)
BACKUP_DIR=/home/holycross/pg_backup
BACKUP="$BACKUP_DIR/db.sqlite3.pre-deploy-$STAMP"

as_app() { sudo -u "$APP_USER" env GIT_TERMINAL_PROMPT=0 "$@"; }

count_rows() {
  "$PY" - <<'PY'
import sqlite3
c = sqlite3.connect("/home/holycross/holycross/db.sqlite3")
for t in ["notices_notice", "news_newsitem", "people_teacher", "auth_user",
          "gallery_album", "admissions_application", "admissions_admissionclass"]:
    try:
        print(t, c.execute("select count(*) from %s" % t).fetchone()[0])
    except Exception as e:
        print(t, "MISSING")
PY
}

echo "=== PRECHECK ==="
systemctl is-active gunicorn nginx
as_app git --no-pager -C "$APP" log -1 --format='current: %h %s'
test -f "$APP/db.sqlite3"
test -d "$APP/media"
if as_app git -C "$APP" ls-files --error-unmatch db.sqlite3 .env >/dev/null 2>&1; then
  echo "REFUSING: db.sqlite3 or .env is tracked by git"
  exit 1
fi
if [ -n "$(as_app git -C "$APP" status --porcelain --untracked-files=no)" ]; then
  echo "REFUSING: the server has local code edits. Inspect with: git -C $APP status"
  exit 1
fi

echo "=== BACKUP DATABASE ==="
mkdir -p "$BACKUP_DIR"
cp -p "$APP/db.sqlite3" "$BACKUP"
chown "$APP_USER:$APP_USER" "$BACKUP"
echo "backup: $BACKUP"
BEFORE=$(count_rows)
MEDIA_BEFORE=$(find "$APP/media" -type f | wc -l)

echo "=== PULL $BRANCH ==="
as_app git --no-pager -C "$APP" fetch origin
as_app git --no-pager -C "$APP" pull --ff-only origin "$BRANCH"
as_app git --no-pager -C "$APP" log -1 --format='now: %h %s'

echo "=== INSTALL REQUIREMENTS ==="
as_app "$PIP" install -q -r "$APP/requirements.txt"

echo "=== MIGRATE ==="
cd "$APP"
as_app "$PY" manage.py migrate --noinput

echo "=== COLLECTSTATIC ==="
as_app "$PY" manage.py collectstatic --noinput -v 0

echo "=== CHECK ==="
as_app "$PY" manage.py check

echo "=== VERIFY CONTENT UNCHANGED ==="
AFTER=$(count_rows)
MEDIA_AFTER=$(find "$APP/media" -type f | wc -l)
# Migrations may add media (e.g. seeded images); only a drop means content was lost.
if [ "$BEFORE" != "$AFTER" ] || [ "$MEDIA_AFTER" -lt "$MEDIA_BEFORE" ]; then
  echo "Row or media counts changed. Not restarting. Backup: $BACKUP"
  diff <(echo "$BEFORE") <(echo "$AFTER") || true
  echo "media before $MEDIA_BEFORE after $MEDIA_AFTER"
  exit 1
fi
echo "$AFTER"
echo "media_files $MEDIA_AFTER"

echo "=== RESTART ==="
systemctl restart gunicorn
sleep 3
systemctl is-active gunicorn

echo "=== HTTP CHECKS ==="
for path in / /admission/ /notices/ /contact/; do
  curl -s -o /dev/null -w "$path %{http_code}\n" -k \
    --resolve "$SITE:443:127.0.0.1" "https://$SITE$path" || true
done
journalctl -u gunicorn --since '1 min ago' --no-pager | grep -iE 'traceback|error|critical' | tail -10 || echo "no gunicorn errors"

echo "=== DONE ==="
echo "Rollback if needed: git -C $APP reset --hard <previous-commit>, cp $BACKUP $APP/db.sqlite3, systemctl restart gunicorn"
