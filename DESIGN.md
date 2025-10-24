# Design Documentation

## System Overview

This document outlines the architectural decisions, rationale, and tradeoffs for the Company Policy RAG System.

## 1. Architecture Design

### High-Level Architecture

```
User Query → Embedding → Vector Search → Context Retrieval → Prompt Building → LLM → Response
```

**Key Components:**
1. **Document Ingestion**: Parse, chunk, embed, and index documents
2. **Vector Database**: Store and retrieve document embeddings
3. **RAG Pipeline**: Orchestrate retrieval and generation
4. **Web Application**: User interface and API
5. **Evaluation Framework**: Measure system quality

### Design Principles

- **Modularity**: Each component (ingestion, retrieval, generation) is independent
- **Reproducibility**: Fixed seeds, deterministic chunking, version-locked dependencies
- **Observability**: Logging, metrics, health checks
- **Scalability**: Stateless design, batch processing support

## 2. Technology Stack Decisions

### 2.1 Embedding Model: all-MiniLM-L6-v2

**Choice**: Sentence-Transformers' `all-MiniLM-L6-v2`

**Rationale:**
- ✅ **Free & Local**: No API costs, runs on CPU
- ✅ **Fast**: 384-dimensional embeddings, ~6MB model size
- ✅ **Balanced Performance**: 58.8 on semantic similarity benchmarks
- ✅ **Production Ready**: Widely used, well-documented

**Alternatives Considered:**
- `all-mpnet-base-v2`: Better quality (63.3 score) but 3x slower
- OpenAI `text-embedding-3-small`: Excellent quality but API costs
- Cohere embeddings: Free tier but rate limited

**Tradeoffs:**
- Smaller model = faster inference but slightly lower quality
- CPU-based = no GPU requirement but slower than GPU alternatives
- Fixed 384 dims = good balance of expressiveness vs. memory

### 2.2 LLM Provider: OpenRouter (Free Tier)

**Choice**: OpenRouter with `meta-llama/llama-3.1-8b-instruct:free`

**Rationale:**
- ✅ **Zero Cost**: Free tier for testing and development
- ✅ **Flexibility**: Easy to switch models via API
- ✅ **Reliability**: Automatic failover, rate limit handling
- ✅ **Multiple Models**: Access to Llama, Gemini, Mistral

**Alternatives Considered:**
- **Groq**: Faster inference (300+ tokens/sec) but stricter rate limits
- **OpenAI**: Best quality but costs $0.50-$15 per 1M tokens
- **Local Models**: No API dependency but requires GPU

**Configuration:**
```python
LLM_PROVIDER=openrouter
MODEL_NAME=meta-llama/llama-3.1-8b-instruct:free
```

**Fallback Options:**
- Groq: `llama-3.1-8b-instant` (very fast)
- OpenRouter: `google/gemini-flash-1.5:free` (longer context)

### 2.3 Vector Database: ChromaDB

**Choice**: ChromaDB with DuckDB backend

**Rationale:**
- ✅ **Embedded Database**: No separate server required
- ✅ **Simple Setup**: `pip install chromadb` and ready
- ✅ **Persistence**: Data persists to disk automatically
- ✅ **Python Native**: First-class Python support
- ✅ **Lightweight**: Perfect for 150-200 chunks

**Alternatives Considered:**
- **Pinecone**: Cloud-hosted, great for production but requires signup
- **Weaviate**: Powerful but overkill for small corpus
- **FAISS**: Faster but no built-in metadata storage
- **Milvus**: Production-grade but complex setup

**Tradeoffs:**
- ChromaDB: Easy setup, good for <1M vectors, Python-first
- Pinecone: Better for production scale but cloud dependency
- FAISS: Faster search but manual metadata management

**Database Size:**
- 8 documents → ~150-200 chunks
- 384-dim embeddings × 200 chunks = ~300KB
- Metadata + text: ~2MB total

### 2.4 Web Framework: Flask

**Choice**: Flask for web application

**Rationale:**
- ✅ **Lightweight**: Minimal overhead for simple API
- ✅ **Flexible**: Easy to add custom endpoints
- ✅ **Well-Documented**: Large ecosystem
- ✅ **Production Ready**: Gunicorn/uWSGI support

**Alternatives Considered:**
- **Streamlit**: Faster prototyping but less control
- **FastAPI**: Modern, async, but overkill for this use case
- **Django**: Too heavy for simple API

## 3. Document Processing Strategy

### 3.1 Chunking Strategy

**Approach**: Fixed-size word-based chunking with overlap

**Parameters:**
- Chunk size: 500 words
- Overlap: 50 words (10%)
- Method: Simple word split

**Rationale:**
- **500 words**: Fits in context window, captures coherent ideas
- **50-word overlap**: Prevents information loss at boundaries
- **Word-based**: Simpler than token-based, language-agnostic

**Alternatives Considered:**
- **Semantic chunking**: Split by headings/sections (better structure but misses cross-section content)
- **Token-based**: More precise for LLM context but model-dependent
- **Sentence-based**: Natural boundaries but variable chunk sizes

**Example:**
```
Document: 5000 words
Chunks: ~11 chunks (500 words each, 50 overlap)
```

### 3.2 Document Parsing

**Supported Formats:**
- Markdown (`.md`) - primary format
- Plain text (`.txt`)
- PDF (`.pdf`) - via PyPDF2
- HTML (`.html`, `.htm`) - via BeautifulSoup

**Why Markdown Primary:**
- ✅ Human-readable source
- ✅ Easy to edit and maintain
- ✅ Preserves structure (headings, lists)
- ✅ Version control friendly
- ✅ No vendor lock-in

## 4. RAG Pipeline Design

### 4.1 Retrieval Strategy

**Method**: Dense retrieval with cosine similarity

**Parameters:**
- Top-k: 5 chunks
- Similarity metric: Cosine (default in ChromaDB)
- Re-ranking: Optional (keyword-based)

**Rationale:**
- **k=5**: Balance between context richness and prompt length
- **Cosine similarity**: Standard for sentence embeddings
- **No re-ranking by default**: Speed vs. marginal accuracy gain

**Retrieval Pipeline:**
```
Query → Embed → Vector Search → Top-5 Chunks → (Optional Re-rank) → Context
```

### 4.2 Prompt Engineering

**Prompt Structure:**
```
System Message: Role definition
Context: [Source 1] ... [Source 5]
Instructions: Guardrails, citation format
Question: User query
```

**Guardrails Implemented:**
1. **Scope Limitation**: "Answer ONLY based on provided sources"
2. **Citation Requirement**: "ALWAYS cite sources as [Source X]"
3. **Refusal Template**: "I can only answer about company policies..."
4. **Length Limit**: max_tokens=500
5. **Factuality Check**: "Do not make up information"

**Temperature: 0.3**
- Lower temperature → more deterministic
- Reduces hallucination risk
- Still allows natural language

### 4.3 Generation Parameters

```python
max_tokens=500       # ~400 words max response
temperature=0.3      # Deterministic, factual
top_p=0.9           # Nucleus sampling
```

## 5. Evaluation Methodology

### 5.1 Metrics

**Answer Quality (Required):**

1. **Groundedness (Target: >90%)**
   - Definition: Answer content is supported by retrieved evidence
   - Method: Word overlap heuristic (production: use NLI model)
   - Calculation: `overlap_ratio = shared_words / answer_words`

2. **Citation Accuracy (Target: >95%)**
   - Definition: Citations point to correct sources
   - Method: Regex extraction + validation
   - Checks: Citation numbers valid, sources exist

**System Metrics (Required):**

1. **Latency P50 (Target: <2000ms)**
   - Median response time
   - Includes: Embedding + retrieval + generation

2. **Latency P95 (Target: <4000ms)**
   - 95th percentile response time
   - Handles outliers

### 5.2 Test Set

**Size**: 30 questions

**Categories:**
- PTO (4 questions)
- Remote Work (3 questions)
- Expenses (4 questions)
- Security (5 questions)
- Benefits (6 questions)
- Performance (3 questions)
- Holidays (2 questions)
- Code of Conduct (3 questions)

**Question Types:**
- Factual retrieval (70%): "How many PTO days?"
- Policy clarification (20%): "Can I work remotely?"
- Multi-document (10%): "What happens when I leave?"

### 5.3 Baseline Performance

**Expected Results:**
- Groundedness: 85-95%
- Citation Accuracy: 95-100%
- Latency P50: 1000-2000ms
- Latency P95: 2000-4000ms

## 6. Scalability Considerations

### Current Scale
- Documents: 8 policies (~100 pages)
- Chunks: ~150-200
- Queries: <1000/day
- Cost: $0 (free tier)

### Scaling Strategy

**To 100 documents:**
- Same architecture works
- ChromaDB handles <100K chunks easily
- Consider batch processing for ingestion

**To 1000+ documents:**
- Move to Pinecone/Weaviate
- Add caching layer (Redis)
- Use async processing (Celery)
- Implement query queue

**To 10K+ queries/day:**
- Load balancer + multiple instances
- Cache frequent queries
- Use faster model (Groq)
- Add rate limiting

## 7. Cost Analysis

### Development Costs (Per 1000 Queries)

**Free Tier (Current Setup):**
- Embedding: $0 (local model)
- Vector DB: $0 (local ChromaDB)
- LLM: $0 (OpenRouter free tier)
- **Total: $0**

**Paid Tier (Production):**
- Embedding: $0.10 (Cohere API)
- Vector DB: $2.00 (Pinecone Starter)
- LLM: $5.00 (OpenAI GPT-3.5 or Groq)
- **Total: ~$7.10 per 1000 queries**

**Break-even**: Free tier sufficient for <10K queries/month

## 8. Security & Privacy

### Data Protection
- ✅ All data local (no cloud unless explicit)
- ✅ No PII in policy documents
- ✅ API keys in environment variables
- ✅ No logging of sensitive queries

### Access Control
- Web interface: No authentication (add Auth0/JWT for production)
- API: Add API key authentication
- Rate limiting: Add Flask-Limiter

### Compliance
- Documents are company-owned (legal to use)
- No external data processing (embeddings local)
- Audit trail: Add logging for production

## 9. Future Enhancements

### Short-term (MVP+)
1. **Better Re-ranking**: Use cross-encoder model
2. **Conversation Memory**: Multi-turn conversations
3. **Feedback Loop**: Thumbs up/down for answers
4. **Query Analytics**: Track popular questions

### Medium-term (V2)
1. **Hybrid Search**: Combine dense + sparse (BM25)
2. **Multi-lingual**: Support Spanish, Chinese
3. **Voice Interface**: Speech-to-text integration
4. **Admin Dashboard**: Usage analytics, document management

### Long-term (V3)
1. **Agentic RAG**: Tool use, multi-step reasoning
2. **Personalization**: Role-based answers
3. **Proactive Suggestions**: "You might want to know..."
4. **Integration**: Slack bot, Teams app

## 10. Lessons Learned

### What Worked Well
- Simple chunking strategy effective for structured docs
- Free tier APIs sufficient for development
- Local embeddings fast enough (<100ms)
- Flask simple and reliable

### What Could Be Improved
- Semantic chunking would preserve section context better
- Cross-encoder re-ranking would improve top-1 accuracy
- Streaming responses would improve UX
- Better error handling for API failures

### Production Readiness Gaps
- Add authentication
- Implement rate limiting
- Add monitoring (Prometheus/Grafana)
- Set up proper logging
- Add integration tests
- Implement caching layer

## 11. References

**Papers:**
- "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)
- "Dense Passage Retrieval for Open-Domain Question Answering" (Karpukhin et al., 2020)

**Libraries:**
- Sentence Transformers: https://www.sbert.net/
- ChromaDB: https://docs.trychroma.com/
- LangChain: https://python.langchain.com/

**Models:**
- all-MiniLM-L6-v2: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- Llama 3.1: https://ai.meta.com/llama/

---

**Document Version**: 1.0  
**Last Updated**: January 2025  
**Author**: [Your Name]
# Company Policy RAG System

A production-ready Retrieval-Augmented Generation (RAG) application that provides intelligent question-answering over company policy documents. Built with LangChain, ChromaDB, and Flask.

## 🎯 Features

- **Intelligent Document Search**: Vector similarity search over 8 comprehensive policy documents
- **Cited Answers**: Every answer includes source citations and snippets
- **Web Interface**: Beautiful, responsive chat interface
- **REST API**: Programmatic access via `/chat` endpoint
- **Guardrails**: Refuses to answer questions outside the policy corpus
- **Evaluation Framework**: Built-in metrics for groundedness and citation accuracy
- **Production Ready**: CI/CD pipeline, health checks, and deployment configuration

## 📚 Policy Documents

The system indexes the following company policies (~100 pages):

1. **PTO Policy** (POL-001) - Vacation, sick leave, accrual rates
2. **Remote Work Policy** (POL-002) - Hybrid schedules, equipment, eligibility
3. **Expense Reimbursement** (POL-003) - Travel, meals, submission procedures
4. **Information Security** (POL-004) - Passwords, access control, data protection
5. **Holiday Policy** (POL-005) - Observed holidays, floating days
6. **Code of Conduct** (POL-006) - Ethics, harassment, conflicts of interest
7. **Employee Benefits** (POL-007) - Health insurance, 401k, parental leave
8. **Performance Management** (POL-008) - Reviews, goals, promotions

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- 4GB RAM minimum
- Internet connection (for LLM API calls)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd AI
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
# Copy example env file
copy .env.example .env

# Edit .env and add your API key
# For free tier, use OpenRouter: https://openrouter.ai/keys
```

5. **Ingest documents**
```bash
python ingest.py
```

This will:
- Parse all policy documents
- Chunk them into ~500-word segments with 50-word overlap
- Generate embeddings using `all-MiniLM-L6-v2`
- Store in ChromaDB vector database

Expected output: ~150-200 chunks indexed

6. **Run the application**
```bash
python app.py
```

Access at: http://localhost:5000

## 📖 Usage

### Web Interface

1. Navigate to http://localhost:5000
2. Type your question in the input box
3. Receive answer with source citations and snippets
4. Click example questions for quick testing

### API Usage

**Chat Endpoint**
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many PTO days do I get?"}'
```

**Response:**
```json
{
  "answer": "Full-time employees accrue PTO based on years of service: [Source 1]...",
  "sources": [
    {
      "source_num": 1,
      "doc_id": "POL-001",
      "title": "Paid Time Off (PTO) Policy",
      "text_snippet": "..."
    }
  ],
  "question": "How many PTO days do I get?",
  "latency_ms": 1234
}
```

**Health Check**
```bash
curl http://localhost:5000/health
```

**List Documents**
```bash
curl http://localhost:5000/documents
```

## 🧪 Evaluation

Run the evaluation suite to measure system performance:

```bash
python evaluate.py
```

**Metrics Tracked:**

1. **Answer Quality**
   - **Groundedness**: % of answers supported by retrieved evidence
   - **Citation Accuracy**: % of answers with correct source attribution

2. **System Metrics**
   - **Latency P50/P95**: Response time percentiles
   - **Mean/Min/Max**: Latency statistics

**Sample Output:**
```
📊 Total Questions: 30

🎯 ANSWER QUALITY METRICS:
  Groundedness:      28/30 (93.3%)
  Citation Accuracy: 30/30 (100.0%)

⚡ SYSTEM METRICS:
  Latency P50:  1250ms
  Latency P95:  2100ms
```

Results saved to `evaluation_results.json`

## 🏗️ Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   Flask Web App     │
│   (app.py)          │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   RAG Pipeline      │
│   (rag.py)          │
├─────────────────────┤
│ 1. Embed Query      │
│ 2. Vector Search    │
│ 3. Build Prompt     │
│ 4. LLM Generation   │
└──────┬──────────────┘
       │
   ┌───┴───┐
   ▼       ▼
┌─────┐ ┌──────────┐
│Chroma│ │LLM API  │
│ DB  │ │(OpenRouter)│
└─────┘ └──────────┘
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHROMA_DB_PATH` | Vector database location | `chroma_db` |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `LLM_PROVIDER` | LLM provider (openrouter/groq/openai) | `openrouter` |
| `MODEL_NAME` | Model identifier | `meta-llama/llama-3.1-8b-instruct:free` |
| `TOP_K` | Number of chunks to retrieve | `5` |
| `PORT` | Web server port | `5000` |

### RAG Parameters

**Chunking Strategy:**
- Chunk size: 500 words
- Overlap: 50 words
- Method: Word-based with heading awareness

**Retrieval:**
- Top-k: 5 chunks
- Similarity metric: Cosine similarity
- Optional re-ranking available

**Generation:**
- Temperature: 0.3 (deterministic)
- Max tokens: 500
- Prompt includes guardrails and citation instructions

## 🧩 Project Structure

```
AI/
├── documents/              # Policy documents (8 .md files)
├── templates/             
│   └── index.html         # Web interface
├── app.py                 # Flask web application
├── rag.py                 # RAG pipeline implementation
├── ingest.py              # Document ingestion & indexing
├── evaluate.py            # Evaluation framework
├── eval_questions.json    # Test questions (30 questions)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── .gitignore            
├── README.md              # This file
├── DESIGN.md              # Design documentation
└── chroma_db/             # Vector database (created after ingestion)
```

## 🚀 Deployment

### Render (Recommended)

1. **Create `render.yaml`** (included in repo)

2. **Deploy to Render:**
   - Connect GitHub repository
   - Set environment variables in Render dashboard
   - Deploy automatically on push to main

3. **Set Environment Variables in Render:**
   - `OPENROUTER_API_KEY` or `GROQ_API_KEY`
   - `FLASK_ENV=production`
   - Other variables from `.env.example`

### Railway

1. **Create new project** on Railway
2. **Connect GitHub repository**
3. **Add environment variables**
4. **Deploy** - Railway auto-detects Python app

### Manual Deployment

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🔄 CI/CD

GitHub Actions workflow included (`.github/workflows/ci-cd.yml`):

**On Push/PR:**
- Install dependencies
- Run import checks
- Test app startup
- Run evaluation (on main branch)

**On Main Branch Success:**
- Auto-deploy to Render/Railway (via webhook)

## 📊 Design Decisions

See [DESIGN.md](DESIGN.md) for detailed rationale on:
- Embedding model selection
- Chunking strategy
- LLM provider choice
- Vector store comparison
- Prompt engineering approach

## 🛡️ Guardrails

The system implements several safety measures:

1. **Scope Limitation**: Refuses questions outside policy domain
2. **Citation Requirement**: Must cite sources for all claims
3. **Length Limits**: Responses capped at 500 tokens
4. **Factual Grounding**: Instructed to only use retrieved context
5. **Output Validation**: Checks for hallucination indicators

## 🐛 Troubleshooting

**"Collection not found" error:**
```bash
python ingest.py  # Re-run ingestion
```

**API errors:**
- Check API key in `.env`
- Verify API quota/limits
- Try alternative provider (Groq, OpenRouter)

**Slow responses:**
- Reduce `TOP_K` in `.env`
- Use faster model (e.g., `llama-3.1-8b-instant` on Groq)
- Consider local embedding model caching

**Empty/bad answers:**
- Check ingestion completed successfully
- Verify documents in `documents/` folder
- Review `ingestion_stats.json` for chunk counts

## 📝 Development

### Running Tests
```bash
# Test ingestion
python ingest.py

# Test RAG pipeline
python rag.py

# Run evaluation
python evaluate.py

# Test web app
python app.py
# Visit http://localhost:5000
```

### Adding New Documents

1. Add `.md`, `.txt`, `.pdf`, or `.html` file to `documents/`
2. Re-run ingestion: `python ingest.py`
3. Restart app: `python app.py`

### Customizing Prompts

Edit `build_prompt()` method in `rag.py` to adjust:
- System instructions
- Citation format
- Response length
- Answer style

## 📄 License

This is an academic project for educational purposes.

## 👥 Contributors

- Student: [Your Name]
- Course: AI Engineering
- Date: January 2025

## 🔗 Links

- **Live Demo**: [Your deployed URL]
- **Documentation**: See DESIGN.md
- **API Reference**: See `/health` and `/chat` endpoints above

## 📞 Support

For questions or issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Review evaluation results for system health
3. Check `/health` endpoint
4. Review application logs

---

**Built with**: Python • Flask • ChromaDB • LangChain • OpenRouter • Sentence Transformers

