#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/banking_app"
REPO_URL="https://github.com/Bighnesh04/User_Management.git"
BRANCH="main"
PYTHON_BIN="/usr/bin/python3"
SERVICE_NAME="banking-app"
NGINX_SITE="banking-app"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash setup_ec2.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git nginx python3 python3-venv python3-pip

if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 1G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=1024
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR"
  git fetch origin
  git checkout "$BRANCH"
  git pull origin "$BRANCH"
fi

cd "$APP_DIR/banking_app"

if [[ ! -d .venv ]]; then
  $PYTHON_BIN -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > .env <<'EOF'
SECRET_KEY=change-this-to-a-strong-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite+aiosqlite:///./banking.db
REDIS_URL=redis://localhost:6379/0
FRONTEND_ORIGINS=http://YOUR_EC2_PUBLIC_IP,https://YOUR_DOMAIN
EOF

cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Banking App FastAPI Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=${APP_DIR}/banking_app
EnvironmentFile=${APP_DIR}/banking_app/.env
ExecStart=${APP_DIR}/banking_app/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/sites-available/${NGINX_SITE} <<'EOF'
server {
    listen 80;
    server_name _;

    root ${APP_DIR}/banking_app/frontend;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

ln -sf /etc/nginx/sites-available/${NGINX_SITE} /etc/nginx/sites-enabled/${NGINX_SITE}
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}
systemctl restart nginx

echo "Setup complete. Visit your EC2 public IP after allowing port 80 in the security group."
