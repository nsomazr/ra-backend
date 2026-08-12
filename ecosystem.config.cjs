const path = require('path');

const port = process.env.BACKEND_PORT || process.env.PORT || 8087;
const workers = process.env.GUNICORN_WORKERS || 3;

module.exports = {
  apps: [
    {
      name: process.env.PM2_APP_NAME || 'assess-backend',
      script: path.join(__dirname, '.venv/bin/gunicorn'),
      args: `config.wsgi:application --bind 0.0.0.0:${port} --workers ${workers} --timeout 120 --access-logfile - --error-logfile -`,
      cwd: __dirname,
      interpreter: 'none',
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env_production: {
        NODE_ENV: 'production',
      },
    },
  ],
};
