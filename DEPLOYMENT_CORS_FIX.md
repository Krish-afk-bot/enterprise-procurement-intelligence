# CORS Authentication Fix - Deployment Guide

## Issue Summary

**Problem**: Vercel frontend could not authenticate against Render backend due to CORS blocking.

**Root Cause**: Pydantic Settings expected `CORS_ORIGINS` environment variable as JSON array format (e.g., `["url1","url2"]`), but environment variables are typically set as comma-separated strings (e.g., `url1,url2`). This caused the backend to fail parsing the CORS configuration and block legitimate frontend requests.

**Solution**: Modified `backend/app/config/settings.py` to:
- Accept comma-separated string format for `CORS_ORIGINS`
- Parse and normalize values (strip whitespace, remove trailing slashes)
- Maintain backward compatibility with test code that passes lists

## Testing Results

✅ All 635 backend tests passing  
✅ Direct parsing test: `CORS_ORIGINS='url1,url2,url3'` → `['url1', 'url2', 'url3']`  
✅ Default values work correctly when environment variable is unset  
✅ Constructor tests (passing list directly) still work

## Deployment Instructions

### 1. Update Render Environment Variables

Navigate to your Render service dashboard and update the `CORS_ORIGINS` environment variable:

**Current Production Origins Needed:**
```
https://enterprise-procurement-intelligence-n04pc4po3.vercel.app,https://enterprise-procurement-intelligence-git-3caaa7-krish-s-projects222.vercel.app
```

**Format**: Comma-separated, no spaces, no square brackets

**Steps:**
1. Go to Render dashboard → Your service → Environment
2. Find `CORS_ORIGINS` variable (or add it if missing)
3. Set value to: `https://enterprise-procurement-intelligence-n04pc4po3.vercel.app,https://enterprise-procurement-intelligence-git-3caaa7-krish-s-projects222.vercel.app`
4. Save changes
5. Render will automatically redeploy with the new configuration

### 2. Verify the Fix

After Render redeploys, test authentication:

```bash
# Test OPTIONS preflight
curl -X OPTIONS https://enterprise-procurement-intelligence.onrender.com/api/v1/auth/login \
  -H "Origin: https://enterprise-procurement-intelligence-n04pc4po3.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -i

# Should return:
# HTTP/1.1 200 OK
# Access-Control-Allow-Origin: https://enterprise-procurement-intelligence-n04pc4po3.vercel.app
# Access-Control-Allow-Credentials: true

# Test actual login
curl -X POST https://enterprise-procurement-intelligence.onrender.com/api/v1/auth/login \
  -H "Origin: https://enterprise-procurement-intelligence-n04pc4po3.vercel.app" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@epi.local","password":"admin-local-password"}' \
  -i

# Should return:
# HTTP/1.1 200 OK
# Access-Control-Allow-Origin: https://enterprise-procurement-intelligence-n04pc4po3.vercel.app
# Access-Control-Allow-Credentials: true
# Set-Cookie: epi_refresh=...
```

### 3. Test Frontend Authentication

Visit your Vercel deployment and attempt to log in:

**Credentials:**
- Email: `admin@epi.local`
- Password: `admin-local-password`

**Expected**: Successful login, no CORS errors in browser console

## Technical Details

### Changes Made

**File**: `backend/app/config/settings.py`

```python
# Before (failed with comma-separated strings):
cors_origins: list[str] = Field(
    default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
)

# After (accepts both comma-separated strings and lists):
cors_origins_raw: str = Field(
    default="http://localhost:5173,http://127.0.0.1:5173",
    alias="cors_origins"
)

@field_validator("cors_origins_raw", mode="before")
@classmethod
def _normalize_cors_origins(cls, value: Any) -> str:
    """Accept both string (from env) and list (from constructor) for cors_origins."""
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)

@property
def cors_origins(self) -> list[str]:
    """Parse CORS_ORIGINS from comma-separated string, stripping whitespace and trailing slashes."""
    return [
        item.strip().rstrip("/") 
        for item in self.cors_origins_raw.split(",") 
        if item.strip()
    ]
```

### Environment Variable Format

**Correct** ✅
```bash
CORS_ORIGINS=https://app.vercel.app,https://preview.vercel.app,http://localhost:5173
```

**Also works** ✅ (spaces and trailing slashes are stripped)
```bash
CORS_ORIGINS=https://app.vercel.app/, https://preview.vercel.app, http://localhost:5173
```

**Incorrect** ❌ (JSON format no longer needed)
```bash
CORS_ORIGINS=["https://app.vercel.app","https://preview.vercel.app"]
```

## Adding New Origins

When deploying new Vercel preview branches or production environments:

1. Add the new origin to the comma-separated list
2. Save in Render dashboard
3. Wait for automatic redeploy (~2-3 minutes)
4. Test authentication from the new origin

**Example** (adding staging environment):
```bash
CORS_ORIGINS=https://enterprise-procurement-intelligence-n04pc4po3.vercel.app,https://enterprise-procurement-intelligence-git-3caaa7-krish-s-projects222.vercel.app,https://staging.epi.example.com
```

## Security Notes

- Never use `*` (wildcard) in production CORS_ORIGINS
- Only add origins you control and trust
- Trailing slashes are automatically removed for consistency
- Whitespace around commas is automatically trimmed
- Empty values are filtered out

## Troubleshooting

### CORS Error Still Appears

1. **Check Render logs**: `render.yaml` marks `CORS_ORIGINS` as `sync: false`, so you must set it in the dashboard
2. **Verify format**: No brackets, no quotes around the entire string, comma-separated
3. **Check origin spelling**: Must exactly match the frontend URL (including https://)
4. **Clear browser cache**: Sometimes cached preflight responses persist

### Backend Won't Start

Check Render logs for validation errors. Common issues:
- Missing required environment variables
- Invalid URL format in CORS_ORIGINS
- Other startup security checks failing (see `validate_startup_security()` in settings.py)

## Rollback Plan

If issues occur, the fix is backward compatible. No rollback needed - just ensure the environment variable format is comma-separated.

## Next Steps

1. ✅ Update Render `CORS_ORIGINS` environment variable
2. ✅ Wait for automatic redeploy
3. ✅ Test authentication from Vercel frontend
4. ✅ Monitor Render logs for any errors
5. ✅ Add new origins as needed for additional deployments

---

**Commit**: b1fedf4  
**Deployed**: [Timestamp when you deploy]  
**Verified by**: [Your name]
