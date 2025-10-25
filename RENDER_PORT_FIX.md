# Fix Render Port Binding Issue

## Problem
Your deployment is failing with this error:
```
Listening at: http://0.0.0.0:10000 (55)  ✅ Correct
Continuing to scan for open port 5000 (from PORT environment variable)... ❌ Wrong
```

Gunicorn starts on port 10000 (correct), but Render expects port 5000 (misconfigured).

## Root Cause
You have a **PORT environment variable manually set to 5000** in your Render dashboard that conflicts with Render's automatic PORT assignment (10000).

## Solution - Delete the PORT Variable

### Step 1: Access Render Dashboard
1. Go to https://dashboard.render.com
2. Select your `company-policy-rag` service

### Step 2: Remove PORT Variable
1. Click on **Environment** in the left sidebar
2. Look for a variable named **PORT** with value **5000**
3. Click the **Delete** button (🗑️) next to it
4. Click **Save Changes**

### Step 3: Redeploy
1. Go to the **Events** tab
2. Click **Manual Deploy** → **Deploy latest commit**
3. Or just push a new commit (the deployment will auto-trigger)

## Why This Happens
- Render **automatically** sets `PORT` to `10000` for web services
- Your manual `PORT=5000` override conflicts with this
- The `$PORT` in gunicorn command uses Render's value (10000)
- But Render's health check uses your manual value (5000)
- Result: Port mismatch → deployment timeout

## Verification
After removing PORT and redeploying, you should see:
```
✅ Listening at: http://0.0.0.0:10000
✅ Scanning for open port 10000
✅ Port 10000 is open
✅ Deploy successful
```

## Alternative: If You Must Use Port 5000
If you really need port 5000, update your `render.yaml`:
```yaml
startCommand: gunicorn -w 2 -b 0.0.0.0:5000 app:app --timeout 120
envVars:
  - key: PORT
    value: 5000
```

But this is **NOT RECOMMENDED** - let Render manage the PORT automatically.

## Files Fixed
- ✅ `Procfile` - Updated to match render.yaml (2 workers)
- ✅ `render.yaml` - Already correct
- ✅ `runtime.txt` - Specifies Python 3.11.9
- ✅ `requirements.txt` - Compatible package versions

## Next Steps
1. Delete PORT=5000 from Render dashboard
2. Push this commit
3. Deployment should succeed automatically

---
**Created**: 2025-10-24
**Issue**: Port binding mismatch (5000 vs 10000)
**Status**: Awaiting manual dashboard fix

