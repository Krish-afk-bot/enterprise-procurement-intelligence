# Vercel configuration

The frontend is a Vite + React SPA in `frontend/`. Build output is `dist/`.
`frontend/vercel.json` pins the build and adds SPA routing and security headers.

## 1. Build settings

| Setting | Value |
| --- | --- |
| Framework preset | Vite |
| Root directory | `frontend` |
| Install command | `npm ci` |
| Build command | `npm run build` (`tsc -b && vite build`) |
| Output directory | `dist` |
| Node version | 22 LTS |

`npm run build` was verified in this repository. The build fails on a TypeScript
error, which is intended: a type error should stop a deploy.

`vercel.json` rewrites every unknown path to `/index.html` so client-side routes
(`/dashboard`, `/documents/:id`, …) survive a refresh. Hashed assets under
`/assets/*` are cached immutably; everything else gets `nosniff`,
`X-Frame-Options: DENY`, a referrer policy and a restrictive permissions policy.

## 2. Environment variables per environment

Only `VITE_*` variables reach the browser bundle. They are public by
definition — never put a secret behind that prefix.

| Variable | Production | Preview | Development (local) |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | `https://api.example.com` | `https://api-staging.example.com` | unset (Vite proxies `/api` to `http://localhost:8000`) |
| `VITE_ENABLE_WORLD` | `false` | `false` | `false` |

If a preview deploy should not touch staging data, point its
`VITE_API_BASE_URL` at a preview API with its own database and bucket, or leave
the preview without a backend and accept that sign-in fails there.

Set these in Vercel → Project → Settings → Environment Variables, scoped to
Production / Preview / Development. They can also be declared in
`vercel.json`, but keeping them in project settings avoids committing even
non-secret URLs into a branch.

## 3. API base URL and CORS

The browser calls `${VITE_API_BASE_URL}/api/v1/...` cross-origin. Two things must
match on the Render side:

1. `CORS_ORIGINS` must list the exact Vercel origins, comma-separated, with no
   trailing slash and no wildcard:
   `https://app.example.com,https://epi-git-main-example.vercel.app`.
   Preview URLs are unique per deployment; either add the stable branch alias or
   accept that preview sign-in fails CORS.
2. The API must allow credentials. It does (`allow_credentials=True` with explicit
   origins). Wildcard CORS is refused at startup in production, which is correct:
   credentials cannot be combined with `*`.

Requests from the SPA include `credentials: "include"` so the refresh cookie is
sent to the API origin.

## 4. Authentication and cookie behaviour

- The access token lives **only in memory** (`frontend/src/lib/api.ts`); it is
  never written to `localStorage`, so an XSS cannot read a durable token.
- The refresh token is an httpOnly cookie set by the API, scoped to
  `/api/v1/auth`. JavaScript cannot read it.
- A page reload calls `/auth/refresh` once to recover a session; concurrent 401s
  share a single refresh.
- Refresh tokens are single-use and rotated; a replayed token is rejected.

Deployment consequences:

| Frontend → API | Required `REFRESH_COOKIE_SAMESITE` | Notes |
| --- | --- | --- |
| `app.example.com` → `api.example.com` (same site) | `lax` (or `strict`) | Recommended. Set `REFRESH_COOKIE_DOMAIN=.example.com` only if other subdomains must receive it. |
| `*.vercel.app` → `*.onrender.com` (cross-site) | `none` | Cookie must also be `Secure`; requires HTTPS on both ends. Some browsers block third-party cookies entirely, so this is a fallback, not the preferred shape. |

Set `REFRESH_COOKIE_SECURE=true` in production. Leaving it unset derives
`Secure` from `APP_ENV`, but explicit is safer.

Custom domains are strongly preferred: they keep the auth cookie first-party,
avoid third-party-cookie blocking, and let you use `lax` instead of `none`.

## 5. Deploying

1. Create the Vercel project from the repository, root directory `frontend`.
2. Add `VITE_API_BASE_URL` for Production and Preview.
3. Deploy; open the deployment URL and check the browser console for CORS errors.
4. Confirm the API logs the request and returns the CORS headers with the exact
   origin (not `*`).
5. Sign in, reload the page, and confirm the session is recovered from the
   refresh cookie. Reload is the step that catches a wrong SameSite/domain
   configuration.

## 6. Rollback

Vercel keeps immutable deployments: promote the previous deployment to production
from the dashboard. Because the SPA is static, rollback does not touch the
database — keep the API backward compatible for at least one frontend release.

## 7. Not verified here

No Vercel project exists for this repository and nothing was deployed. The build
settings match the checked-in `package.json`/`vite.config.ts`, and
`npm run build` passes locally, but the hosted build, domain and cookie behaviour
have not been exercised in a real browser against a deployed API.
