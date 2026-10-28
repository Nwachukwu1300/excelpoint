#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 server for ExcelPoint (Oracle Cloud Always Free, or any VPS).
# Run it on the server as the default user (ubuntu):
#   curl -fsSL https://raw.githubusercontent.com/Nwachukwu1300/excelpoint/main/deploy/setup-server.sh | bash
# Safe to run again: it skips what is already done, and later runs just pull the code and restart.
set -euo pipefail

REPO=https://github.com/Nwachukwu1300/excelpoint.git
DIR="$HOME/excelpoint"

echo "== 1/4 Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

echo "== 2/4 Firewall: allow web traffic (Oracle's Ubuntu image blocks everything except SSH)"
for port in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
done
if command -v netfilter-persistent >/dev/null; then sudo netfilter-persistent save; fi

echo "== 3/4 Code"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone "$REPO" "$DIR"; fi
cd "$DIR"

echo "== 4/4 Settings (.env)"
set_env() {  # set_env KEY VALUE: replace the line, or add it
  local value=${2//&/\\&}
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=${value//|/\\|}|" .env; else echo "$1=$2" >> .env; fi
}
if [ ! -f .env ]; then
  cp .env.example .env
  # Read from the terminal even when this script is piped in through curl
  read -rp "Your web address, e.g. excelpoint.duckdns.org: " domain </dev/tty
  read -rsp "OpenAI API key (sk-...): " openai_key </dev/tty; echo
  read -rp "Gmail address that sends password-reset emails (blank to skip for now): " mail_user </dev/tty
  mail_pass=""
  if [ -n "$mail_user" ]; then read -rsp "Its 16-character Gmail app password: " mail_pass </dev/tty; echo; fi

  set_env DEBUG False
  set_env DOMAIN "$domain"
  set_env ALLOWED_HOSTS "$domain"
  set_env DJANGO_SECRET_KEY "$(openssl rand -base64 48 | tr -d '\n/+=')"
  set_env DB_NAME excelpoint
  set_env DB_USER excelpoint
  set_env DB_PASSWORD "$(openssl rand -hex 24)"
  set_env OPENAI_API_KEY "$openai_key"
  set_env GOOGLE_OAUTH_REDIRECT_URI "https://$domain/users/google/callback/"
  if [ -n "$mail_user" ]; then
    set_env EMAIL_HOST smtp.gmail.com
    set_env EMAIL_PORT 587
    set_env EMAIL_HOST_USER "$mail_user"
    set_env EMAIL_HOST_PASSWORD "${mail_pass// /}"
  fi
  chmod 600 .env
  echo ".env written (secret key and database password were generated)."
else
  echo ".env already exists: left as it is."
fi

echo "== Starting ExcelPoint (the first build takes about 10 minutes)"
# sg: the docker group from step 1 isn't active in this shell until you log in again
sg docker -c "docker compose up -d --build"

domain=$(grep '^DOMAIN=' .env | cut -d= -f2)
echo
echo "Done. Open https://$domain in a minute or two (Caddy is getting the HTTPS certificate)."
echo "Logs: cd $DIR && docker compose logs -f web worker caddy"
