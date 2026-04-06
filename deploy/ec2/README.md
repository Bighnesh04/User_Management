# AWS EC2 t3.micro Deployment

This repo is designed to run on a lightweight EC2 instance using:

- `nginx` for the public web server
- `uvicorn` for the FastAPI backend
- SQLite for the first deployment pass
- static frontend served from the same origin as the backend proxy (`/api`)

## Recommended EC2 settings

- Instance type: `t3.micro`
- OS: Ubuntu 22.04 LTS
- Storage: 20 GB gp3 or higher
- Security group inbound:
  - `22` from your IP
  - `80` from `0.0.0.0/0`
  - `443` from `0.0.0.0/0` if you later add TLS

## One-time setup

SSH into the instance and run:

```bash
sudo bash /path/to/setup_ec2.sh
```

Or perform the steps manually:

```bash
sudo apt-get update
sudo apt-get install -y git nginx python3 python3-venv python3-pip
sudo git clone -b main https://github.com/Bighnesh04/User_Management.git /opt/banking_app
cd /opt/banking_app/banking_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```bash
cat > /opt/banking_app/banking_app/.env <<'EOF'
SECRET_KEY=change-this-to-a-strong-secret
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite+aiosqlite:///./banking.db
REDIS_URL=redis://localhost:6379/0
FRONTEND_ORIGINS=http://YOUR_EC2_PUBLIC_IP
EOF
```

Copy the systemd service and nginx config:

```bash
sudo cp /opt/banking_app/deploy/ec2/banking-app.service /etc/systemd/system/banking-app.service
sudo cp /opt/banking_app/deploy/ec2/nginx-banking-app.conf /etc/nginx/sites-available/banking-app
sudo ln -sf /etc/nginx/sites-available/banking-app /etc/nginx/sites-enabled/banking-app
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable banking-app
sudo systemctl restart banking-app
sudo systemctl restart nginx
```

## Seed demo data

After the app is running:

```bash
cd /opt/banking_app/banking_app
source .venv/bin/activate
python3 scripts/seed_data.py --customers 20 --seed 42
```

## Access

Open the EC2 public IP in your browser. The frontend will use `/api` automatically through nginx.

## Notes for `t3.micro`

- Keep SQLite for the first version; move to Postgres later if traffic grows.
- Swap is enabled in `setup_ec2.sh` to reduce out-of-memory issues.
- Avoid running extra services unless needed.
