# ra-backend

Django REST Framework API for the P10354 field assessment system.

- **Public URL:** https://api.assess.nileagi.com
- **PM2 port:** `8087`
- **Database:** SQLite (`db.sqlite3`)

## Admin login

| | |
| --- | --- |
| Username | `Angel` |
| Password | `ChangeMeNow!` |
| Role | System Administrator (`ADMIN`) |

Configured in `.env`:

```bash
BOOTSTRAP_ADMIN_USERNAME=Angel
BOOTSTRAP_ADMIN_PASSWORD=ChangeMeNow!
```

Seeded by `python manage.py seed_framework` (also run from `./start.sh` / `./deploy.sh`).

Sign in from the frontend at `/login.html` — admins are routed to `/admin.html`.

## CORS (production)

The API must allow the frontend origin. In production `.env`:

```bash
CORS_ALLOWED_ORIGINS=https://assess.nileagi.com
CSRF_TRUSTED_ORIGINS=https://assess.nileagi.com,https://api.assess.nileagi.com
ALLOWED_HOSTS=api.assess.nileagi.com,localhost,127.0.0.1
```

Then redeploy:

```bash
./deploy.sh
```

If login shows “Failed to fetch”, the reverse proxy for `api.assess.nileagi.com` must forward `OPTIONS` preflight to gunicorn (port 8087), not answer it itself without CORS headers.

## Local

```bash
./start.sh
```

## Production

```bash
cp .env.example .env   # set SECRET_KEY, DEBUG=False, CORS, etc.
./deploy.sh            # migrate, seed, gunicorn via pm2
```

## Key endpoints

| Path | Notes |
| --- | --- |
| `GET /api/health/` | Liveness |
| `POST /api/auth/login/` | JWT login |
| `GET /api/framework/` | Reference data bundle |
| `GET/PATCH /api/reports/` | School reports |
| `GET/PATCH /api/programmes/` | Programme workbooks |
| `GET/POST /api/consents/` | Consent register |
| `GET/POST /api/users/` | User list / create (admin) |
