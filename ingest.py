"""
Document ingestion script for RAG system.
Run this script to load documents into ChromaDB.
"""

import os
import sys
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# Disable ChromaDB telemetry to prevent production errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Force ONNX to use CPU only to prevent GPU warnings
os.environ["ORT_DEVICE"] = "CPU"

import chromadb
from chromadb.config import Settings
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

        # Initialize ChromaDB with telemetry disabled
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="company_policies",
            metadata={"description": "Company policy documents"}
        )
        print("Created new collection: company_policies")

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

    def parse_document(self, file_path: Path) -> Dict[str, Any]:
        """Parse document based on file extension."""
        ext = file_path.suffix.lower()

        if ext == '.md':
            return self.parse_markdown(file_path)
        elif ext == '.txt':
            return self.parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller pieces with overlap.
        Uses word-based chunking.
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
        print(f"\nStarting document ingestion from {self.docs_path}")

        # Find all supported documents
        supported_exts = ['.md', '.txt']
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
                import traceback
                traceback.print_exc()
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
        print("✅ Ingestion complete!")
        print(f"Total documents: {stats['total_docs']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Vector DB location: {self.db_path}")

        return stats


def main():
    """Run document ingestion."""
    import json

    print("="*60)
    print("Document Ingestion Pipeline")
    print("="*60)

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

    print("\n📊 Stats saved to ingestion_stats.json")


if __name__ == "__main__":
    main()
