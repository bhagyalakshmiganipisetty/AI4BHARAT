# AI4B Bug Reporting API

Production-ready backend for an internal bug tracker, built with FastAPI, PostgreSQL, and Docker. This repo follows the AI4B Backend Engineer assignment requirements.

## Key Features
- RESTful API with JWT auth (RS256), refresh rotation, blacklist, role-based permissions middleware
- Models: User, Project, Issue (state machine), Comment with business rules
- Security: bcrypt/argon2 hashing, rate-limit + lockout on login, CSP headers, markdown sanitization, PII encryption support
- DevOps: Docker multi-stage image, docker-compose (API + Postgres + Redis + Nginx), Kubernetes manifests, healthchecks
- CI/CD: lint/type/test/coverage, security scan, build/push image (GitHub Actions)
- Tooling: Alembic migrations, seed script, structured logging, OpenAPI docs, audit logging, basic metrics endpoint
- Load testing: k6 script in `scripts/load_test.js` with runner in `scripts/load_test.py`

## Quick Start (dev)
```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
poetry install --with dev
cp .env.example .env
uvicorn app.main:app --reload
```

## Security & Sessions
- JWT RS256 with refresh rotation + blacklist; logout-all and password change invalidate existing refresh tokens.
- Login rate limiting and lockout after repeated failures.
- Inputs sanitized (bleach) and request size capped at 1MB.
- Optional PII encryption via `PII_ENCRYPTION_KEY` and hashed lookup via `PII_HASH_KEY`.

## Repository Layout
- `app/` - FastAPI application code
- `app/db/` - DB session + Alembic base
- `app/models/` - SQLAlchemy models
- `app/schemas/` - Pydantic request/response models
- `app/api/` - routers
- `app/services/` - auth, security helpers
- `infra/` - Docker, Nginx, Kubernetes
- `scripts/` - seed and utility scripts
- `tests/` - unit/integration tests (pytest)

## Architecture Notes
- Stateless API; JWT stored client-side; Redis used for token blacklist + rate limiting counters
- Permissions enforced via dependency middleware (not inline)
- Config via environment variables using `pydantic-settings`; secrets injected via env/K8s secrets
- Health endpoints: `/health/live`, `/health/ready`

## Next Steps
- Run Alembic migrations (`alembic upgrade head`)
- Set RSA keys in `.env` (or mount via secrets)
- Configure CI secrets for registry push
- Replace Nginx dev TLS certs in `infra/nginx/certs` for production
