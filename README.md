# Foodies — Cloud-Based Secure Food Ordering System

A secure, DevSecOps-style food ordering web application (Flask + PostgreSQL), built from the
capstone report's requirements and adapted to run as a serverless deployment on **Vercel** with
a managed Postgres database, instead of the report's original AWS EC2/RDS setup (see
[Relationship to the original AWS design](#relationship-to-the-original-aws-design) below for why,
and how the two map to each other).

## Features

- **Customers:** browse restaurants → view menus → add to cart → checkout → track order status
  (placed → preparing → out for delivery → delivered).
- **Restaurant Admins:** manage their menu (add / hide / delete items) and update order statuses
  from a dashboard with live stats.
- **Security (report section 3):**
  - Passwords hashed with bcrypt (`Flask-Bcrypt`), never stored or logged in plaintext.
  - JWT-based stateless sessions (`Flask-JWT-Extended`), 1-hour access tokens, stored in
    HTTP-only, SameSite=Lax cookies.
  - SQL injection prevention via SQLAlchemy ORM only — no raw/string-concatenated SQL anywhere.
  - XSS protection via Jinja2 autoescaping + a strict Content-Security-Policy header.
  - Rate limiting on login (`5/min`) and cart APIs (`30/min`) via `Flask-Limiter`; account lockout
    after 5 consecutive failed logins (15 minutes).
  - Role-based access control: `customer` vs `admin`, enforced server-side from the JWT's `role`
    claim (`app/security.py`), not just hidden in the UI.
  - Security headers on every response: `X-Frame-Options: DENY`, `X-Content-Type-Options:
    nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security`, `CSP`.

## Project layout

```
app/                Flask application package (factory in app/__init__.py)
  auth/              signup / login / logout, JWT issuance, account lockout
  customer/          restaurant browsing, cart, checkout, order tracking
  admin/             restaurant-admin dashboard, menu + order management
  templates/, static/  Jinja2 templates and CSS/JS (the "Foodies" UI)
  models.py          SQLAlchemy models (User, Restaurant, MenuItem, Cart/Order)
  security.py        RBAC decorators + security headers
api/index.py         Vercel serverless entry point (imports the Flask app)
seed.py              Sample restaurants/menu + admin & demo customer accounts
tests/               pytest suite (auth, RBAC, cart/order flow, SQLi-safety)
docker/, docker-compose.yml, nginx/, Jenkinsfile   reference on-prem/AWS deployment (see below)
```

## Running locally

```bash
python -m venv .venv
.venv/Scripts/activate        # (Windows)  |  source .venv/bin/activate (macOS/Linux)
pip install -r requirements.txt
cp .env.example .env          # edit DATABASE_URL etc. if needed; sqlite:///dev.db works out of the box
flask --app wsgi init-db      # creates tables + seeds sample data
python wsgi.py                # http://127.0.0.1:5000
```

Seeded accounts:
- Admin: `admin@foodies.com` / `ChangeMe123!` (manages "Bella Italia")
- Customer: `customer@foodies.com` / `Customer123!`

Run tests: `pytest tests/ -v` (uses an in-memory SQLite DB, no setup needed).

## Deploying to Vercel

1. **Provision a Postgres database.** Easiest: add the **Vercel Postgres** (Neon-backed)
   integration from your Vercel project's Storage tab — it injects `DATABASE_URL` (and related
   `POSTGRES_*` vars) into your project automatically. A standalone Neon project works the same
   way; copy its pooled connection string into `DATABASE_URL`.
2. **Set environment variables** in the Vercel project settings: `SECRET_KEY`, `JWT_SECRET_KEY`
   (long random values — these stand in for the report's AWS Secrets Manager secrets),
   `ADMIN_EMAIL`, `ADMIN_PASSWORD`. `DATABASE_URL` is set for you if you used the Vercel Postgres
   integration.
3. **Initialize the database** once, from your machine, pointed at the same `DATABASE_URL`:
   ```bash
   export DATABASE_URL="<the pooled connection string from Vercel/Neon>"
   flask --app wsgi init-db
   ```
4. **Deploy:**
   ```bash
   npm i -g vercel   # if you don't have the CLI
   vercel             # first deploy, links the project
   vercel --prod      # production deploy
   ```
   `vercel.json` routes every request to `api/index.py`, which exposes the Flask app as a WSGI
   handler — Vercel's Python runtime takes care of the rest.
5. Vercel serves everything over HTTPS automatically, which is what makes the `Strict-Transport-
   Security` header (and the JWT cookie's `Secure` flag) meaningful in production.

**Note on serverless constraints:** Vercel functions are stateless and short-lived, so
`Flask-Limiter`'s in-memory rate-limit counters reset between cold starts (best-effort, not a hard
guarantee) and account lockout is tracked in Postgres instead (durable, works correctly). In the
report's AWS design, both would additionally be enforced at the Nginx/WAF layer in front of a
long-running EC2 process — see `nginx/nginx.conf` for that config.

## Relationship to the original AWS design

The capstone report specifies a full AWS deployment: VPC with public/private subnets, a bastion
host, EC2 running Dockerized Flask behind Nginx, RDS MySQL, S3 + CloudFront for images, an ALB
with AWS WAF, Route 53, Jenkins CI/CD, and CloudWatch monitoring. That infrastructure requires an
AWS account, costs money to run, and is provisioned by hand or via IaC against real cloud
resources — it isn't something to spin up as a side effect of a coding session. This repo
implements the **application and its security controls** exactly as specified, and keeps the
AWS-shaped deployment artifacts as reference/documentation rather than deploying them:

| Report component | This repo |
|---|---|
| EC2 + Nginx reverse proxy | `docker/Dockerfile` + `nginx/nginx.conf` (works via `docker-compose up` for a non-serverless run) |
| RDS MySQL | Postgres (Vercel Postgres / Neon) — swapped because Vercel has no persistent MySQL/EC2 equivalent; same SQLAlchemy ORM, same security properties |
| ALB + AWS WAF + ACM/HTTPS | Vercel's edge network (automatic HTTPS, DDoS protection) |
| Jenkins CI/CD (`Jenkinsfile`) | Present as-is for a self-hosted deployment target; Vercel's own git-push deploys serve as the CI/CD path used in practice |
| S3 + CloudFront (food images) | Emoji/icon-based placeholders in `seed.py` (no binary asset storage needed for the demo) |
| CloudWatch monitoring | Vercel's built-in function logs/analytics; `docker/Dockerfile`'s `HEALTHCHECK` and the `/health` route are the same signal the report's ALB health check and CloudWatch Synthetics canary would use |

If you do want the literal AWS deployment (VPC/EC2/RDS/S3/CloudFront/WAF), follow the report's
section 4.1–4.4 step-by-step with your own AWS account — `docker/Dockerfile`, `nginx/nginx.conf`,
and `Jenkinsfile` in this repo are ready to drop into that setup unchanged.

## Architecture diagram

See `docs/architecture.png` for the original AWS multi-tier architecture diagram from the report.
