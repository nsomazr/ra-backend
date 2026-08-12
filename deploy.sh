#!/usr/bin/env bash
# Assess API — production deploy with pm2 + gunicorn on :8087
# Served publicly as https://api.assess.nileagi.com (reverse proxy -> 127.0.0.1:8087).
# Production .env should set:
#   DEBUG=False
#   SECRET_KEY=<strong secret>
#   FRONTEND_URL=https://assess.nileagi.com
#   USE_SQLITE=1
#   ALLOWED_HOSTS=api.assess.nileagi.com,localhost,127.0.0.1
#   CORS_ALLOWED_ORIGINS=https://assess.nileagi.com
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v pm2 >/dev/null 2>&1; then
  echo "Error: pm2 is not installed. Run: npm install -g pm2"
  exit 1
fi

if [ ! -f .env ]; then
  echo "Error: .env not found. Copy .env.example to .env and configure production values."
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate --no-input
python manage.py seed_framework
python manage.py collectstatic --no-input

PORT="${BACKEND_PORT:-8087}"
WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN="$(pwd)/.venv/bin/gunicorn"
PM2_NAME="${PM2_APP_NAME:-assess-backend}"

pm2 delete "$PM2_NAME" 2>/dev/null || true
pm2 start "$GUNICORN" \
  --name "$PM2_NAME" \
  --cwd "$(pwd)" \
  -- config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "$WORKERS" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -

pm2 save
echo "assess-backend deployed on :${PORT} (pm2: ${PM2_NAME})"
echo "Public URL: https://api.assess.nileagi.com (point reverse proxy at 127.0.0.1:${PORT})"
pm2 status "$PM2_NAME"
