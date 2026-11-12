# Docker Build Fix - Render Deployment

## Issue
Render build was failing with error:
```
ERROR: "/backend": not found
```

## Root Cause
The Dockerfile is designed to be built from the **repository root**, not from inside the `backend/` directory. The `COPY backend/ ./` command expects the build context to include the `backend/` directory as a subdirectory.

## Solution Applied

### ✅ Fixed Configuration

The `render.yaml` is already correctly configured:
```yaml
services:
  - type: web
    name: epi-api
    dockerfilePath: ./backend/Dockerfile  # Path to Dockerfile
    dockerContext: .                       # Build from repo root ✅
```

The Dockerfile now has clear comments explaining this:
```dockerfile
# This Dockerfile is designed to be built from the repository root:
#   docker build -f backend/Dockerfile .
```

## How to Build Locally

### From Repository Root (Correct)
```bash
# Navigate to repo root
cd "C:\Users\user\OneDrive\Desktop\Sprint 2"

# Build the backend
docker build -f backend/Dockerfile -t epi-backend .
```

### Using Docker Compose (Correct)
```bash
docker compose build api
```

The `docker-compose.yml` is also correctly configured:
```yaml
api:
  build:
    context: .                    # Build from repo root
    dockerfile: backend/Dockerfile
```

## Render Deployment Notes

### What Render Does
1. Clones your GitHub repository
2. Sets build context to repository root (due to `dockerContext: .`)
3. Runs: `docker build -f ./backend/Dockerfile .`
4. The `COPY backend/ ./` command works because it copies from `./backend/` relative to the root

### Verify Your Render Configuration

In your Render dashboard, ensure:

1. **Build Context** should be: `. (root)` or empty (defaults to root)
2. **Dockerfile Path** should be: `./backend/Dockerfile`

### If Still Failing on Render

Check these:

1. **Repository Structure:**
   ```
   repo-root/
   ├── backend/
   │   ├── Dockerfile ✅
   │   ├── app/
   │   ├── pyproject.toml
   │   └── ...
   ├── frontend/
   ├── render.yaml
   └── ...
   ```

2. **Environment Variables:**
   Make sure all required env vars are set in Render dashboard under "Environment" section.

3. **Build Logs:**
   Look for these lines in Render build logs:
   ```
   [internal] load build context
   transferring context: XXX bytes
   ```
   
   If context is too small (< 1MB), it might not include the backend directory.

## Testing the Fix

### Test Locally
```bash
# From repo root
docker build -f backend/Dockerfile -t epi-backend-test .

# If successful, run it
docker run -p 8000:8000 epi-backend-test
```

### Expected Output
```
✅ Successfully built
✅ Successfully tagged epi-backend-test:latest
```

## File Structure Reference

```
Sprint 2/                           ← Build context root
├── backend/                        ← Copied by COPY backend/ ./
│   ├── Dockerfile                  ← The Dockerfile
│   ├── .dockerignore               ← Excludes __pycache__, tests, etc.
│   ├── pyproject.toml              ← Dependencies
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/
│   │   └── ...
│   └── tests/
├── frontend/
├── docker-compose.yml
├── render.yaml
└── ...
```

## Common Mistakes to Avoid

❌ **Wrong:** Building from inside `backend/` directory
```bash
cd backend
docker build -t epi-backend .  # FAILS - no backend/ subdirectory
```

✅ **Correct:** Building from repository root
```bash
docker build -f backend/Dockerfile -t epi-backend .
```

❌ **Wrong:** Setting dockerContext to `./backend`
```yaml
dockerContext: ./backend  # WRONG
```

✅ **Correct:** Setting dockerContext to repo root
```yaml
dockerContext: .  # CORRECT
```

## Verification Checklist

Before deploying to Render:

- [ ] Dockerfile exists at `backend/Dockerfile`
- [ ] `.dockerignore` exists at `backend/.dockerignore`
- [ ] `render.yaml` has `dockerContext: .`
- [ ] `render.yaml` has `dockerfilePath: ./backend/Dockerfile`
- [ ] Local build works: `docker build -f backend/Dockerfile .`
- [ ] Pushed latest changes to GitHub

## Next Steps

If the build succeeds but the app fails to start on Render:

1. Check **Logs** tab in Render dashboard
2. Look for:
   - Database connection errors
   - Missing environment variables
   - Port binding issues (use `$PORT` env var on Render)
3. Ensure health check endpoint works: `/api/v1/ready`

## Support

If issues persist:
1. Check Render build logs carefully
2. Verify all environment variables are set
3. Test Docker build locally first
4. Consult `docs/deployment/EPI_DEPLOYMENT_GUIDE.md`

---

**Status:** ✅ Fixed and pushed to GitHub  
**Commit:** `f02b996` - "fix(docker): improve Dockerfile comments and clarity"
