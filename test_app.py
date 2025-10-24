"""
Test suite for Company Policy RAG System
Tests app endpoints, RAG pipeline, and system health
"""

import pytest
import json
import os
from app import app, get_rag_pipeline
from rag import RAGPipeline


@pytest.fixture
def client():
    """Create Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def rag_pipeline():
    """Create RAG pipeline for testing"""
    return get_rag_pipeline()


class TestAppEndpoints:
    """Test Flask application endpoints"""

    def test_index_page(self, client):
        """Test that index page loads"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Company Policy Assistant' in response.data

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'chunks_indexed' in data

    def test_documents_endpoint(self, client):
        """Test documents listing endpoint"""
        response = client.get('/documents')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'documents' in data
        assert 'total_documents' in data
        assert data['total_documents'] >= 5  # At least 5 policy docs

    def test_chat_post_valid(self, client):
        """Test chat endpoint with valid question"""
        response = client.post('/chat',
                              json={'question': 'How many PTO days do I get?'},
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data
        assert 'sources' in data
        assert 'latency_ms' in data
        assert len(data['sources']) > 0

    def test_chat_post_missing_question(self, client):
        """Test chat endpoint without question"""
        response = client.post('/chat',
                              json={},
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_chat_post_empty_question(self, client):
        """Test chat endpoint with empty question"""
        response = client.post('/chat',
                              json={'question': ''},
                              content_type='application/json')
        assert response.status_code == 400

    def test_chat_get_not_allowed(self, client):
        """Test that GET is not allowed on /chat"""
        response = client.get('/chat')
        assert response.status_code == 405  # Method Not Allowed

    def test_404_handler(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data


class TestRAGPipeline:
    """Test RAG pipeline functionality"""

    def test_rag_initialization(self, rag_pipeline):
        """Test RAG pipeline initializes correctly"""
        assert rag_pipeline is not None
        assert rag_pipeline.collection is not None
        assert rag_pipeline.embedding_model is not None

    def test_retrieval(self, rag_pipeline):
        """Test document retrieval"""
        chunks = rag_pipeline.retrieve("PTO policy", top_k=5)
        assert len(chunks) > 0
        assert len(chunks) <= 5
        assert 'text' in chunks[0]
        assert 'metadata' in chunks[0]

    def test_query_returns_answer(self, rag_pipeline):
        """Test that query returns structured answer"""
        result = rag_pipeline.query("How many PTO days?", top_k=3)
        assert 'answer' in result
        assert 'sources' in result
        assert 'question' in result
        assert isinstance(result['sources'], list)

    def test_query_with_citations(self, rag_pipeline):
        """Test that answers include citations"""
        result = rag_pipeline.query("What is the 401k match?")
        answer = result['answer']
        # Should have source citations
        assert '[Source' in answer or 'Source' in answer
        assert len(result['sources']) > 0

    def test_guardrails_out_of_scope(self, rag_pipeline):
        """Test that system refuses out-of-scope questions"""
        result = rag_pipeline.query("What is the weather today?")
        answer = result['answer'].lower()
        # Should refuse or indicate limited knowledge
        assert 'cannot' in answer or 'only' in answer or 'policy' in answer or 'don\'t have' in answer


class TestSystemIntegration:
    """Test system integration and requirements"""

    def test_environment_variables(self):
        """Test that required environment variables can be loaded"""
        from dotenv import load_dotenv
        load_dotenv()
        # Check that at least one LLM provider is configured
        has_groq = os.getenv('GROQ_API_KEY') and os.getenv('GROQ_API_KEY') != 'your_groq_api_key_here'
        has_openrouter = os.getenv('OPENROUTER_API_KEY') and os.getenv('OPENROUTER_API_KEY') != 'your_openrouter_api_key_here'
        has_openai = os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_API_KEY') != 'your_openai_api_key_here'
        assert has_groq or has_openrouter or has_openai, "No valid API key configured"

    def test_document_corpus_exists(self):
        """Test that document corpus has sufficient files"""
        docs_dir = 'documents'
        assert os.path.exists(docs_dir)
        files = [f for f in os.listdir(docs_dir) if f.endswith('.md')]
        assert len(files) >= 5, f"Need at least 5 documents, found {len(files)}"

    def test_vector_db_exists(self):
        """Test that vector database exists"""
        db_path = os.getenv('CHROMA_DB_PATH', 'chroma_db')
        assert os.path.exists(db_path), "Vector database not found. Run ingest.py first"

    def test_templates_exist(self):
        """Test that required templates exist"""
        assert os.path.exists('templates/index.html')

    def test_eval_questions_exist(self):
        """Test that evaluation questions file exists"""
        assert os.path.exists('eval_questions.json')
        with open('eval_questions.json', 'r', encoding='utf-8') as f:
            questions = json.load(f)
        assert len(questions) >= 15, "Need at least 15 evaluation questions"


class TestDocumentProcessing:
    """Test document processing and chunking"""

    def test_chunk_count(self, rag_pipeline):
        """Test that sufficient chunks are indexed"""
        count = rag_pipeline.collection.count()
        assert count >= 50, f"Expected at least 50 chunks, found {count}"
        assert count <= 500, f"Too many chunks: {count}"

    def test_metadata_structure(self, rag_pipeline):
        """Test that chunks have proper metadata"""
        results = rag_pipeline.collection.get(limit=1)
        assert len(results['metadatas']) > 0
        metadata = results['metadatas'][0]
        assert 'doc_id' in metadata
        assert 'title' in metadata
        assert 'chunk_id' in metadata


class TestPerformance:
    """Test performance requirements"""

    def test_query_latency(self, rag_pipeline):
        """Test that queries complete within reasonable time"""
        import time
        start = time.time()
        result = rag_pipeline.query("How many PTO days?")
        latency = time.time() - start
        assert latency < 5.0, f"Query took too long: {latency:.2f}s"
        assert 'latency_ms' in result

    def test_retrieval_speed(self, rag_pipeline):
        """Test that retrieval is fast"""
        import time
        start = time.time()
        chunks = rag_pipeline.retrieve("PTO policy", top_k=5)
        latency = time.time() - start
        assert latency < 1.0, f"Retrieval took too long: {latency:.2f}s"
        assert len(chunks) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
