import streamlit as st
from rag_graph import create_graph

def run():
    st.title("🧠 Agentic Page Inspector (LangGraph RAG)")

    url = st.text_input("Enter URL to analyze:", "").strip()
print("RETRIEVER_INVOKE_ACTIVE")
    if st.button("🚀 Run LangGraph Agent"):
        if not url:
            st.warning("Please enter a URL.")
            return

        with st.spinner("Running agentic inspection..."):
            try:
                graph = create_graph()
                result = graph.invoke({"url": url})
            except Exception as e:
                st.error(f"Failed to run inspector: {e}")
                return

        if result.get("summary"):
            st.subheader("🔍 Final Summary")
            st.text_area("AI Insight", result["summary"], height=300)

        if result.get("inspection_notes"):
            st.subheader("🧪 Inspection Notes")
            for note in result["inspection_notes"]:
                st.markdown(f"- {note}")

        if result.get("status") is not None:
            st.markdown(f"**HTTP Status:** {result['status']}")

        if result.get("redirects") is not None:
            st.markdown(f"**Redirects:** {result['redirects']}")

        if result.get("final_url"):
            st.markdown(f"**Final URL:** {result['final_url']}")

        if result.get("robots_allowed") is not None:
            st.markdown(f"**robots.txt allows fetch:** {result['robots_allowed']}")

        if result.get("error"):
            st.error(f"Error: {result['error']}")
