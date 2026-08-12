const fs = require('fs');
const path = require('path');

function loadEnvFile(filePath) {
  const out = {};
  if (!fs.existsSync(filePath)) return out;
  for (const line of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq < 1) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    out[key] = val;
  }
  return out;
}

const fileEnv = loadEnvFile(path.join(__dirname, '.env'));
const port = fileEnv.BACKEND_PORT || process.env.BACKEND_PORT || process.env.PORT || '8087';
const workers = fileEnv.GUNICORN_WORKERS || process.env.GUNICORN_WORKERS || '3';

module.exports = {
  apps: [
    {
      name: process.env.PM2_APP_NAME || fileEnv.PM2_APP_NAME || 'assess-backend',
      script: path.join(__dirname, '.venv/bin/gunicorn'),
      // Required: otherwise PM2 tries to run gunicorn via node → crash loop, nothing on :8087
      interpreter: 'none',
      exec_mode: 'fork',
      instances: 1,
      args: [
        'config.wsgi:application',
        '--bind', `0.0.0.0:${port}`,
        '--workers', String(workers),
        '--timeout', '120',
        '--access-logfile', '-',
        '--error-logfile', '-',
      ].join(' '),
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        ...fileEnv,
        BACKEND_PORT: String(port),
      },
    },
  ],
};
