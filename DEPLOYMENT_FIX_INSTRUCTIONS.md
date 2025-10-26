# Deployment Fix Instructions

## Problem Summary

Your Render deployment is failing with a **PORT mismatch error**:
- Gunicorn is listening on port **10000** (Render's automatic assignment)
- Render is scanning for port **5000** (from a manually set PORT environment variable)
- This causes deployment timeout and JSON parsing errors in production

## Root Causes

1. **PORT environment variable conflict**: There's a PORT variable manually set in your Render dashboard that overrides Render's automatic PORT=10000 assignment
2. **Missing proper port binding**: The application wasn't properly configured to use Render's PORT environment variable

## Fixes Applied

### 1. Updated `app.py`
- Added `if __name__ == '__main__'` block to properly handle PORT environment variable
- Defaults to port 5000 for local development, uses PORT env var in production

### 2. Updated `render.yaml`
- Modified startCommand to: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`
- Added timeout (120s) to handle slow model loading
- Set workers to 1 (recommended for free tier)
- Added CHROMA_DB_PATH environment variable

### 3. Updated `Procfile`
- Aligned with render.yaml configuration
- Properly binds to $PORT environment variable

### 4. Updated `.env`
- Removed PORT=1000 setting that was causing conflicts
- Added comment explaining PORT is set automatically by Render

## CRITICAL: Action Required on Render Dashboard

**You MUST manually delete the PORT environment variable from your Render dashboard:**

1. Go to your Render dashboard: https://dashboard.render.com
2. Select your `company-policy-rag` service
3. Go to **Environment** tab
4. Look for a variable named **PORT** with value **5000** or **1000**
5. Click the **X** button to delete it
6. Click **Save Changes**
7. Render will automatically redeploy

## Why This Is Necessary

Render web services automatically set `PORT=10000`. When you manually override it:
- Gunicorn binds to the manual port (5000)
- Render expects the service on port 10000
- Port scan fails → deployment times out
- Frontend gets HTML error pages instead of JSON → "Unexpected token '<'" error

## Expected Behavior After Fix

Once you delete the manual PORT variable from Render:

1. ✅ Render will set PORT=10000 automatically
2. ✅ Gunicorn will bind to 0.0.0.0:10000
3. ✅ Port scan will succeed
4. ✅ Health check at `/health` will pass
5. ✅ Deployment will complete successfully
6. ✅ Frontend will receive proper JSON responses

## Verification Steps

After redeployment:

1. Check logs for: `Listening at: http://0.0.0.0:10000`
2. Check logs for: `Port scan successful` (or similar)
3. Visit your service URL: `https://company-policy-rag.onrender.com`
4. Test the `/health` endpoint
5. Try asking a question in the UI

## Local Development

For local development, the app will default to port 5000:

```bash
python app.py
# Server runs on http://0.0.0.0:5000
```

Or with gunicorn:

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

## Common Issues

### Issue: "Port scan timeout"
**Solution**: Delete PORT environment variable from Render dashboard

### Issue: "Unexpected token '<'" in frontend
**Solution**: This happens when the backend returns HTML error pages. Fix the PORT issue first.

### Issue: Service keeps restarting
**Solution**: Check logs for actual errors. May need to verify API keys are set correctly.

## Configuration Summary

### Render Environment Variables (Should Have):
- ✅ FLASK_ENV=production
- ✅ OPENROUTER_API_KEY (set as secret)
- ✅ GROQ_API_KEY (set as secret)
- ✅ LLM_PROVIDER=openrouter
- ✅ MODEL_NAME=meta-llama/llama-3.1-8b-instruct:free
- ✅ EMBEDDING_MODEL=all-MiniLM-L6-v2
- ✅ TOP_K=5
- ✅ CHROMA_DB_PATH=chroma_db

### Render Environment Variables (Should NOT Have):
- ❌ PORT (let Render set this automatically)

## Support Resources

- Render Port Binding Docs: https://render.com/docs/web-services#port-binding
- Render Troubleshooting: https://render.com/docs/troubleshooting-deploys
- Your previous fix attempts: `RENDER_PORT_FIX.md`, `RENDER_DEPLOYMENT_FIX.md`

## Next Steps

1. **Delete PORT from Render dashboard** (most important!)
2. Commit and push the code changes made to:
   - `app.py`
   - `render.yaml`
   - `Procfile`
   - `.env`
3. Wait for automatic redeployment or trigger manually
4. Monitor logs for successful deployment
5. Test the application

---

**Last Updated**: October 25, 2025
**Status**: Ready for deployment after manual PORT deletion

