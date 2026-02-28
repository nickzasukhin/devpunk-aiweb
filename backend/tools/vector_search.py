from langchain_core.tools import tool
from ingestion.embedder import search_similar


@tool
def search_company_knowledge(query: str) -> str:
    """Search DevPunks knowledge base for relevant information about the company, services, tech stack, and cases."""
    results = search_similar(query, top_k=5)
    if not results:
        return "No relevant information found."
    return "\n\n---\n\n".join(
        f"[Source: {r['filename']}]\n{r['text']}" for r in results
    )
