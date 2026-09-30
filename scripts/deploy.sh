#!/bin/bash
# Deploy the website to the production VPS from your Mac.
#
#   ./scripts/deploy.sh                    push main to GitHub, then deploy it on the VPS
#   ./scripts/deploy.sh --no-push          deploy what is already on GitHub
#   ./scripts/deploy.sh set-env KEY=VALUE  add or update a variable in the VPS .env, then restart
#   ./scripts/deploy.sh show-env           list variable names in the VPS .env (values hidden)
#   ./scripts/deploy.sh payment-check      check live JanataPay from the VPS and install payment cron jobs
#
# SSH asks for the VPS root password unless you have set up an SSH key.
# Override the server with: DEPLOY_HOST=user@host ./scripts/deploy.sh
set -euo pipefail

HOST="${DEPLOY_HOST:-root@187.124.66.192}"
BRANCH=main
REMOTE_ENV=/home/holycross/holycross/.env
cd "$(dirname "$0")/.."

remote() { ssh -o StrictHostKeyChecking=accept-new "$HOST" "$@"; }

case "${1:-}" in
  set-env)
    shift
    [ $# -ge 1 ] || { echo "Usage: $0 set-env KEY=VALUE [KEY=VALUE ...]"; exit 1; }
    for pair in "$@"; do
      [[ "$pair" == *=* ]] || { echo "Not KEY=VALUE: $pair"; exit 1; }
    done
    # Pairs travel over stdin so values never appear in the remote process list.
    printf '%s\n' "$@" | remote "set -e
      touch $REMOTE_ENV
      while IFS= read -r pair; do
        key=\${pair%%=*}
        grep -v \"^\${key}=\" $REMOTE_ENV > $REMOTE_ENV.tmp || true
        printf '%s\n' \"\$pair\" >> $REMOTE_ENV.tmp
        mv $REMOTE_ENV.tmp $REMOTE_ENV
        echo \"set \$key\"
      done
      chown holycross:holycross $REMOTE_ENV
      chmod 600 $REMOTE_ENV
      systemctl restart gunicorn && systemctl is-active gunicorn"
    exit 0
    ;;
  show-env)
    remote "sed -E 's/=.*/=<hidden>/' $REMOTE_ENV"
    exit 0
    ;;
  payment-check)
    remote "bash -s" < scripts/remote_payment_check.sh
    exit 0
    ;;
  --no-push|"")
    ;;
  *)
    sed -n '2,12p' "$0"; exit 1
    ;;
esac

if git ls-files --error-unmatch .env db.sqlite3 >/dev/null 2>&1; then
  echo "REFUSING: .env or db.sqlite3 is tracked by git. Remove it with: git rm --cached .env"
  exit 1
fi

if [ "${1:-}" != "--no-push" ]; then
  current=$(git branch --show-current)
  [ "$current" = "$BRANCH" ] || { echo "Switch to $BRANCH first (on $current)."; exit 1; }
  if [ -n "$(git status --porcelain)" ]; then
    echo "You have uncommitted changes. Commit them first:"
    git status --short
    exit 1
  fi
  echo "=== Running tests ==="
  if [ -x venv/bin/python ]; then venv/bin/python manage.py test -v 0; fi
  echo "=== Pushing $BRANCH to GitHub ==="
  git push origin "$BRANCH"
fi

echo "=== Deploying on $HOST ==="
remote "BRANCH=$BRANCH bash -s" < scripts/remote_deploy.sh
