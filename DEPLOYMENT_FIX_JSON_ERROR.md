# Deployment Fix - Worker Timeout Error

## Problem Analysis

The production error shows workers are timing out even with increased timeout:

```
[2025-10-26 15:07:22 +0000] [56] [CRITICAL] WORKER TIMEOUT (pid:66)
[2025-10-26 15:07:22 +0000] [66] [INFO] Worker exiting (pid: 66)
```

### Root Causes Identified

1. **Background Thread Preload Not Completing** - Background thread was non-blocking, so workers started before model loaded
2. **Heavy Embedding Model** - `all-MiniLM-L6-v2` takes 30-90 seconds to load on free tier memory constraints
3. **Sync Worker Class** - Synchronous workers block during model loading
4. **First Request Timeout** - Worker timeout kills process before embedding model finishes loading

## Solutions Implemented v2

### 1. Synchronous Module-Level Initialization (app.py)

**Changed from:** Background thread preload (non-blocking)  
**Changed to:** Module-level synchronous initialization

```python
# Initialize RAG pipeline at module load time (synchronous)
# This ensures it's loaded BEFORE gunicorn workers start
print("🔄 Initializing RAG pipeline at module load...")
rag_pipeline = RAGPipeline(...)
# Force load embedding model NOW during module initialization
_ = rag_pipeline._load_embedding_model()
print("✅ RAG pipeline initialized and ready!")
```

**Why this works:**

- Runs during Python module import
- Completes BEFORE Flask app starts accepting requests
- No race condition between preload and first request

### 2. Use gthread Worker Class (render.yaml)

**Changed from:** `sync` worker with `--preload`  
**Changed to:** `gthread` worker with 2 threads

```yaml
startCommand: gunicorn app:app --timeout 300 --workers 1 --threads 2 --worker-class gthread
```

**Benefits:**

- Threads share memory (single model instance)
- Better for I/O-bound operations (API calls to LLM)
- Lower memory footprint than multiple workers

### 3. Memory Optimizations (render.yaml)

Added environment variables to reduce memory usage:

```yaml
- key: TOKENIZERS_PARALLELISM
  value: "false"
- key: ORT_DEVICE
  value: CPU
- key: ANONYMIZED_TELEMETRY
  value: "False"
```

### 4. Reduced Timeout to 300s (render.yaml)

Since model loads at module import (not per-request), we can use shorter timeout:

```yaml
--timeout 300
```

### 5. Frontend Robust Error Handling (index.html)

Already implemented:

- ✅ Validates response content-type
- ✅ Checks for empty responses
- ✅ Auto-retries on 503 warming state
- ✅ Clear error messages

## Expected Behavior

### Startup Sequence

```
==> Running 'gunicorn app:app'
🔄 Initializing RAG pipeline at module load...
✅ Loaded existing collection with 123 chunks
⏳ Loading embedding model...
✅ Embedding model loaded on cpu
✅ RAG pipeline initialized and ready!
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Using worker: gthread
[INFO] Booting worker with pid: 46
==> Detected service running on port 10000
==> Your service is live 🎉
```

### First Request

```
127.0.0.1 - - [26/Oct/2025:15:30:00 +0000] "POST /chat HTTP/1.1" 200 512
✅ Query executed successfully
```

**NO worker timeout!** Model is already loaded.

## Testing Checklist

After deployment:

- [ ] Check logs show "RAG pipeline initialized and ready!" BEFORE worker starts
- [ ] No "WORKER TIMEOUT" messages in logs
- [ ] First `/chat` request completes successfully (< 10s response time)
- [ ] `/health` endpoint returns `{"status": "healthy"}`
- [ ] `/status` endpoint returns `{"ready": true}`
- [ ] No JSON parsing errors on frontend

## Deployment

```bash
git add app.py render.yaml DEPLOYMENT_FIX_JSON_ERROR.md
git commit -m "Fix: Synchronous model loading to prevent worker timeout"
git push
```

## Monitoring

Watch for these success indicators in Render logs:

✅ **Success Pattern:**

```
🔄 Initializing RAG pipeline at module load...
✅ RAG pipeline initialized and ready!
[INFO] Booting worker with pid: XX
==> Your service is live 🎉
```

❌ **Failure Pattern (if still occurs):**

```
[CRITICAL] WORKER TIMEOUT (pid:XX)
[ERROR] Worker (pid:XX) was sent SIGKILL!
```

## Fallback Plan (If Still Failing)

If worker still times out, the embedding model is too heavy for free tier. Alternative solutions:

1. **Use lighter model:** Change `EMBEDDING_MODEL` to `paraphrase-MiniLM-L3-v2` (even smaller)
2. **Lazy load on first request:** Accept slower first request but return 503 during load
3. **Use paid tier:** More memory/CPU for faster model loading
4. **Pre-compute embeddings:** Store query embeddings in cache

## Key Differences from Previous Fix

| Aspect | Previous (Failed) | Current (Fixed) |
|--------|------------------|-----------------|
| Preload method | Background thread | Synchronous module-level |
| Worker class | sync | gthread |
| Timeout | 600s | 300s |
| Threads | N/A | 2 threads |
| When model loads | Async after app start | Before app accepts requests |
| Memory optimization | Basic | + TOKENIZERS_PARALLELISM |
