"""
Flask web application for Company Policy RAG system.
Provides web interface and API endpoints for querying company policies.
"""

import os
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv
from rag import RAGPipeline

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize RAG pipeline (loaded once at startup)
rag_pipeline = None

def get_rag_pipeline():
    """Lazy load RAG pipeline."""
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline(
            db_path=os.getenv("CHROMA_DB_PATH", "chroma_db"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            llm_provider=os.getenv("LLM_PROVIDER", "openrouter"),
            model_name=os.getenv("MODEL_NAME", "google/gemini-flash-1.5-8b"),
            top_k=int(os.getenv("TOP_K", "5"))
        )
    return rag_pipeline


@app.route('/')
def index():
    """Render main chat interface."""
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


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
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


@app.route('/chat', methods=['POST'])
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
    try:
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
        print(f"🔍 Initializing RAG pipeline for question: {question[:50]}...")
        rag = get_rag_pipeline()
        print(f"✅ RAG pipeline initialized")

        # Execute query
        print(f"🔎 Executing query...")
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
