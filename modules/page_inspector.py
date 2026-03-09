# page_inspector.py
import streamlit as st
from rag_graph import create_graph
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma

def run():
    st.title("🧠 Agentic Page Inspector (LangGraph RAG)")

    url = st.text_input("Enter URL to analyze:", "")
    if st.button("🚀 Run LangGraph Agent") and url:
        with st.spinner("Running agentic inspection..."):
            graph = create_graph()
            result = graph.invoke({"url": url})

        if "summary" in result:
            st.subheader("🔍 Final Summary")
            st.text_area("AI Insight", result["summary"], height=300)

        if "inspection_notes" in result:
            st.subheader("🧪 Inspection Notes")
            for note in result["inspection_notes"]:
                st.markdown(f"- {note}")

        if "status" in result:
            st.markdown(f"**HTTP Status:** {result['status']}")
            st.markdown(f"**Redirects:** {result['redirects']}")