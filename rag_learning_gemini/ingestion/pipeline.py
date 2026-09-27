import os
import glob
import requests
import chromadb
from docling.document_converter import DocumentConverter

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb-service")
EMBEDDING_ENDPOINT = os.getenv("EMBEDDING_ENDPOINT")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
DATA_DIR = os.getenv("DATA_DIR", "/app/sample-data")

def embed_text(text: str) -> list:
    headers = {"Authorization": f"Bearer {EMBEDDING_API_KEY}"}
    resp = requests.post(EMBEDDING_ENDPOINT, json={"input": text}, headers=headers).json()
    return resp["data"][0]["embedding"]

def run_ingestion():
    print(f"Starting Ingestion from {DATA_DIR}...")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
    collection = client.get_or_create_collection("enterprise_docs")
    converter = DocumentConverter()
    
    files = glob.glob(f"{DATA_DIR}/*.*")
    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"Parsing document: {filename}")
        
        # 1. Parsing via Docling
        result = converter.convert(filepath)
        markdown_text = result.document.export_to_markdown()
        
        # 2. Chunking (500-word sliding window)
        words = markdown_text.split()
        chunk_size = 500
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i+chunk_size])
            chunk_id = f"{filename}_chunk_{i // chunk_size}"
            
            # 3. Embedding Generation
            vector = embed_text(chunk_text)
            
            # 4. Write to Vector DB with Metadata
            collection.upsert(
                ids=[chunk_id],
                embeddings=[vector],
                documents=[chunk_text],
                metadatas=[{
                    "document_name": filename,
                    "chunk_index": i // chunk_size,
                    "source_path": filepath
                }]
            )
            print(f"  Ingested chunk {chunk_id}")
            
    print("Ingestion Pipeline Completed Successfully.")

if __name__ == "__main__":
    run_ingestion()