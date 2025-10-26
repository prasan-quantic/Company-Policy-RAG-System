"""
RAG retrieval and generation module.
Handles query embedding, vector search, re-ranking, and LLM generation.
"""

import os
from typing import List, Dict, Any, Optional
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv
import torch

# Load environment variables
load_dotenv()


class RAGPipeline:
    def __init__(self,
                 db_path: str = "chroma_db",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 llm_provider: str = "openrouter",
                 model_name: str = "google/gemini-flash-1.5-8b",
                 top_k: int = 5):
        """
        Initialize RAG pipeline.

        Args:
            db_path: Path to ChromaDB
            embedding_model: Sentence-transformers model name
            llm_provider: LLM provider (openrouter, groq, openai)
            model_name: Model identifier
            top_k: Number of chunks to retrieve
        """
        self.db_path = db_path
        self.top_k = top_k
        self.llm_provider = llm_provider
        self.model_name = model_name
        self.embedding_model_name = embedding_model
        self.embedding_model = None

        # Initialize ChromaDB with new API
        self.client = chromadb.PersistentClient(path=db_path)

        try:
            self.collection = self.client.get_collection(name="company_policies")
            print(f"✅ Loaded existing collection with {self.collection.count()} chunks")
        except Exception as e:
            # Collection doesn't exist - create it and re-ingest
            print(f"⚠️  Collection not found: {e}")
            print(f"🔄 Creating new collection and re-ingesting documents...")
            try:
                from ingest import DocumentIngestion
                ingestion = DocumentIngestion(
                    docs_path="documents",
                    db_path=db_path,
                    embedding_model=embedding_model,
                    chunk_size=500,
                    chunk_overlap=50
                )
                stats = ingestion.ingest_documents()
                print(f"✅ Ingestion complete: {stats['total_chunks']} chunks indexed")

                # Now get the collection
                self.collection = self.client.get_collection(name="company_policies")
                print(f"✅ Collection loaded with {self.collection.count()} chunks")
            except Exception as ingest_error:
                raise Exception(f"Failed to create and ingest collection: {ingest_error}")

        # Initialize LLM client
        self._init_llm_client()

    def _load_embedding_model(self):
        """Lazy load embedding model to avoid startup timeout."""
        if self.embedding_model is None:
            print(f"⏳ Loading embedding model: {self.embedding_model_name}")
            # Use CPU and optimize for memory
            device = 'cpu'
            self.embedding_model = SentenceTransformer(
                self.embedding_model_name,
                device=device
            )
            # Set to eval mode to save memory
            self.embedding_model.eval()
            print(f"✅ Embedding model loaded on {device}")
        return self.embedding_model

    def _init_llm_client(self):
        """Initialize LLM API client based on provider."""
        if self.llm_provider == "openrouter":
            self.llm_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY", "")
            )
        elif self.llm_provider == "groq":
            self.llm_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY", "")
            )
        elif self.llm_provider == "openai":
            self.llm_client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", "")
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for query.

        Args:
            query: User question
            top_k: Number of chunks to retrieve (overrides default)

        Returns:
            List of retrieved chunks with metadata
        """
        k = top_k or self.top_k

        # Lazy load embedding model on first use
        model = self._load_embedding_model()

        # Embed query
        query_embedding = model.encode([query])[0].tolist()

        # Search vector database
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )

        # Format results
        chunks = []
        for i in range(len(results['ids'][0])):
            chunks.append({
                'chunk_id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })

        return chunks

    def rerank_chunks(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simple re-ranking based on keyword overlap (optional enhancement).
        For production, use cross-encoder models.
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for chunk in chunks:
            text_lower = chunk['text'].lower()
            text_terms = set(text_lower.split())

            # Calculate overlap score
            overlap = len(query_terms & text_terms)
            chunk['rerank_score'] = overlap

        # Sort by rerank score (descending)
        chunks.sort(key=lambda x: x['rerank_score'], reverse=True)

        return chunks

    def build_prompt(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Build prompt with retrieved context and guardrails.

        Args:
            query: User question
            chunks: Retrieved document chunks

        Returns:
            Formatted prompt string
        """
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            doc_id = chunk['metadata']['doc_id']
            title = chunk['metadata']['title']
            text = chunk['text']

            context_parts.append(
                f"[Source {i}: {doc_id} - {title}]\n{text}\n"
            )

        context = "\n".join(context_parts)

        # Build prompt with guardrails
        prompt = f"""You are a helpful assistant that answers questions about company policies based ONLY on the provided policy documents.

INSTRUCTIONS:
1. Answer the question using ONLY information from the provided sources below
2. If the answer is not in the sources, say "I can only answer questions about our company policies, and I don't have information about that in the policy documents."
3. ALWAYS cite your sources using the format [Source X] where X is the source number
4. Keep your answer concise (under 200 words unless more detail is needed)
5. If multiple policies apply, cite all relevant sources
6. Do not make up information or use external knowledge

POLICY SOURCES:
{context}

QUESTION: {query}

ANSWER (with citations):"""

        return prompt

    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
        """
        Generate answer using LLM.

        Args:
            prompt: Formatted prompt with context
            max_tokens: Maximum response length
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Generated answer text
        """
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions about company policies based on provided documents."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
            )

            answer = response.choices[0].message.content.strip()
            return answer

        except Exception as e:
            return f"Error generating response: {str(e)}"

    def query(self,
              question: str,
              top_k: Optional[int] = None,
              use_rerank: bool = False) -> Dict[str, Any]:
        """
        Complete RAG pipeline: retrieve, optionally rerank, and generate.

        Args:
            question: User question
            top_k: Number of chunks to retrieve
            use_rerank: Whether to apply re-ranking

        Returns:
            Dictionary with answer, sources, and metadata
        """
        # Retrieve relevant chunks
        chunks = self.retrieve(question, top_k)

        if not chunks:
            return {
                'answer': "I couldn't find any relevant information in the policy documents.",
                'sources': [],
                'question': question
            }

        # Optional re-ranking
        if use_rerank:
            chunks = self.rerank_chunks(question, chunks)

        # Build prompt
        prompt = self.build_prompt(question, chunks)

        # Generate answer
        answer = self.generate(prompt)

        # Format sources
        sources = []
        for i, chunk in enumerate(chunks, 1):
            sources.append({
                'source_num': i,
                'doc_id': chunk['metadata']['doc_id'],
                'title': chunk['metadata']['title'],
                'text_snippet': chunk['text'][:300] + "..." if len(chunk['text']) > 300 else chunk['text'],
                'full_text': chunk['text']
            })

        return {
            'answer': answer,
            'sources': sources,
            'question': question,
            'num_sources': len(sources)
        }


def main():
    """Test RAG pipeline."""
    import json

    # Initialize pipeline
    rag = RAGPipeline(
        db_path="chroma_db",
        embedding_model="all-MiniLM-L6-v2",
        llm_provider="openrouter",
        model_name="google/gemini-flash-1.5-8b",
        top_k=5
    )

    # Test queries
    test_queries = [
        "How many days of PTO do I get?",
        "Can I work remotely?",
        "What is the expense reimbursement limit for meals?",
        "What holidays does the company observe?",
        "What are the password requirements?"
    ]

    print("\n" + "="*60)
    print("Testing RAG Pipeline")
    print("="*60)

    for query in test_queries:
        print(f"\n📝 Question: {query}")
        result = rag.query(query, use_rerank=False)
        print(f"\n💡 Answer:\n{result['answer']}")
        print(f"\n📚 Sources: {result['num_sources']} documents referenced")
        print("-"*60)


if __name__ == "__main__":
    main()
"""
Document ingestion and indexing module for RAG system.
Parses documents, chunks them, generates embeddings, and stores in vector database.
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from sentence_transformers import SentenceTransformer
import markdown
from bs4 import BeautifulSoup
from pypdf import PdfReader

class DocumentIngestion:
    def __init__(self,
                 docs_path: str = "documents",
                 db_path: str = "chroma_db",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 500,
                 chunk_overlap: int = 50):
        """
        Initialize document ingestion system.

        Args:
            docs_path: Path to documents directory
            db_path: Path to store ChromaDB
            embedding_model: Name of sentence-transformers model
            chunk_size: Target size for document chunks (in words)
            chunk_overlap: Overlap between chunks (in words)
        """
        self.docs_path = Path(docs_path)
        self.db_path = db_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize embedding model
        print(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # Initialize ChromaDB with new API
        self.client = chromadb.PersistentClient(path=db_path)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="company_policies",
            metadata={"description": "Company policy documents"}
        )

    def parse_markdown(self, file_path: Path) -> Dict[str, Any]:
        """Parse markdown file and extract content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Convert markdown to HTML then extract text
        html = markdown.markdown(content)
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()

        # Extract document ID and title from content
        lines = content.split('\n')
        title = lines[0].strip('# ') if lines else file_path.stem
        doc_id = None

        for line in lines[:20]:  # Check first 20 lines
            if 'Document ID:' in line:
                doc_id = line.split('Document ID:')[1].strip().replace('**', '')
                break

        if not doc_id:
            doc_id = file_path.stem.upper()

        return {
            'title': title,
            'doc_id': doc_id,
            'content': text,
            'file_path': str(file_path),
            'format': 'markdown'
        }

    def parse_txt(self, file_path: Path) -> Dict[str, Any]:
        """Parse plain text file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            'title': file_path.stem.replace('_', ' ').title(),
            'doc_id': file_path.stem.upper(),
            'content': content,
            'file_path': str(file_path),
            'format': 'text'
        }

    def parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Parse PDF file."""
        content = []
        with open(file_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            for page in pdf_reader.pages:
                content.append(page.extract_text())

        return {
            'title': file_path.stem.replace('_', ' ').title(),
            'doc_id': file_path.stem.upper(),
            'content': '\n'.join(content),
            'file_path': str(file_path),
            'format': 'pdf'
        }

    def parse_html(self, file_path: Path) -> Dict[str, Any]:
        """Parse HTML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        title = soup.find('title')
        title = title.get_text() if title else file_path.stem

        return {
            'title': title,
            'doc_id': file_path.stem.upper(),
            'content': text,
            'file_path': str(file_path),
            'format': 'html'
        }

    def parse_document(self, file_path: Path) -> Dict[str, Any]:
        """Parse document based on file extension."""
        ext = file_path.suffix.lower()

        if ext == '.md':
            return self.parse_markdown(file_path)
        elif ext == '.txt':
            return self.parse_txt(file_path)
        elif ext == '.pdf':
            return self.parse_pdf(file_path)
        elif ext in ['.html', '.htm']:
            return self.parse_html(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller pieces with overlap.
        Uses word-based chunking with heading awareness.
        """
        chunks = []
        words = text.split()

        # Simple word-based chunking
        start = 0
        chunk_id = 0

        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)

            # Create unique chunk ID
            chunk_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]

            chunks.append({
                'text': chunk_text,
                'chunk_id': f"{metadata['doc_id']}_chunk_{chunk_id}_{chunk_hash}",
                'chunk_index': chunk_id,
                'doc_id': metadata['doc_id'],
                'title': metadata['title'],
                'file_path': metadata['file_path']
            })

            chunk_id += 1
            start = end - self.chunk_overlap

        return chunks

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate embeddings for text chunks."""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()

    def ingest_documents(self) -> Dict[str, Any]:
        """
        Main ingestion pipeline: parse all documents, chunk, embed, and store.
        """
        print(f"Starting document ingestion from {self.docs_path}")

        # Find all supported documents
        supported_exts = ['.md', '.txt', '.pdf', '.html', '.htm']
        doc_files = [f for f in self.docs_path.iterdir()
                     if f.is_file() and f.suffix.lower() in supported_exts]

        print(f"Found {len(doc_files)} documents to process")

        all_chunks = []
        stats = {
            'total_docs': len(doc_files),
            'total_chunks': 0,
            'documents': []
        }

        for doc_file in doc_files:
            print(f"\nProcessing: {doc_file.name}")

            try:
                # Parse document
                doc_data = self.parse_document(doc_file)
                print(f"  - Title: {doc_data['title']}")
                print(f"  - Doc ID: {doc_data['doc_id']}")
                print(f"  - Content length: {len(doc_data['content'])} chars")

                # Chunk document
                chunks = self.chunk_text(doc_data['content'], doc_data)
                print(f"  - Created {len(chunks)} chunks")

                all_chunks.extend(chunks)

                stats['documents'].append({
                    'file': doc_file.name,
                    'title': doc_data['title'],
                    'doc_id': doc_data['doc_id'],
                    'chunks': len(chunks)
                })
                stats['total_chunks'] += len(chunks)

            except Exception as e:
                print(f"  - ERROR: {str(e)}")
                continue

        if not all_chunks:
            print("No chunks created. Exiting.")
            return stats

        print(f"\n{'='*60}")
        print(f"Total chunks to embed: {len(all_chunks)}")
        print("Generating embeddings...")

        # Generate embeddings
        embeddings = self.embed_chunks(all_chunks)

        print("Storing in vector database...")

        # Prepare data for ChromaDB
        ids = [chunk['chunk_id'] for chunk in all_chunks]
        documents = [chunk['text'] for chunk in all_chunks]
        metadatas = [{
            'doc_id': chunk['doc_id'],
            'title': chunk['title'],
            'file_path': chunk['file_path'],
            'chunk_index': chunk['chunk_index']
        } for chunk in all_chunks]

        # Store in ChromaDB (batch if large)
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
            print(f"  - Stored batch {i//batch_size + 1}/{(len(ids)-1)//batch_size + 1}")

        print(f"\n{'='*60}")
        print("Ingestion complete!")
        print(f"Total documents: {stats['total_docs']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Vector DB location: {self.db_path}")

        return stats


def main():
    """Run document ingestion."""
    import json

    # Set random seed for reproducibility
    import random
    import numpy as np
    random.seed(42)
    np.random.seed(42)

    # Initialize and run ingestion
    ingestion = DocumentIngestion(
        docs_path="documents",
        db_path="chroma_db",
        embedding_model="all-MiniLM-L6-v2",
        chunk_size=500,  # words
        chunk_overlap=50
    )

    stats = ingestion.ingest_documents()

    # Save stats
    with open('ingestion_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)

    print("\nStats saved to ingestion_stats.json")


if __name__ == "__main__":
    main()
