"""Quick script to check ingestion status."""
import os
import time

print("Checking ingestion status...")
print(f"ChromaDB folder exists: {os.path.exists('chroma_db')}")
print(f"Stats file exists: {os.path.exists('ingestion_stats.json')}")

if os.path.exists('chroma_db'):
    print(f"\nChromaDB folder contents:")
    for item in os.listdir('chroma_db'):
        print(f"  - {item}")

if os.path.exists('ingestion_stats.json'):
    import json
    with open('ingestion_stats.json', 'r', encoding='utf-8') as f:
        stats = json.load(f)
    print(f"\nIngestion Stats:")
    print(f"  Total documents: {stats['total_docs']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    print("\n✅ Ingestion completed successfully!")
else:
    print("\n⏳ Ingestion still in progress or not yet run...")
    print("The first run takes 2-3 minutes to download the embedding model.")
