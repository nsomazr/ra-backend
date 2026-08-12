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

## Production notes

Frontend and API are separate services:

| Host | Process | Port |
| --- | --- | --- |
| https://assess.nileagi.com | `assess-frontend` (Node) | 3087 |
| https://api.assess.nileagi.com | `assess-backend` (gunicorn) | 8087 |

CORS must allow the frontend origin:

```bash
CORS_ALLOWED_ORIGINS=https://assess.nileagi.com
CSRF_TRUSTED_ORIGINS=https://assess.nileagi.com,https://api.assess.nileagi.com
ALLOWED_HOSTS=api.assess.nileagi.com,localhost,127.0.0.1
```

If the API process is down, nginx returns 502 and the browser may show a connection error on login — start/redeploy the API:

```bash
./deploy.sh
pm2 status assess-backend
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
