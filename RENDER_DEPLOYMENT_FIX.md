# URGENT: Fix Render Port Binding Error

## Problem
Your deployment is failing because of a PORT environment variable mismatch:

```
✅ Gunicorn listening on port 10000 (correct - Render's automatic assignment)
❌ Render scanning for port 5000 (wrong - from manual PORT variable in dashboard)
```

## Root Cause
You have manually set `PORT=5000` as an environment variable in your Render dashboard. This conflicts with Render's automatic PORT assignment (10000).

## SOLUTION: Delete the PORT Variable from Render Dashboard

### Step-by-Step Fix:

1. **Go to Render Dashboard**
   - Navigate to: https://dashboard.render.com
   - Select your service: `company-policy-rag`

2. **Delete the PORT Environment Variable**
   - Click **"Environment"** in the left sidebar
   - Look for an environment variable named **PORT** with value **5000**
   - Click the **trash/delete icon** (🗑️) next to it
   - Click **"Save Changes"**

3. **Redeploy**
   - The deployment will automatically trigger
   - OR manually trigger: Go to "Manual Deploy" → "Deploy latest commit"

## Why This Happens

Render web services automatically set the `PORT` environment variable to **10000**. When you manually override it to **5000**:
- Your `startCommand` uses `$PORT` → Render sets this to 10000 internally
- Gunicorn binds to **10000** (using Render's automatic PORT)
- But Render's health check looks for **5000** (your manual override)
- Result: Port mismatch → deployment timeout

## Expected Result After Fix

Once you delete the PORT variable, you should see:
```
✅ Starting gunicorn 21.2.0
✅ Listening at: http://0.0.0.0:10000
✅ Scanning for open port 10000
✅ Port 10000 is open
✅ Your service is live
```

## Configuration Files (Already Correct)

- ✅ `render.yaml` - Uses `$PORT` correctly
- ✅ `Procfile` - Uses `$PORT` correctly  
- ✅ `app.py` - Falls back to 10000 for local development
- ✅ `runtime.txt` - Python 3.11.9
- ✅ `requirements.txt` - All compatible packages

## DO NOT

❌ Do NOT manually set a PORT environment variable in Render
❌ Do NOT hardcode port numbers in your start command
❌ Let Render manage the PORT automatically

## Alternative (If Required to Use Specific Port)

If your organization REQUIRES port 5000, update `render.yaml`:

```yaml
startCommand: gunicorn -w 2 -b 0.0.0.0:5000 app:app --timeout 120
```

And keep PORT=5000 in environment variables. But this is NOT recommended.

---

**Status**: Awaiting manual dashboard fix
**Action Required**: Delete PORT=5000 from Render Environment Variables
**ETA**: 2 minutes after fix applied

