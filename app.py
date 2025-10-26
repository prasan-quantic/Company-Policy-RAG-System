"""
Flask web application for Company Policy RAG system.
Provides web interface and API endpoints for querying company policies.
"""

import os
import time
import threading
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv
from rag import RAGPipeline

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize RAG pipeline (loaded once at startup)
rag_pipeline = None
rag_lock = threading.Lock()
preload_complete = False

def preload_rag_pipeline():
    """Preload RAG pipeline in background to avoid first-request timeout."""
    global rag_pipeline, preload_complete
    try:
        print("🔄 Preloading RAG pipeline in background...")
        with rag_lock:
            if rag_pipeline is None:
                rag_pipeline = RAGPipeline(
                    db_path=os.getenv("CHROMA_DB_PATH", "chroma_db"),
                    embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
                    llm_provider=os.getenv("LLM_PROVIDER", "openrouter"),
                    model_name=os.getenv("MODEL_NAME", "google/gemini-flash-1.5-8b"),
                    top_k=int(os.getenv("TOP_K", "5"))
                )
                # Force load embedding model now
                _ = rag_pipeline._load_embedding_model()
        preload_complete = True
        print("✅ RAG pipeline preloaded successfully")
    except Exception as e:
        print(f"❌ Error preloading RAG pipeline: {e}")
        import traceback
        traceback.print_exc()

def get_rag_pipeline():
    """Get RAG pipeline instance."""
    global rag_pipeline
    with rag_lock:
        if rag_pipeline is None:
            rag_pipeline = RAGPipeline(
                db_path=os.getenv("CHROMA_DB_PATH", "chroma_db"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
                llm_provider=os.getenv("LLM_PROVIDER", "openrouter"),
                model_name=os.getenv("MODEL_NAME", "google/gemini-flash-1.5-8b"),
                top_k=int(os.getenv("TOP_K", "5"))
            )
    return rag_pipeline

# Start preloading in background thread
preload_thread = threading.Thread(target=preload_rag_pipeline, daemon=True)
preload_thread.start()

@app.route('/')
def index():
    """Render main chat interface."""
    # Only handle GET requests, not HEAD
    if request.method == 'HEAD':
        return '', 200
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors."""
    try:
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )
    except FileNotFoundError:
        # Return empty response if favicon doesn't exist
        return '', 204


@app.route('/health', methods=['GET', 'HEAD'])
def health():
    """Health check endpoint."""
    # Handle HEAD requests properly
    if request.method == 'HEAD':
        return '', 200

    try:
        # For GET requests, check if preload is complete
        if not preload_complete:
            return jsonify({
                'status': 'warming_up',
                'service': 'Company Policy RAG System',
                'message': 'Loading models...',
                'timestamp': time.time()
            }), 200

        # Check if vector DB is accessible
        rag = get_rag_pipeline()
        chunk_count = rag.collection.count()

        return jsonify({
            'status': 'healthy',
            'service': 'Company Policy RAG System',
            'vector_db': 'connected',
            'chunks_indexed': chunk_count,
            'timestamp': time.time()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 503


@app.route('/status', methods=['GET'])
def status():
    """Check if system is ready."""
    return jsonify({
        'ready': preload_complete,
        'message': 'System ready' if preload_complete else 'Loading models...'
    }), 200


@app.route('/chat', methods=['POST', 'OPTIONS'])
def chat():
    """
    API endpoint for chat queries.

    Request JSON:
    {
        "question": "How many PTO days do I get?",
        "top_k": 5 (optional),
        "use_rerank": false (optional)
    }

    Response JSON:
    {
        "answer": "...",
        "sources": [...],
        "question": "...",
        "latency_ms": 1234
    }
    """
    # Handle OPTIONS for CORS preflight
    if request.method == 'OPTIONS':
        return '', 204

    try:
        # Check if system is ready
        if not preload_complete:
            return jsonify({
                'error': 'System is still warming up. Please try again in a few seconds.',
                'ready': False
            }), 503

        # Parse request
        data = request.get_json()

        if not data or 'question' not in data:
            return jsonify({
                'error': 'Missing required field: question',
                'example': {'question': 'How many PTO days do I get?'}
            }), 400

        question = data['question'].strip()

        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400

        top_k = data.get('top_k', None)
        use_rerank = data.get('use_rerank', False)

        # Track latency
        start_time = time.time()

        # Get RAG pipeline
        print(f"🔍 Processing question: {question[:50]}...")
        rag = get_rag_pipeline()

        # Execute query
        result = rag.query(
            question=question,
            top_k=top_k,
            use_rerank=use_rerank
        )
        print(f"✅ Query executed successfully")

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        result['latency_ms'] = latency_ms

        return jsonify(result), 200

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ ERROR in /chat endpoint:")
        print(error_trace)
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'type': type(e).__name__
        }), 500


@app.route('/documents', methods=['GET'])
def list_documents():
    """List all indexed documents."""
    try:
        rag = get_rag_pipeline()

        # Get all unique documents
        results = rag.collection.get()

        # Extract unique documents
        docs = {}
        for metadata in results['metadatas']:
            doc_id = metadata['doc_id']
            if doc_id not in docs:
                docs[doc_id] = {
                    'doc_id': doc_id,
                    'title': metadata['title'],
                    'chunks': 0
                }
            docs[doc_id]['chunks'] += 1

        return jsonify({
            'documents': list(docs.values()),
            'total_documents': len(docs),
            'total_chunks': len(results['ids'])
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Use PORT environment variable or default to 10000 for Render compatibility
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
