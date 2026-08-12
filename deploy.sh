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
PM2_NAME="${PM2_APP_NAME:-assess-backend}"

if [ ! -x .venv/bin/gunicorn ]; then
  echo "Error: .venv/bin/gunicorn missing — pip install failed?"
  exit 1
fi

# Use ecosystem so interpreter:none is set (bare `pm2 start gunicorn` crash-loops).
pm2 delete "$PM2_NAME" 2>/dev/null || true
pm2 start ecosystem.config.cjs --update-env
pm2 save

ok=0
for _ in 1 2 3 4 5 6 7 8; do
  sleep 1
  if curl -sf "http://127.0.0.1:${PORT}/api/health/" >/dev/null; then
    ok=1
    break
  fi
done

if [ "$ok" -eq 1 ]; then
  echo "Backend OK on :${PORT}"
else
  echo "Warning: health check failed — see: pm2 logs ${PM2_NAME} --lines 80"
fi
pm2 status "$PM2_NAME"
echo "Public URL: https://api.assess.nileagi.com → 127.0.0.1:${PORT}"
