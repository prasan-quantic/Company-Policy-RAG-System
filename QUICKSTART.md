# Quick Start Guide

## Setup (5 minutes)

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Free API Key
Visit https://openrouter.ai/keys and create a free account to get an API key.

### 3. Configure Environment
```bash
copy .env.example .env
```

Edit `.env` and add your API key:
```
OPENROUTER_API_KEY=your_key_here
```

### 4. Index Documents
```bash
python ingest.py
```

Wait ~2 minutes while documents are processed. You should see:
```
Total documents: 8
Total chunks: ~150-200
```

### 5. Run Application
```bash
python app.py
```

Visit: http://localhost:5000

## Testing Queries

Try these example questions:

**PTO & Leave:**
- "How many PTO days do I get?"
- "How long is maternity leave?"
- "Can I carry over unused PTO?"

**Remote Work:**
- "Can I work remotely?"
- "What are the core hours for remote workers?"
- "What equipment does the company provide?"

**Expenses:**
- "What's the daily meal limit when traveling?"
- "Can I expense my gym membership?"
- "How do I submit expense reports?"

**Security:**
- "What are the password requirements?"
- "Do I need MFA?"
- "What should I do if I lose my laptop?"

**Benefits:**
- "What is the 401k match?"
- "What health insurance plans are available?"
- "What's the tuition reimbursement policy?"

## Running Evaluation

```bash
python evaluate.py
```

This will:
- Test 30 questions across all policy areas
- Measure groundedness and citation accuracy
- Calculate latency metrics (P50, P95)
- Save results to `evaluation_results.json`

Expected results:
- Groundedness: 85-95%
- Citation Accuracy: 95-100%
- Latency P50: 1000-2000ms

## Troubleshooting

**Problem: "Collection not found"**
```bash
python ingest.py  # Re-run ingestion
```

**Problem: API errors**
- Check API key in `.env`
- Try alternative provider: `LLM_PROVIDER=groq`
- Verify quota at https://openrouter.ai/activity

**Problem: Slow responses**
- Reduce retrieval: `TOP_K=3` in `.env`
- Use faster model: `MODEL_NAME=llama-3.1-8b-instant`

**Problem: Import errors**
```bash
pip install -r requirements.txt --upgrade
```

## Next Steps

1. **Deploy to Production**
   - See README.md deployment section
   - Configure secrets in hosting platform
   - Set `FLASK_ENV=production`

2. **Customize**
   - Add more policy documents to `documents/`
   - Adjust RAG parameters in `.env`
   - Modify prompts in `rag.py`

3. **Integrate**
   - Use `/chat` API endpoint in other apps
   - Build Slack/Teams bot
   - Add authentication layer

## Project Structure

```
AI/
├── documents/              # Your policy docs (8 .md files)
├── templates/index.html    # Web UI
├── app.py                  # Flask server
├── rag.py                  # RAG pipeline
├── ingest.py              # Document indexing
├── evaluate.py            # Evaluation framework
├── chroma_db/             # Vector database (auto-created)
└── requirements.txt       # Dependencies
```

## Support

- Documentation: README.md and DESIGN.md
- Health check: http://localhost:5000/health
- API docs: See README.md "API Usage" section
"""
Simple test suite for RAG application.
"""

import os
import sys

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import flask
        print("  ✓ Flask")
    except ImportError as e:
        print(f"  ✗ Flask: {e}")
        return False
    
    try:
        import chromadb
        print("  ✓ ChromaDB")
    except ImportError as e:
        print(f"  ✗ ChromaDB: {e}")
        return False
    
    try:
        import sentence_transformers
        print("  ✓ Sentence Transformers")
    except ImportError as e:
        print(f"  ✗ Sentence Transformers: {e}")
        return False
    
    try:
        import app
        print("  ✓ App module")
    except ImportError as e:
        print(f"  ✗ App module: {e}")
        return False
    
    try:
        import rag
        print("  ✓ RAG module")
    except ImportError as e:
        print(f"  ✗ RAG module: {e}")
        return False
    
    try:
        import ingest
        print("  ✓ Ingest module")
    except ImportError as e:
        print(f"  ✗ Ingest module: {e}")
        return False
    
    return True


def test_documents():
    """Test that document corpus exists."""
    print("\nTesting document corpus...")
    
    docs_path = "documents"
    if not os.path.exists(docs_path):
        print(f"  ✗ Documents directory not found: {docs_path}")
        return False
    
    files = [f for f in os.listdir(docs_path) if f.endswith(('.md', '.txt', '.pdf', '.html'))]
    print(f"  ✓ Found {len(files)} document files")
    
    if len(files) < 8:
        print(f"  ⚠ Warning: Expected at least 8 documents, found {len(files)}")
    
    return True


def test_env_file():
    """Test environment configuration."""
    print("\nTesting environment configuration...")
    
    if not os.path.exists('.env'):
        print("  ⚠ .env file not found (optional for testing)")
        return True
    
    print("  ✓ .env file exists")
    return True


if __name__ == "__main__":
    print("="*60)
    print("Running RAG Application Tests")
    print("="*60)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Documents", test_documents()))
    results.append(("Environment", test_env_file()))
    
    print("\n" + "="*60)
    print("Test Results")
    print("="*60)
    
    all_passed = all(result[1] for result in results)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    print("="*60)
    
    if all_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

