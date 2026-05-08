from typing import Dict, List
from ddgs import DDGS
import requests
import trafilatura

HEADERS = {
    "User-Agent": "WikipediaAIChat/0.2 (local learning project)"
}


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the public web using DuckDuckGo via ddgs.
    Returns title, URL, and snippet.
    """
    results = []

    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                title = item.get("title", "").strip()
                url = item.get("href", "").strip()
                snippet = item.get("body", "").strip()

                if title and url:
                    results.append(
                        {
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "source_type": "web",
                            "matched_query": query,
                        }
                    )
    except Exception as e:
        print(f"Web search failed for query '{query}': {e}")

    return results


def fetch_web_page(url: str, max_chars: int = 10000) -> Dict[str, str] | None:
    """
    Fetch and extract readable text from a webpage.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch webpage '{url}': {e}")
        return None

    try:
        extracted = trafilatura.extract(
            response.text,
            url=url,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
    except Exception as e:
        print(f"Failed to extract webpage text from '{url}': {e}")
        return None

    if not extracted:
        return None

    text = extracted.strip()
    if len(text) < 300:
        return None

    return {
        "url": url,
        "content": text[:max_chars],
    }


def retrieve_web_context(
    queries: List[str],
    results_per_query: int = 3,
    max_pages: int = 4,
) -> List[Dict[str, str]]:
    """
    Search the web, fetch readable page text, and return source dictionaries.
    """
    sources = []
    seen_urls = set()

    for query in queries:
        web_results = search_web(query, max_results=results_per_query)

        for result in web_results:
            url = result["url"]

            if url in seen_urls:
                continue

            fetched = fetch_web_page(url)
            if not fetched:
                continue

            sources.append(
                {
                    "title": result["title"],
                    "url": url,
                    "snippet": result.get("snippet", ""),
                    "content": fetched["content"],
                    "source_type": "web",
                    "matched_query": query,
                }
            )

            seen_urls.add(url)

            if len(sources) >= max_pages:
                return sources

    return sources