from fastapi import FastAPI
import requests
import chromadb
import os

app = FastAPI(title="RAG Learning API")

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb-service")
EMBEDDING_ENDPOINT = os.getenv("EMBEDDING_ENDPOINT")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
RERANKER_ENDPOINT = os.getenv("RERANKER_ENDPOINT")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
LLM_API_KEY = os.getenv("LLM_API_KEY")
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", 10))
TOP_K_RERANK = int(os.getenv("TOP_K_RERANK", 3))

def get_chroma_client():
    return chromadb.HttpClient(host=CHROMA_HOST, port=8000)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/query")
def process_query(payload: dict):
    user_query = payload.get("question", "")
    debug = payload.get("debug", False)
    
    # 1. Generate Query Embedding
    headers = {"Authorization": f"Bearer {EMBEDDING_API_KEY}"}
    emb_resp = requests.post(EMBEDDING_ENDPOINT, json={"input": user_query}, headers=headers).json()
    query_vector = emb_resp["data"][0]["embedding"]
    
    # 2. Vector Retrieval (ChromaDB)
    client = get_chroma_client()
    collection = client.get_or_create_collection("enterprise_docs")
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=TOP_K_RETRIEVAL,
        include=["documents", "metadatas", "distances"]
    )
    
    candidates = []
    if results["documents"]:
        for i in range(len(results["documents"][0])):
            candidates.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
            
    # 3. Optional Reranking Stage
    top_chunks = candidates[:TOP_K_RERANK]
    if RERANKER_ENDPOINT and candidates:
        try:
            rr_resp = requests.post(
                RERANKER_ENDPOINT, 
                json={"query": user_query, "documents": [c["text"] for c in candidates]}
            ).json()
            for idx, score in enumerate(rr_resp.get("scores", [])):
                candidates[idx]["rerank_score"] = score
            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            top_chunks = candidates[:TOP_K_RERANK]
        except Exception:
            pass # Fallback to standard vector similarity if reranker fails
            
    # 4. Context Assembly & Prompt Construction
    context = "\n\n".join([f"Source ({c['metadata'].get('document_name','unknown')}):\n{c['text']}" for c in top_chunks])
    prompt = f"""You are an enterprise AI assistant. Answer the user question using ONLY the context provided below.

CONTEXT:
{context}

QUESTION:
{user_query}

ANSWER:"""

    # 5. LLM Call
    llm_headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    llm_payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    llm_resp = requests.post(LLM_ENDPOINT, json=llm_payload, headers=llm_headers).json()
    answer = llm_resp["choices"][0]["message"]["content"]
    
    response = {
        "answer": answer,
        "sources": list(set([c["metadata"].get("document_name", "unknown") for c in top_chunks]))
    }
    
    if debug:
        response["debug_trace"] = {
            "retrieved_candidates": candidates,
            "reranked_top_chunks": top_chunks,
            "final_prompt": prompt
        }
        
    return response