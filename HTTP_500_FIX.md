# Fix for HTTP 500 Error in Production

## Problem Analysis

From the production logs:
```
127.0.0.1 - - [26/Oct/2025:03:35:24 +0000] "POST /chat HTTP/1.1" 500 145
```

**Status**: ✅ App is live, but ❌ users get HTTP 500 errors when asking questions

## Root Cause

The HTTP 500 error when POSTing to `/chat` is likely caused by one of these issues:

1. **RAG pipeline initialization failure** - ChromaDB or embedding model not loading properly
2. **API key issues** - Missing or invalid OPENROUTER_API_KEY/GROQ_API_KEY
3. **Memory/timeout during first query** - Embedding model loading takes too long

The telemetry warning (`Failed to send telemetry event ClientStartEvent`) suggests ChromaDB compatibility issues.

## Fixes Applied

### 1. **Enhanced Error Logging** (app.py)
Added comprehensive logging to diagnose the exact error:
```python
print(f"🔍 Initializing RAG pipeline...")
print(f"❌ ERROR in /chat endpoint:")
print(error_trace)
```

This will help us see the exact error in Render logs.

### 2. **Removed --preload Flag** (Procfile & render.yaml)
The `--preload` flag causes issues with:
- ChromaDB (SQLite doesn't work well with preloading)
- Lazy-loaded embedding models
- Global state in workers

Changed from:
```bash
--preload  # REMOVED
```

### 3. **Better Error Response**
Now returns detailed error information:
```python
return jsonify({
    'error': 'Internal server error',
    'message': str(e),
    'type': type(e).__name__
}), 500
```

## Next Steps to Debug

After deploying these changes, check the Render logs for:

1. **When user asks a question**, you'll see:
   ```
   🔍 Initializing RAG pipeline for question: ...
   ⏳ Loading embedding model: all-MiniLM-L6-v2
   ✅ Embedding model loaded on cpu
   🔎 Executing query...
   ✅ Query executed successfully
   ```

2. **If there's an error**, you'll see:
   ```
   ❌ ERROR in /chat endpoint:
   Traceback (most recent call last):
   ...
   [exact error details]
   ```

## Most Likely Issues & Solutions

### Issue 1: Missing API Key
**Symptoms**: Error message about API key
**Fix**: Verify in Render dashboard that `OPENROUTER_API_KEY` or `GROQ_API_KEY` is set

### Issue 2: ChromaDB Not Found
**Symptoms**: "Could not load collection" error
**Fix**: Check build logs to ensure `python ingest.py` completed successfully

### Issue 3: Memory/Timeout on First Query
**Symptoms**: Worker timeout or SIGKILL
**Fix**: Already applied - 300s timeout should be enough

### Issue 4: Model Download Issues
**Symptoms**: Errors downloading sentence-transformers model
**Fix**: The model should be cached during build, but might fail on first runtime

## Deploy This Fix

```bash
git add app.py Procfile render.yaml
git commit -m "Add error logging and remove preload flag to fix HTTP 500"
git push
```

## Testing After Deployment

1. **Visit your site**: https://company-policy-rag-system-fynf.onrender.com/
2. **Ask a test question**: "How many PTO days do I get?"
3. **Check Render logs** for the detailed error trace
4. **Share the error output** so we can apply the specific fix

## Quick Diagnostics

Test these endpoints manually:

```bash
# Test health endpoint
curl https://company-policy-rag-system-fynf.onrender.com/health

# Test chat endpoint
curl -X POST https://company-policy-rag-system-fynf.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many PTO days?"}'
```

The response will now include the error type and message!

---

**Next Action**: Deploy these changes and check the logs for the detailed error message. Once we see the exact error, we can apply a targeted fix.

