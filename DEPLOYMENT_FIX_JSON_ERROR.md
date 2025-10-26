# Deployment Fix - JSON Parsing Error

## Problem Analysis

The production error "Failed to execute 'json' on 'Response': Unexpected end of JSON input" was caused by:

1. **Worker Timeout** - Gunicorn workers were timing out (30s default) while loading the heavy sentence-transformers embedding model
2. **Worker Killed** - Workers were sent SIGKILL due to timeout, interrupting requests mid-flight
3. **HEAD Requests** - Browser was making HEAD requests that returned 200 with empty body, causing JSON parsing errors
4. **Memory Issues** - Free tier Render instance running out of memory during model loading

## Root Cause

```
[2025-10-26 14:17:44 +0000] [38] [CRITICAL] WORKER TIMEOUT (pid:46)
[2025-10-26 14:18:11 +0000] [38] [ERROR] Worker (pid:46) was sent SIGKILL! Perhaps out of memory?
```

The embedding model (sentence-transformers) was being loaded on first request, causing:
- Worker timeout after 30 seconds
- Incomplete HTTP responses
- JSON parsing errors on frontend

## Solutions Implemented

### 1. Background Model Preloading (app.py)

Added background thread to preload the RAG pipeline and embedding model **before** handling any requests:

```python
preload_complete = False

def preload_rag_pipeline():
    """Preload RAG pipeline in background to avoid first-request timeout."""
    global rag_pipeline, preload_complete
    # Load RAG pipeline
    rag_pipeline = RAGPipeline(...)
    # Force load embedding model now
    _ = rag_pipeline._load_embedding_model()
    preload_complete = True
```

### 2. Increased Worker Timeout (render.yaml)

Changed gunicorn timeout from default 30s to 600s to allow model loading:

```yaml
startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 600 --workers 1 --worker-class sync --max-requests 100 --max-requests-jitter 10 --preload
```

### 3. HEAD Request Handling (app.py)

Fixed HEAD requests to return proper empty responses without trying to render JSON:

```python
@app.route('/health', methods=['GET', 'HEAD'])
def health():
    if request.method == 'HEAD':
        return '', 200
    # ... JSON response for GET
```

### 4. Warming-Up State (app.py)

Added status endpoint and warming state to inform users system is loading:

```python
@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'ready': preload_complete,
        'message': 'System ready' if preload_complete else 'Loading models...'
    })
```

### 5. Frontend Error Handling (index.html)

Improved frontend to properly handle:
- Empty responses
- Non-JSON responses  
- 503 warming-up state with auto-retry

```javascript
// Check content type before parsing
const contentType = response.headers.get('content-type');
if (!contentType || !contentType.includes('application/json')) {
    throw new Error('Server returned non-JSON response');
}

// Check for empty response
const text = await response.text();
if (!text) {
    throw new Error('Server returned empty response');
}

// Now safely parse JSON
const data = JSON.parse(text);

// Handle warming state
if (response.status === 503 && data.ready === false) {
    // Auto-retry after 3 seconds
    setTimeout(() => askQuestion(question), 3000);
}
```

## Benefits

1. ✅ **No more worker timeouts** - Model preloads in background
2. ✅ **No JSON parsing errors** - Proper response validation
3. ✅ **Better UX** - Users see warming state instead of cryptic errors
4. ✅ **Faster responses** - Model already loaded when first request comes
5. ✅ **Memory efficient** - Single worker with preloading

## Testing

After deployment, check:

1. `/health` endpoint returns warming state initially, then healthy
2. `/status` endpoint shows ready=true after preload
3. First chat request doesn't timeout
4. No worker SIGKILL messages in logs

## Expected Startup Sequence

```
==> Running 'gunicorn app:app'
[INFO] Starting gunicorn 21.2.0
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Booting worker with pid: 46
🔄 Preloading RAG pipeline in background...
✅ Loaded existing collection with 123 chunks
⏳ Loading embedding model: all-MiniLM-L6-v2
✅ Embedding model loaded on cpu
✅ RAG pipeline preloaded successfully
==> Your service is live 🎉
```

## Deployment

Push changes to trigger redeployment:

```bash
git add app.py render.yaml templates/index.html
git commit -m "Fix: Worker timeout and JSON parsing errors in production"
git push
```

Monitor Render logs for successful startup with preload message.

