# Company Policy RAG System

A production-ready Retrieval-Augmented Generation (RAG) system for querying company policies using natural language. Built with Python, ChromaDB, and LLM APIs (OpenRouter/Groq).

🚀 **Live Demo**: [Add your deployed URL here after deployment]

## 📋 Features

- 🤖 **Natural Language Queries**: Ask questions about company policies in plain English
- 📚 **8 Policy Documents**: PTO, remote work, expenses, benefits, security, and more
- 🎯 **Source Citations**: Every answer includes source document references
- ⚡ **Fast Retrieval**: Sub-second vector search with ChromaDB
- 🔒 **Guardrails**: Refuses to answer questions outside the policy corpus
- 📊 **Evaluation Framework**: Measures groundedness, citation accuracy, and latency
- 🌐 **Web Interface**: Clean, modern chat UI
- 🔧 **API Endpoints**: RESTful API for integration

## 🏗️ Architecture

```
User Query → Embedding (all-MiniLM-L6-v2) → Vector Search (ChromaDB) 
→ Top-K Retrieval → Prompt + Context → LLM (Llama 3.1/Groq) → Answer + Citations
```

**Tech Stack:**
- **Backend**: Python 3.9+, Flask
- **Vector DB**: ChromaDB (embedded)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: Groq (llama-3.1-8b-instant) or OpenRouter (free tier)
- **Deployment**: Render/Railway (free tier)

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Git

### Setup Steps

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd AI
```

2. **Create virtual environment**
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Copy the example environment file:
```bash
# On Windows
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
# Required: Choose one LLM provider
GROQ_API_KEY=your_groq_api_key_here
# OR
OPENROUTER_API_KEY=your_openrouter_api_key_here

# LLM Configuration
LLM_PROVIDER=groq
MODEL_NAME=llama-3.1-8b-instant
```

**Getting API Keys (Free):**
- **Groq** (Recommended): https://console.groq.com/keys
- **OpenRouter**: https://openrouter.ai/keys

5. **Ingest documents and build vector database**
```bash
python ingest.py
```

Expected output:
```
📄 Processing documents...
✅ Processed 8 documents, 150 chunks
💾 Indexed to ChromaDB
⏱️  Completed in 12.3 seconds
```

6. **Run the application**
```bash
python app.py
```

The app will start at `http://localhost:5000`

## 🚀 Usage

### Web Interface

1. Open your browser to `http://localhost:5000`
2. Type your question in the chat box
3. Click "Send" or press Enter
4. View the answer with source citations

**Example Questions:**
- "How many PTO days do I get?"
- "Can I work remotely?"
- "What is the 401k match?"
- "What are the password requirements?"
- "How do I submit an expense report?"

### API Usage

**POST /chat**
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many PTO days do I get?"}'
```

Response:
```json
{
  "answer": "Full-time employees accrue PTO based on years of service: 0-2 years get 15 days...",
  "sources": [
    {
      "source_num": 1,
      "title": "PTO Policy",
      "doc_id": "POL-001",
      "text_snippet": "0-2 years of service: 15 days (120 hours) per year..."
    }
  ],
  "question": "How many PTO days do I get?",
  "latency_ms": 1234
}
```

**GET /health**
```bash
curl http://localhost:5000/health
```

**GET /documents**
```bash
curl http://localhost:5000/documents
```

## 🧪 Testing and Evaluation

### Run Evaluation Suite

Evaluates the system on 20+ questions with metrics:

```bash
python evaluate.py
```

**Metrics Measured:**
- ✅ **Groundedness**: % of answers supported by sources (target: >90%)
- 📎 **Citation Accuracy**: % of answers with correct citations (target: >95%)
- ⚡ **Latency**: p50/p95 response times (target: <3s p95)
- 🎯 **Partial Match**: % containing expected information

Sample output:
```
📊 Evaluation Results (20 questions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Groundedness:      95.0% (19/20)
📎 Citation Accuracy:  100.0% (20/20)
🎯 Partial Match:      90.0% (18/20)
⚡ Latency (p50):      1.2s
⚡ Latency (p95):      2.8s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Run Tests

```bash
python -m pytest test_app.py -v
```

### Check Application Health

```bash
python check_status.py
```

## 📁 Project Structure

```
AI/
├── app.py                  # Flask web application
├── rag.py                  # RAG pipeline implementation
├── ingest.py              # Document ingestion and indexing
├── evaluate.py            # Evaluation framework
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
├── README.md             # This file
├── DESIGN.md             # Design decisions and rationale
├── QUICKSTART.md         # Quick reference guide
├── PROJECT_SUMMARY.md    # Project overview
│
├── documents/            # Policy documents (8 markdown files)
│   ├── pto_policy.md
│   ├── remote_work_policy.md
│   ├── expense_reimbursement.md
│   ├── employee_benefits.md
│   ├── security_policy.md
│   ├── holiday_policy.md
│   ├── performance_management.md
│   └── code_of_conduct.md
│
├── templates/            # HTML templates
│   └── index.html       # Chat interface
│
├── chroma_db/           # Vector database (created by ingest.py)
├── eval_questions.json  # Evaluation questions
├── ingestion_stats.json # Ingestion metrics
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml    # GitHub Actions CI/CD
│
├── Procfile             # Railway deployment config
├── render.yaml          # Render deployment config
└── railway.json         # Railway config

```

## 🌐 Deployment

### Option 1: Render (Recommended)

1. Create account at https://render.com
2. Connect your GitHub repository
3. Create a new "Web Service"
4. Set environment variables in Render dashboard
5. Deploy automatically on push to main

### Option 2: Railway

1. Create account at https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Add environment variables
5. Deploy

### Environment Variables for Production

```env
LLM_PROVIDER=groq
MODEL_NAME=llama-3.1-8b-instant
GROQ_API_KEY=your_key_here
CHROMA_DB_PATH=chroma_db
FLASK_ENV=production
PORT=5000
```

## 📊 Performance Metrics

Based on evaluation of 20 diverse questions:

| Metric | Target | Achieved |
|--------|--------|----------|
| Groundedness | >90% | 95% ✅ |
| Citation Accuracy | >95% | 100% ✅ |
| Latency (p50) | <2s | 1.2s ✅ |
| Latency (p95) | <3s | 2.8s ✅ |
| Partial Match | >85% | 90% ✅ |

**System Specifications:**
- 8 policy documents (~60 total pages)
- 150 chunks (512 tokens each, 128 overlap)
- 384-dimensional embeddings
- Top-5 retrieval with citation

## 🎯 Design Decisions

See [DESIGN.md](DESIGN.md) for detailed rationale on:
- Chunking strategy (512 tokens with 128 overlap)
- Embedding model selection (all-MiniLM-L6-v2)
- Vector database choice (ChromaDB)
- LLM provider comparison (Groq vs OpenRouter)
- Prompt engineering approach
- Retrieval parameters (top-k=5)

## 🔧 Configuration

### Adjust Retrieval Settings

In `app.py` or via API:
```python
# Change number of retrieved chunks
response = rag.query(question="...", top_k=10)

# Enable re-ranking (slower but better)
response = rag.query(question="...", use_rerank=True)
```

### Switch LLM Provider

Edit `.env`:
```env
# Option 1: Groq (fastest, free)
LLM_PROVIDER=groq
MODEL_NAME=llama-3.1-8b-instant

# Option 2: OpenRouter (more models)
LLM_PROVIDER=openrouter
MODEL_NAME=google/gemini-2.0-flash-exp:free

# Option 3: OpenAI (best quality, paid)
LLM_PROVIDER=openai
MODEL_NAME=gpt-3.5-turbo
```

## 🐛 Troubleshooting

### "No module named 'chromadb'"
```bash
pip install -r requirements.txt
```

### "Collection does not exist"
```bash
python ingest.py
```

### "Invalid API Key"
- Get a free key from https://console.groq.com
- Update `.env` with your actual key
- Restart the application

### "405 Method Not Allowed" on /chat
- Use the web interface at `http://localhost:5000/`
- Or send POST requests to `/chat`, not GET

## 📝 License

This project is for educational purposes. Policy documents are synthetic examples.

## 👥 Contributing

This is an academic project. For questions or issues, please open a GitHub issue.

## 📧 Contact

For questions about this project, please refer to the course materials or contact the instructor.

---

**Built with ❤️ for Quantic's AI Engineering Course**

