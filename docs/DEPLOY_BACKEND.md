# DocFlow Backend Early Deployment Guide

This guide walks you through deploying the DocFlow backend on [Render](https://render.com) using [Neon](https://neon.tech) for PostgreSQL and [Upstash](https://upstash.com) (or Render Redis) for Redis.

The early deployment goal is to get:
- Public API URL live
- Health check working (`GET /api/v1/health`)
- Auth working (User registration, login, and `/api/v1/auth/me`)
- Database migrations applied
- Celery worker service configured

> **Zero-Secrets Policy**: You will generate and paste all credentials directly into your respective dashboards. Never commit secret values or share them in chat.

---

## Architecture Overview

```
                        ┌──────────────────────────────────────────────┐
                        │              Render Platform                 │
                        │                                              │
  Public Web Traffic    │   ┌──────────────────────────────────────┐   │
───────────────────────►│   │  Web Service (docflow-api)           │   │
                        │   │  - Port: $PORT (e.g. 10000)          │   │
                        │   │  - Alembic migrations on boot        │   │
                        │   │  - FastAPI (Uvicorn)                 │   │
                        │   └──────────────────┬───────────────────┘   │
                        │                      │                       │
                        │   ┌──────────────────┴───────────────────┐   │
                        │   │  Worker Service (docflow-worker)     │   │
                        │   │  - Celery Worker (same image)        │   │
                        │   └──────────────────┬───────────────────┘   │
                        └──────────────────────┼───────────────────────┘
                                               │
                        ┌──────────────────────┴───────────────────────┐
                        │                                              │
                        ▼                                              ▼
          ┌───────────────────────────┐                  ┌───────────────────────────┐
          │      Neon PostgreSQL      │                  │   Redis (Upstash/Render)  │
          │   (Serverless Postgres)   │                  │     (TLS / rediss://)     │
          │  sslmode=require enabled  │                  │  ssl_cert_reqs supported  │
          └───────────────────────────┘                  └───────────────────────────┘
```

---

## Step 1: Create Neon Database & Copy Connection String

1. Sign in or sign up at **[console.neon.tech](https://console.neon.tech)**.
2. Click **Create Project**:
   - **Project name**: `docflow` (or any name you prefer).
   - **Postgres version**: `15` or `16` (default recommended).
   - **Region**: Choose the region closest to your Render service region (e.g., `US East (Ohio)` if using Render `Oregon` / `Ohio`).
3. Once created, go to the **Dashboard** of your project.
4. Locate the **Connection Details** widget:
   - Select the database (e.g., `neondb` or `docflow`).
   - Choose **Direct Connection** (or **Pooled Connection**).
   - Ensure the connection string includes `sslmode=require`.
5. Copy the connection string. It will look like:
   ```text
   postgresql://alex:AbCdEf123456@ep-cool-pond-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(Note: The DocFlow backend automatically handles both `postgresql://` and `postgres://` prefixes and maps them to SQLAlchemy's psycopg2 driver).*

---

## Step 2: Create Redis Instance (Upstash or Render Redis)

You can choose either Upstash (serverless free tier with TLS) or Render Redis.

### Option A: Upstash Redis (Recommended for Free Tier)
1. Sign in or sign up at **[console.upstash.com](https://console.upstash.com)**.
2. Click **Create Database**:
   - **Name**: `docflow-redis`.
   - **Type**: Regional.
   - **Region**: Select a region close to your Neon and Render services.
   - **TLS**: Enabled (default).
3. In the database details page, find the **Connect to your database** section.
4. Select the **redis-cli** or **Python** tab and copy the `rediss://` URL:
   ```text
   rediss://default:your_upstash_password@your-endpoint.upstash.io:6379
   ```
   *(Note: The extra `s` in `rediss://` enables TLS. DocFlow's Celery configuration automatically enables SSL verification).*

### Option B: Render Managed Redis
1. In your **Render Dashboard**, click **New +** > **Redis**.
2. Name it `docflow-redis`.
3. Choose the same region as your Render Web Service.
4. Copy the **Internal Redis URL** (for services within the same Render account/region) or **External Redis URL** (`rediss://...`).

---

## Step 3: Create Render Services from `render.yaml` Blueprint

1. Push the reviewed deployment configuration to the `dev` branch, then create or update the Render Blueprint from that branch. Promote it to `main` only after the integrated stack passes verification.
2. Log in to **[dashboard.render.com](https://dashboard.render.com)**.
3. Click **New +** in the top navigation bar and select **Blueprint**.
4. Connect your Git repository (`DocFlow`).
5. Render will detect `render.yaml` and parse two services:
   - **`docflow-api`**: Web Service (Docker, Plan: Free).
   - **`docflow-worker`**: Background Worker (Docker, Plan: Starter).
   *(Note: On Render, background workers require a Starter plan ($7/mo). If you only want to test the API for free right now, you can temporarily suspend or delete the worker service in the Render dashboard until background processing is needed).*
6. Click **Apply**. Render will begin configuring the blueprint.

---

## Step 4: Configure Environment Variables in Render Dashboard

Because all sensitive environment variables are specified with `sync: false` in `render.yaml`, Render prompts you to enter their values.

In the Render Dashboard, go to your service (`docflow-api` and `docflow-worker`) > **Environment** tab:

| Variable | Recommended / Required Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Environment mode |
| `PORT` | `10000` | Port automatically assigned by Render for Web Services |
| `SECRET_KEY` | *(Generate a 64-char random hex)* | Used for JWT signing. Generate via: `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT expiration (24 hours) |
| `CORS_ORIGINS` | `*` or `https://your-frontend.vercel.app` | Allowed CORS origins (comma-separated) |
| `DATABASE_URL` | *(Pasted from Step 1)* | Neon connection string with `?sslmode=require` |
| `REDIS_URL` | *(Pasted from Step 2)* | Upstash or Render Redis URL (`rediss://...`) |
| `USE_STUB_EXTRACTOR` | `true` | Uses built-in rule stub extractor for early deployment |
| `ANTHROPIC_API_KEY` | *(Optional for early deploy)* | Leave blank or provide key if running LLM extraction |
| `S3_ENDPOINT_URL` | *(Optional for early deploy)* | Cloudflare R2 / S3 endpoint (configured in storage phase) |
| `S3_REGION` | `auto` | Storage region |
| `S3_ACCESS_KEY` | *(Optional for early deploy)* | Storage access key |
| `S3_SECRET_KEY` | *(Optional for early deploy)* | Storage secret key |
| `S3_BUCKET` | `docflow-documents` | Bucket name |
| `PRESIGNED_URL_EXPIRES_SECONDS` | `300` | Presigned URL expiration |
| `LLM_MODEL` | `claude-sonnet-5-5` | Model identifier |
| `CONFIDENCE_THRESHOLD` | `0.85` | Confidence score cutoff |
| `JOB_MAX_ATTEMPTS` | `3` | Worker retry limit |
| `FORCE_FAIL_FILENAME_CONTAINS` | `failme` | Demo failure trigger |
| `FORCE_FAIL_UNTIL_ATTEMPT` | `0` | Fail the matching stub document for the first N attempts; `0` keeps failing every attempt |

Click **Save Changes**. Render will automatically trigger a deployment.

### Startup Environment Variable Check
When the container boots, check the **Logs** tab in Render. The backend prints a dedicated startup line detailing missing variables (names only, never values):
```text
[STARTUP] Missing environment variables: ANTHROPIC_API_KEY, S3_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT_URL, S3_SECRET_KEY
```
For early deployment (auth + health), missing storage/AI keys are expected and safe.

---

## Step 5: Run Database Seed Script (Once)

The seed script creates the initial demo account:
- **Email**: `demo@docflow.app`
- **Password**: `Demo@1234`

You can run the seed script using any of the following methods:

### Method A: Via Render One-Off Shell (Recommended)
1. In the Render Dashboard, navigate to `docflow-api`.
2. Click the **Shell** tab on the left menu.
3. Click **Connect**.
4. In the shell prompt, execute:
   ```bash
   python scripts/seed.py
   ```
   Expected output:
   ```text
   Seeded demo user: demo@docflow.app
   ```
*(The seed script is idempotent; running it multiple times is completely safe).*

### Method B: From Local Machine against Neon
From your local terminal with python installed:
```bash
DATABASE_URL="<your-neon-database-url>" python backend/scripts/seed.py
```

---

## Step 6: Verify Health and Authentication Endpoints

Substitute `https://your-api.onrender.com` with your actual Render service URL.

### 1. Verify Health Check
```bash
curl -i https://your-api.onrender.com/api/v1/health
```
**Expected Response:**
```http
HTTP/2 200
content-type: application/json

{"status":"ok"}
```

### 2. Verify Demo User Login
```bash
curl -i -X POST https://your-api.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@docflow.app","password":"Demo@1234"}'
```
**Expected Response:**
```http
HTTP/2 200
content-type: application/json

{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "...",
    "email": "demo@docflow.app",
    "full_name": "Demo User"
  }
}
```

### 3. Verify User Registration
```bash
curl -i -X POST https://your-api.onrender.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com","password":"SecurePassword123","full_name":"Test User"}'
```
**Expected Response:**
```http
HTTP/2 201
content-type: application/json

{
  "id": "...",
  "email": "testuser@example.com",
  "full_name": "Test User"
}
```

### 4. Verify Authenticated `/api/v1/auth/me`
Export the token received from login:
```bash
TOKEN="<paste-access-token-here>"

curl -i https://your-api.onrender.com/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```
**Expected Response:**
```http
HTTP/2 200
content-type: application/json

{
  "id": "...",
  "email": "demo@docflow.app",
  "full_name": "Demo User"
}
```

---

## Step 7: Free-Tier Cold Starts & Warm-Up Procedure

### Understanding Free-Tier Behavior
- **Render Free Web Services**: If no HTTP traffic is received for **15 minutes**, Render spins down the container instance to conserve resources.
- **Neon Serverless Postgres**: Neon compute endpoints scale to zero when idle.
- **Cold Start Latency**: When a new request arrives after inactivity:
  - Render takes **30–50 seconds** to boot the container.
  - Neon takes **1–2 seconds** to resume the compute endpoint.
  - The first request may experience a noticeable delay before responding.

### Warm-Up Steps
1. **Before Demos / Testing**:
   Send a simple warmup ping 60 seconds before showing the application:
   ```bash
   curl -s https://your-api.onrender.com/api/v1/health > /dev/null
   ```
2. **Automated Ping (Optional)**:
   You can set up a free uptime monitor (e.g., [UptimeRobot](https://uptimerobot.com) or [Cron-Job.org](https://cron-job.org)) to ping `https://your-api.onrender.com/api/v1/health` every **10 minutes**. This prevents the instance from sleeping during active testing periods.

---

## Troubleshooting & Diagnostics

- **Database Connection Error**:
  - Confirm your Neon URL ends with `?sslmode=require`.
  - In Neon Dashboard, verify the project status is **Active** (not paused or deleted).
- **Celery / Redis Connection Issues**:
  - Ensure Upstash connection string begins with `rediss://` (with two 's' characters).
  - Verify IP access restrictions on Upstash are set to allow all IPs (`0.0.0.0/0`).
- **Container Build Issues**:
  - Check the **Build Logs** in the Render dashboard.
  - Ensure `dockerContext: ./backend` and `dockerfilePath: ./backend/Dockerfile` match repository structure.
