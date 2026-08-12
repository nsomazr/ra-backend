#!/usr/bin/env bash
# Assess API — local development server on :8087
# Public URL (production): https://api.assess.nileagi.com
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -c "import django" 2>/dev/null || pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit secrets before production use."
fi

PORT="${BACKEND_PORT:-8087}"
python manage.py migrate --no-input
python manage.py seed_framework
exec python manage.py runserver "0.0.0.0:${PORT}"
