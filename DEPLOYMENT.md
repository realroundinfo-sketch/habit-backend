# Deployment (Railway, etc.)

## Backend (this repo)

1. **Expose the service**  
   In Railway: **Settings → Networking → Generate domain** so the backend gets a public URL (e.g. `https://habit-backend-production-xxxx.up.railway.app`).

2. **Environment variables** (Variables tab):
   - `SECRET_KEY` — set a strong random secret for production.
   - `CORS_ORIGINS` — optional. Default is `*` (allows any frontend). To restrict: set to your frontend URL(s), comma-separated (e.g. `https://yourapp.vercel.app`).
   - `DATABASE_URL` — optional if using SQLite; for production you may use Railway PostgreSQL.

3. **Frontend** must call this backend: set `NEXT_PUBLIC_API_URL` to your backend public URL with path `/api/v1`, e.g.:
   ```bash
   NEXT_PUBLIC_API_URL=https://habit-backend-production-xxxx.up.railway.app/api/v1
   ```

After exposing the service and setting the frontend env, the live backend will support the frontend.
