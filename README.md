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

## View-only login

| | |
| --- | --- |
| Username | `viewer` |
| Password | `ViewOnly123!` |
| Role | CBM Viewer (`CBM_VIEWER`) |

Viewers can browse dashboard/reports/framework data but **cannot** create, edit, submit, or change settings. Enforced in the API (`IsNotViewer`) and in the UI (view-only banner + disabled controls).

Configured in `.env`:

```bash
BOOTSTRAP_ADMIN_USERNAME=Angel
BOOTSTRAP_ADMIN_PASSWORD=ChangeMeNow!
BOOTSTRAP_VIEWER_USERNAME=viewer
BOOTSTRAP_VIEWER_PASSWORD=ViewOnly123!
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

## Nginx (api.assess.nileagi.com → :8087)

```nginx
server {
    listen 443 ssl http2;
    server_name api.assess.nileagi.com;

    location / {
        proxy_pass http://127.0.0.1:8087;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
    }
}
```

A browser CORS error with **no** `Access-Control-Allow-Origin` often means nginx returned **502** because gunicorn/pm2 is not running:

```bash
cd /path/to/ra-backend
./deploy.sh
pm2 status assess-backend
curl -i http://127.0.0.1:8087/api/health/
```

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
