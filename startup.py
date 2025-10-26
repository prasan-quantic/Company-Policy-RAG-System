"""
Startup script for production deployment.
Ensures vector database is initialized before starting the web app.
"""

import os
import sys
from pathlib import Path

# Disable ChromaDB telemetry to prevent production errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Force ONNX to use CPU only to prevent GPU warnings
os.environ["ORT_DEVICE"] = "CPU"

import chromadb
from chromadb.config import Settings


def check_and_initialize_db():
    """Check if ChromaDB collection exists, create if not."""
    db_path = os.getenv("CHROMA_DB_PATH", "chroma_db")

    try:
        print("🔍 Checking vector database...")
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        try:
            collection = client.get_collection(name="company_policies")
            count = collection.count()
            if count > 0:
                print(f"✅ Vector database ready with {count} chunks")
                return True
            else:
                print("⚠️  Collection exists but is empty")
                return False
        except Exception:
            print("⚠️  Collection 'company_policies' not found")
            return False

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


def initialize_database():
    """Initialize vector database with documents."""
    print("🔄 Initializing vector database...")

    # Check if documents directory exists
    docs_path = Path("documents")
    if not docs_path.exists():
        print("❌ Documents directory not found!")
        return False

    # Check if there are documents
    doc_files = list(docs_path.glob("*.md")) + list(docs_path.glob("*.txt"))
    if not doc_files:
        print("❌ No documents found in documents directory!")
        return False

    print(f"📄 Found {len(doc_files)} documents")

    # Run ingestion
    try:
        from ingest import DocumentIngestion

        ingestion = DocumentIngestion(
            docs_path="documents",
            db_path=os.getenv("CHROMA_DB_PATH", "chroma_db"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            chunk_size=500,
            chunk_overlap=50
        )

        stats = ingestion.ingest_documents()

        if stats['total_chunks'] > 0:
            print(f"✅ Database initialized with {stats['total_chunks']} chunks")
            return True
        else:
            print("❌ No chunks were created")
            return False

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main startup function."""
    print("="*60)
    print("Starting Company Policy RAG System")
    print("="*60)

    # Check if database exists and is ready
    if not check_and_initialize_db():
        print("\n🔧 Database not ready, initializing...")
        if not initialize_database():
            print("\n❌ Failed to initialize database!")
            print("Please ensure documents are in the 'documents' directory")
            sys.exit(1)

    print("\n✅ Startup checks complete!")
    print("="*60)

    # Start gunicorn
    import subprocess
    port = os.environ.get('PORT', '10000')

    cmd = [
        'gunicorn',
        'app:app',
        '--bind', f'0.0.0.0:{port}',
        '--timeout', '300',
        '--workers', '1',
        '--worker-class', 'sync',
        '--max-requests', '100',
        '--max-requests-jitter', '10',
        '--preload'
    ]

    print(f"🚀 Starting gunicorn on port {port}...")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
