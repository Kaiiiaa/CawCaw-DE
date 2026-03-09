import os
import re
from typing import TypedDict, Optional, List
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

BLOCK_PATTERNS = [
    (r"captcha", "🚧 CAPTCHA detected."),
    (r"cf-browser-verification|cloudflare", "⚠️ Cloudflare challenge or block likely."),
    (r"access denied", "⛔ Access denied message detected."),
    (r"forbidden", "⛔ Forbidden message detected in page content."),
    (r"bot detection|automated queries|unusual traffic", "🤖 Anti-bot language detected."),
    (r"verify you are human|human verification", "👤 Human verification detected."),
    (r"temporarily unavailable", "🛠️ Temporary unavailability message detected."),
]

class RAGState(TypedDict):
    url: str
    html: Optional[str]
    status: Optional[int]
    redirects: Optional[int]
    final_url: Optional[str]
    robots_allowed: Optional[bool]
    robots_url: Optional[str]
    retry_after: Optional[str]
    server: Optional[str]
    content_type: Optional[str]
    inspection_notes: Optional[List[str]]
    context: Optional[str]
    summary: Optional[str]
    saved: Optional[bool]
    error: Optional[str]


def check_robots(url: str, user_agent: str = "*"):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    rp = RobotFileParser()
    rp.set_url(robots_url)

    try:
        rp.read()
        allowed = rp.can_fetch(user_agent, url)
        return {"robots_allowed": allowed, "robots_url": robots_url}
    except Exception:
        return {"robots_allowed": None, "robots_url": robots_url}


def fetch_page(state):
    url = state["url"]

    robots_info = check_robots(url, "*")

    try:
        session = requests.Session()
        resp = session.get(url, headers=HEADERS, timeout=15, allow_redirects=True)

        html = resp.text[:8000]
        return {
            "html": html,
            "status": resp.status_code,
            "redirects": len(resp.history),
            "final_url": resp.url,
            "retry_after": resp.headers.get("Retry-After"),
            "server": resp.headers.get("Server"),
            "content_type": resp.headers.get("Content-Type"),
            "robots_allowed": robots_info["robots_allowed"],
            "robots_url": robots_info["robots_url"],
            "error": None,
        }
    except Exception as e:
        return {
            "error": str(e),
            "html": "",
            "status": None,
            "redirects": 0,
            "final_url": None,
            "retry_after": None,
            "server": None,
            "content_type": None,
            "robots_allowed": robots_info["robots_allowed"],
            "robots_url": robots_info["robots_url"],
        }


def inspect_page(state):
    html = (state.get("html") or "").lower()
    notes = []

    status = state.get("status")
    redirects = state.get("redirects", 0)
    final_url = state.get("final_url")
    retry_after = state.get("retry_after")
    content_type = (state.get("content_type") or "").lower()
    robots_allowed = state.get("robots_allowed")

    if robots_allowed is False:
        notes.append(f"🛑 robots.txt appears to disallow scraping for this URL: {state.get('robots_url')}")
    elif robots_allowed is None:
        notes.append("❓ Could not reliably read robots.txt.")

    if status == 403:
        notes.append("⛔ HTTP 403 Forbidden returned. This usually means the server understood the request but refused it.")        
    if status == 429:
        msg = "⏳ HTTP 429 Too Many Requests detected."
        if retry_after:
            msg += f" Server asked clients to wait via Retry-After: {retry_after}."
        notes.append(msg)
    if status == 503:
        msg = "🛠️ HTTP 503 Service Unavailable detected."
        if retry_after:
            msg += f" Retry-After header present: {retry_after}."
        notes.append(msg)

    if redirects > 0:
        notes.append(f"🔁 Redirect chain detected ({redirects} redirects).")
    if final_url and final_url != state.get("url"):
        notes.append(f"↪️ Final URL differs from requested URL: {final_url}")

    if "text/html" not in content_type and content_type:
        notes.append(f"📄 Response content type is not normal HTML: {content_type}")

    if len(html.strip()) < 500:
        notes.append("❗ Very short HTML — possible soft block, consent page, or JS-only page.")

    if re.search(r"<meta[^>]+http-equiv=[\"']refresh[\"']", html):
        notes.append("🔄 Meta refresh detected — the page may redirect to an interstitial or challenge page.")

    if re.search(r"<noscript>.*enable javascript.*</noscript>", html, flags=re.DOTALL):
        notes.append("⚙️ Site appears to depend heavily on JavaScript.")

    if re.search(r"window\.__next_data__|id=[\"']__next[\"']", html):
        notes.append("🧩 Next.js markers detected — content may be app-rendered.")
    if re.search(r"ng-version|data-reactroot|__nuxt", html):
        notes.append("🧩 SPA framework markers detected — some content may load client-side.")

    for pattern, message in BLOCK_PATTERNS:
        if re.search(pattern, html):
            notes.append(message)

    workarounds = []

    if robots_allowed is False:
        workarounds.append("Respect robots.txt and look for an official API, feed, sitemap, or allowed endpoint instead.")
    if status in {429, 503}:
        workarounds.append("Slow request rate and honor Retry-After before retrying.")
    if status == 403:
        workarounds.append("Check whether the site requires authentication, cookies, or an approved API/integration.")
    if "javascript" in " ".join(notes).lower() or "spa" in " ".join(notes).lower():
        workarounds.append("Look for data embedded in script tags, JSON endpoints, sitemap.xml, or server-rendered category pages.")
    if len(html.strip()) < 500:
        workarounds.append("Compare the fetched HTML to a browser view; a consent wall, region gate, or soft block may be returning minimal HTML.")

    if workarounds:
        notes.append("Suggested next steps:")
        for item in dict.fromkeys(workarounds):
            notes.append(f"- {item}")

    return {"inspection_notes": notes}


def retrieve_rag_context(state):
    html = state.get("html") or ""
    if not html.strip():
        return {"context": ""}

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory="vectorstore",
        embedding_function=embeddings,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(html)
    return {"context": "\n\n".join(doc.page_content for doc in docs)}


def summarize_with_llm(state):
    context = state.get("context") or ""
    html = state.get("html") or ""
    notes = "\n".join(state.get("inspection_notes", []))
    status = state.get("status")
    robots_allowed = state.get("robots_allowed")
    retry_after = state.get("retry_after")
    final_url = state.get("final_url")

    prompt = f"""
You are a senior web scraping engineer.

Analyze this page fetch and explain:
1. whether the page appears scrapeable with normal HTTP requests,
2. which signs suggest blocking, rate limiting, robots restrictions, JS rendering, or interstitials,
3. the safest legitimate next steps,
4. whether an API, sitemap, feed, or embedded JSON should be explored before browser automation.

Observed metadata:
- Requested URL: {state.get('url')}
- Final URL: {final_url}
- HTTP status: {status}
- Robots allowed: {robots_allowed}
- Retry-After: {retry_after}

Inspection Findings:
{notes}

Reference Knowledge:
{context}

HTML Sample:
{html[:4000]}

Be concrete and practical. Do not recommend bypassing CAPTCHA or defeating anti-bot systems.
"""

    llm = ChatOpenAI(model="gpt-4", temperature=0)
    result = llm.invoke(prompt)
    return {"summary": result.content}


def save_to_vectorstore(state):
    summary = state.get("summary", "")
    url = state.get("url", "")
    notes = "\n".join(state.get("inspection_notes", []))
    status = state.get("status", "Unknown")

    metainfo = {
        "url": url,
        "status": status,
        "notes": notes,
    }

    vectorstore = Chroma(
        persist_directory="inspections_store",
        collection_name="page_inspections",
        embedding_function=OpenAIEmbeddings(),
    )
    vectorstore.add_texts([summary], metadatas=[metainfo])
    return {"saved": True}


def create_graph():
    builder = StateGraph(RAGState)

    builder.add_node("fetch", RunnableLambda(fetch_page))
    builder.add_node("inspect", RunnableLambda(inspect_page))
    builder.add_node("retrieve", RunnableLambda(retrieve_rag_context))
    builder.add_node("summarize", RunnableLambda(summarize_with_llm))
    builder.add_node("save", RunnableLambda(save_to_vectorstore))

    builder.set_entry_point("fetch")
    builder.add_edge("fetch", "inspect")
    builder.add_edge("inspect", "retrieve")
    builder.add_edge("retrieve", "summarize")
    builder.add_edge("summarize", "save")
    builder.add_edge("save", END)

    return builder.compile()

