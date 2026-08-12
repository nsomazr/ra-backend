#!/usr/bin/env bash
# Assess API — production deploy with pm2 + gunicorn on :8087
# Independent service: https://api.assess.nileagi.com → 127.0.0.1:8087
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v pm2 >/dev/null 2>&1; then
  echo "Error: pm2 is not installed. Run: npm install -g pm2"
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — set SECRET_KEY before going live."
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt
python manage.py migrate --no-input
python manage.py seed_framework
python manage.py collectstatic --no-input

PORT="${BACKEND_PORT:-${PORT:-8087}}"
WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN="$(pwd)/.venv/bin/gunicorn"
PM2_NAME="${PM2_APP_NAME:-assess-backend}"

pm2 delete "$PM2_NAME" 2>/dev/null || true
pm2 start "$GUNICORN" \
  --name "$PM2_NAME" \
  --cwd "$(pwd)" \
  --update-env \
  -- config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "$WORKERS" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -

pm2 save
sleep 1
curl -sf "http://127.0.0.1:${PORT}/api/health/" >/dev/null && echo "Backend OK on :${PORT}" || echo "Warning: health check failed — see: pm2 logs ${PM2_NAME}"
pm2 status "$PM2_NAME"
echo "Public URL: https://api.assess.nileagi.com → 127.0.0.1:${PORT}"
