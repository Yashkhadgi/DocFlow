# DocFlow

DocFlow is a V1 invoice processing and automation SaaS prototype.

See [V1_BUILD_PLAN.md](./V1_BUILD_PLAN.md) for the frozen build plan, roles, contracts, and task checklist.

Person C owns the final README content for C7.

## A1/A2 Local Verification

Start the backend stack:

```bash
docker compose up --build
```

The API container runs migrations automatically before Uvicorn starts:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Check health:

```bash
curl http://localhost:8000/api/v1/health
```

Show migrated tables and indexes:

```bash
docker compose exec db psql -U docflow -d docflow -c '\dt'
docker compose exec db psql -U docflow -d docflow -c '\di'
docker compose exec db psql -U docflow -d docflow -c "\d+ documents"
```

Run tests:

```bash
docker compose exec api pytest
```

Seed demo user:

```bash
docker compose exec api python scripts/seed.py
```

Register, login, and call the protected route:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"asha@example.test","password":"Password123","full_name":"Asha"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"asha@example.test","password":"Password123"}' \
  | python -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```
