# DocuMind AI — Login Failure Walkthrough (2026-08)

The "login 405" saga was actually **two independent bugs** producing an identical
network pattern (request -> 308/307 redirect -> 405). The first fix shipped was
harmless but not the cure; the second was the real cause.

## Timeline

### 1. Backend hardening — `redirect_slashes` (shipped first, NOT the cure)

- **Symptom**: cross-origin auth requests showed a redirect (307 for POST, 308
  for GET/HEAD) followed by 405.
- **Fix**: `redirect_slashes=False` on the `FastAPI()` app instance
  (`backend/app/main.py`). Slash-mismatched paths now 404 instead of redirecting.
- **Commit**: `5d65b573` — `fix(api): disable redirect_slashes to prevent cross-origin 308/405 auth failures`
- **Reality check**: the repo's frontend never sent trailing slashes, so this
  changed nothing for real traffic. It remains valid hardening (kills the
  redirect class for any client), but it did not fix login.

### 2. THE REAL BUG — malformed `VITE_API_URL` in Vercel env vars

- **Symptom**: browser console showed the login POST going to
  `https://docu-mind-ai-iota.vercel.app/[https://documind-ai-97t5.onrender.com](https://documind-ai-97t5.onrender.com)/api/auth/login`
  — i.e. hitting the **frontend's own Vercel domain** with a bracketed string in
  the path, producing Vercel's 308 -> 405.
- **Root cause**: Vercel's project env var `VITE_API_URL` was set to a full
  **Markdown link** `[https://documind-ai-97t5.onrender.com](https://documind-ai-97t5.onrender.com)`
  (brackets + parentheses, pasted from a README). Vite bakes `import.meta.env.VITE_API_URL`
  into the bundle at build time; the leading `[` made `fetch` treat it as a
  *relative* URL, resolved against the Vercel origin. The repo's `frontend/.env`
  was always clean (verified via `git log -p -- frontend/.env`) — the poison came
  from the platform env var, which overrides `.env` at build time.
- **Detection**: curl-based testing hit the backend directly, so it never saw
  this. The value was extracted from the **deployed bundle**
  (`assets/index-DQFcQwww.js`) — the definitive source for what Vite actually
  baked in.
- **Fix**: Vercel dashboard -> Settings -> Environment Variables ->
  `VITE_API_URL` = `https://documind-ai-97t5.onrender.com` (bare URL), then
  Redeploy (env changes do not apply retroactively).
- **Verification** (post-redeploy):
  - New bundle `assets/index-tv0d-cUr.js`; extracted baked value:
    `https://documind-ai-97t5.onrender.com` — bare, no brackets.
  - Preflight: `OPTIONS /api/auth/login` with the Vercel Origin -> 200 +
    `access-control-allow-origin: https://docu-mind-ai-iota.vercel.app`.
  - Valid login -> 200, `redirects=0`; invalid login -> 401, `redirects=0`.
  - `/api/auth/me`, `/api/documents`, `/api/conversations`,
    `/api/analytics/summary` all 200.

### 3. Related frontend race — double-click duplicate POSTs

- While investigating, `AuthModal.jsx` was found to fire two `handleSubmit` calls
  on a rapid double-click (before the `disabled`/`loading` state re-rendered).
- **Fix**: synchronous `useRef` in-flight guard in `handleSubmit`
  (`frontend/src/components/AuthModal.jsx`).
- **Commit**: `f2a4e919` — `fix(frontend): guard login submit against double-click duplicate POSTs`

### 4. Hardening — fail loudly on bad `API_URL`

- Module-load validation in `frontend/src/services/api.js`: throws
  `Invalid VITE_API_URL: must be an absolute URL starting with http:// or https://, got: <value>`
  if `API_URL` isn't absolute — so a future bad env var fails visibly at app
  load instead of silently 404/405ing at request time.
- **Commit**: `6aa509b3` — `fix(frontend): fail loudly on malformed VITE_API_URL at module load`

## How to verify the deployed bundle (regression check)

```bash
# 1. Get current bundle name (note: may contain '-' — adjust the pattern)
curl -s https://docu-mind-ai-iota.vercel.app/ | grep -o 'assets/index-[^"]*\.js'
# 2. Confirm the baked URL is a bare absolute URL (no [ ] ( ) characters)
curl -s https://docu-mind-ai-iota.vercel.app/assets/<BUNDLE> | grep -o 'https://documind-ai-97t5[^"]*'
```

## Key lesson

`import.meta.env.VITE_*` values are **baked into the bundle at build time** and
**platform env vars override committed `.env` files**. When a live frontend
misbehaves in a way the code doesn't explain, extract the actual baked value
from the deployed JS bundle before touching code.
