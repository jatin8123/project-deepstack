import streamlit as st
import requests
import os

RAG_API_URL = os.getenv("RAG_API_URL", "http://rag-api-service:8080/api/query")

st.set_page_config(page_title="RAG Architecture Explorer", layout="wide")
st.title("🧠 RAG Architecture Explorer & Debugger")

question = st.text_input("Enter your enterprise question:", "What is the remote work policy?")
debug_mode = st.checkbox("Enable RAG Debug Mode (Expose Pipeline Step Details)", value=True)

if st.button("Submit Query"):
    with st.spinner("Executing RAG Pipeline..."):
        payload = {"question": question, "debug": debug_mode}
        try:
            res = requests.post(RAG_API_URL, json=payload).json()
            
            st.markdown("### 💬 Generated Answer")
            st.success(res.get("answer"))
            
            st.markdown("### 📑 Cited Sources")
            st.json(res.get("sources", []))
            
            if debug_mode and "debug_trace" in res:
                st.markdown("---")
                st.markdown("### 🔍 RAG Execution Trace")
                trace = res["debug_trace"]
                
                tab1, tab2 = st.tabs(["Retrieved & Reranked Chunks", "Final Constructed Prompt"])
                with tab1:
                    st.json(trace.get("reranked_top_chunks"))
                with tab2:
                    st.code(trace.get("final_prompt"), language="markdown")
        except Exception as e:
            st.error(f"Failed to reach RAG API: {e}")