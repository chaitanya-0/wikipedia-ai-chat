import requests
from typing import List, Dict, Tuple


WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": "WikipediaAIChat/0.1 (local learning project)"
}


def search_wikipedia_titles(query: str, limit: int = 5) -> List[str]:
    """
    Search Wikipedia and return matching page titles.
    This uses the official MediaWiki API instead of the brittle wikipedia package.
    """

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
        "utf8": 1,
    }

    response = requests.get(
        WIKIPEDIA_API_URL,
        params=params,
        headers=HEADERS,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    search_results = data.get("query", {}).get("search", [])

    return [item["title"] for item in search_results]


def fetch_wikipedia_page(title: str, max_chars: int = 12000) -> Dict[str, str] | None:
    """
    Fetch plain-text article content for a Wikipedia page title.
    """

    params = {
        "action": "query",
        "prop": "extracts|info",
        "explaintext": 1,
        "exsectionformat": "plain",
        "inprop": "url",
        "redirects": 1,
        "titles": title,
        "format": "json",
        "utf8": 1,
    }

    response = requests.get(
        WIKIPEDIA_API_URL,
        params=params,
        headers=HEADERS,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    for _, page in pages.items():
        if "missing" in page:
            return None

        content = page.get("extract", "").strip()

        if not content:
            return None

        return {
            "title": page.get("title", title),
            "url": page.get("fullurl", ""),
            "content": content[:max_chars],
        }

    return None


def retrieve_wikipedia_context(
    queries: List[str],
    pages_per_query: int = 3,
    max_pages: int = 8,
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Search Wikipedia using multiple queries, fetch pages, deduplicate them,
    and return formatted context for Gemini.
    """

    sources = []
    seen_titles = set()

    for query in queries:
        try:
            titles = search_wikipedia_titles(query, limit=pages_per_query)
        except Exception as e:
            print(f"Wikipedia title search failed for query '{query}': {e}")
            continue

        for title in titles:
            title_key = title.lower().strip()

            if title_key in seen_titles:
                continue

            try:
                page = fetch_wikipedia_page(title)
            except Exception as e:
                print(f"Wikipedia page fetch failed for title '{title}': {e}")
                continue

            if not page:
                continue

            page["matched_query"] = query

            sources.append(page)
            seen_titles.add(title_key)

            if len(sources) >= max_pages:
                break

        if len(sources) >= max_pages:
            break

    if not sources:
        return "No useful Wikipedia results found.", []

    context_blocks = []

    for index, source in enumerate(sources, start=1):
        context_blocks.append(
            f"Source [{index}]\n"
            f"Title: {source['title']}\n"
            f"URL: {source['url']}\n"
            f"Matched query: {source['matched_query']}\n"
            f"Content:\n{source['content']}"
        )

    context = "\n\n---\n\n".join(context_blocks)

    return context, sources