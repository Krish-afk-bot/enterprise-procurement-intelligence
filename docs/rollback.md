# Rollback and Recovery

This document describes rollback and recovery procedures for the Enterprise Procurement Intelligence platform.

---

## Local Development Rollback

### Revert to a previous commit (working tree only)

```bash
# View recent commits
git log --oneline -10

# Restore the working tree to a specific commit without changing the branch
git checkout <sha> -- <file>

# Or create a new revert commit (safe, non-destructive)
git revert <sha>
```

### Reset the local branch (destructive — local only)

```bash
# Soft reset: moves HEAD back, keeps changes staged
git reset --soft <sha>

# Hard reset: discards all changes since <sha>
git reset --hard <sha>
```

Do not hard-reset commits that have already been pushed without coordinating with other contributors.

---

## Database Rollback

### Local SQLite

The local database (`backend/var/epi.db`) is not in version control. To reset it:

```bash
# Delete the local database and all indexed state
rm -rf backend/var/epi.db backend/var/vector_index/ backend/var/graph.db

# On next startup with AUTO_CREATE_SCHEMA=true, a fresh schema is created
uvicorn app.main:app --reload --port 8000
```

Re-ingest the synthetic corpus afterwards if needed:

```bash
cd backend
epi ingest --dir ../data/synthetic
```

### PostgreSQL (Alembic)

```bash
# Roll back the last migration
alembic downgrade -1

# Roll back to base (empty schema)
alembic downgrade base

# Roll forward to latest
alembic upgrade head
```

Always take a database snapshot before running `alembic downgrade` in any environment that contains real data.

---

## Docker Compose Rollback

### Stop all services

```bash
docker compose down
```

### Stop all services and remove volumes (destroys all data)

```bash
docker compose down -v
```

### Roll back to a specific image version

```bash
# Edit the image tag in docker-compose.yml, then
docker compose pull
docker compose up -d
```

---

## Application Rollback

> Note: Docker deployment is not yet verified (`backend/Dockerfile` is missing). These steps apply once the Docker build is working.

### Rollback procedure

1. Identify the last known good SHA from `git log` or the GitHub Releases page.
2. Pull the previously built image for that SHA from the container registry.
3. Update the running containers:

```bash
docker compose up -d --no-build api
```

4. Verify the health endpoint:

```bash
curl http://localhost:8000/api/v1/health
```

5. If unhealthy, check logs:

```bash
docker compose logs api --tail=100
```

---

## CI/CD Rollback (PLANNED)

Once the deployment workflows are active:

- Staging: re-run the `Deploy — Staging` workflow against the last known good SHA via `workflow_dispatch`.
- Production: re-run the `Deploy — Production` workflow against the last known good SHA. Requires manual confirmation.

Both deployment workflows require an explicit SHA input, which makes rollback explicit and auditable.

---

## Incident Response Quick Reference

| Situation | First action |
|---|---|
| Backend returning 500s | Check `docker compose logs api` or uvicorn stdout |
| Database migration failed | Run `alembic downgrade -1`, investigate, fix, re-apply |
| Secret accidentally committed | Rotate the secret immediately, then contact GitHub support to purge from history |
| Broken dependency introduced | `pip install <package>==<last-known-good-version>` or revert the `pyproject.toml` change |
| Frontend build broken | Run `npm run typecheck` and `npm run build` locally to reproduce |
| Production outage | Roll back to last good Docker image, open an incident issue, notify stakeholders |

---

## Backup Branches

When performing destructive operations such as author rewrites or rebases, a backup branch is created first:

```bash
git branch backup-<description>
```

Backup branches are preserved in the local repository and optionally pushed to GitHub for safety. They are not deleted until the rewritten history has been successfully verified and pushed.

Current backup branches:

| Branch | Purpose | Safe to delete? |
|---|---|---|
| `backup-before-author-rewrite` | Pre-rewrite history (old EPI Engineering author) | Yes, after verifying GitHub shows correct author |
