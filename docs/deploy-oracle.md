# Deploying ExcelPoint for free (Oracle Cloud + DuckDNS + Gmail)

This runs the whole app (web, worker, database, Redis, HTTPS, nightly backups) on one free server.
It takes about 45 minutes the first time, most of it waiting.

What you need: a card for Oracle's identity check (Always Free resources are not charged), a Gmail account,
and an OpenAI API key.

## 1. A Gmail app password (for password-reset emails)

1. Turn on 2-Step Verification for the Gmail account: https://myaccount.google.com/security
2. Create an app password: https://myaccount.google.com/apppasswords (name it "ExcelPoint").
3. Keep the 16-character password for step 6. Never put your normal Gmail password anywhere.

Gmail sends about 500 emails a day, which is plenty for a beta. When you buy a domain, switch to Resend (see the end).

## 2. An Oracle Cloud account

1. Sign up at https://signup.cloud.oracle.com.
2. Pick a **home region** close to your users (for the UK: "UK South (London)"). It can't be changed later.
3. After sign-up, consider **Upgrade to Pay As You Go** (Billing). It stays free while you only use Always Free
   resources, and stops Oracle reclaiming the server when it is mostly idle, which a small beta might be.
   Set a budget alert of £1 so you hear about any charge.

## 3. The server

Compute → Instances → **Create instance**:

| Setting | Value |
|---|---|
| Image | Canonical **Ubuntu 24.04** |
| Shape | Ampere → **VM.Standard.A1.Flex**, **2 OCPUs, 12 GB memory** (the Always Free allowance) |
| Networking | default (create a new VCN with a public subnet), "Assign a public IPv4 address" on |
| SSH keys | "Generate a key pair" and **download the private key** (you can't get it again) |
| Boot volume | default (about 50 GB; up to 200 GB is free) |

If it says "Out of capacity", try another availability domain, or again in a few hours.

When it is running, note its **public IP address**.

## 4. Open the web ports

Networking → Virtual cloud networks → your VCN → Security → the default security list → **Add ingress rules**:

- Source `0.0.0.0/0`, TCP, destination port **80**
- Source `0.0.0.0/0`, TCP, destination port **443**

(The setup script opens the same ports in the server's own firewall.)

## 5. A free web address (DuckDNS)

1. Sign in at https://www.duckdns.org.
2. Add a subdomain, for example `excelpoint`, giving `excelpoint.duckdns.org`.
3. Set its IP to the server's public IP and click "update ip".

## 6. Install ExcelPoint

From your computer (use the key you downloaded):

```bash
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<server IP>
```

On the server:

```bash
curl -fsSL https://raw.githubusercontent.com/Nwachukwu1300/excelpoint/main/deploy/setup-server.sh | bash
```

It asks for your DuckDNS address, the OpenAI key, and the Gmail address and app password. It generates the
secret key and database password itself, writes `~/excelpoint/.env`, and starts everything. The first build
takes about 10 minutes.

Then open `https://<your address>`. Caddy gets the HTTPS certificate on the first visit (allow a minute).

To make an admin account for `/admin/`:

```bash
cd ~/excelpoint && docker compose exec web python manage.py createsuperuser
```

Once HTTPS works, set `SECURE_HSTS_SECONDS=31536000` in `.env` and run `docker compose up -d`.

## Everyday tasks

| Task | Command (in `~/excelpoint`) |
|---|---|
| Update to the latest code | `git pull && docker compose up -d --build` |
| See logs | `docker compose logs -f web worker caddy` |
| Restart | `docker compose restart` |
| List backups | `docker compose exec backup ls -lh /backups` |
| Copy backups to your computer | on the server `docker compose cp backup:/backups ./backups`, then on your computer `scp -i <key> -r ubuntu@<IP>:excelpoint/backups .` |

**Backups:** the database is dumped every night and the last 7 dumps are kept on the server. Uploaded files
(the `media` volume) are not in them. Copy both off the server now and then: a server failure takes the
backups with it.

**Restoring a backup** (replaces the current data):

```bash
docker compose stop web worker beat
docker compose exec backup sh -c 'pg_restore --clean --if-exists -d "$PGDATABASE" /backups/excelpoint-YYYY-MM-DD.dump'
docker compose start web worker beat
```

## Later: your own domain and Resend

1. Buy a domain (about £10 a year) and point an A record at the server.
2. In `.env`, set `DOMAIN` and `ALLOWED_HOSTS` to it, and `GOOGLE_OAUTH_REDIRECT_URI` if you use Google sign-in.
3. Add the domain in Resend, add the DNS records it shows, then in `.env`:
   `EMAIL_HOST=smtp.resend.com`, `EMAIL_PORT=587`, `EMAIL_HOST_USER=resend`, `EMAIL_HOST_PASSWORD=<API key>`,
   `DEFAULT_FROM_EMAIL=ExcelPoint <noreply@yourdomain>`.
4. `docker compose up -d`.
