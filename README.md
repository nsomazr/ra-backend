# ra-backend

Django REST Framework API for the P10354 field assessment system.

- **Public URL:** https://api.assess.nileagi.com
- **PM2 port:** `8087`
- **Database:** SQLite (`db.sqlite3`)

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

Bootstrap admin username defaults to `Angel` (see `.env`).
