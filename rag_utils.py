import re
from typing import Dict, List


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 200) -> List[str]:
    """
    Simple character-based chunking.
    Good enough for this app without adding embeddings/vector DB complexity.
    """
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

        if start < 0:
            start = 0

        if start >= len(text):
            break

    return chunks


def score_chunk(question: str, query_terms: List[str], chunk: str, title: str = "") -> float:
    """
    Lightweight lexical scoring.
    Not as good as embeddings, but cheap, fast, and enough for a small demo.
    """
    question_tokens = tokenize(question)
    query_tokens = tokenize(" ".join(query_terms))
    chunk_tokens = tokenize(chunk)
    title_tokens = tokenize(title)

    question_overlap = len(question_tokens & chunk_tokens)
    query_overlap = len(query_tokens & chunk_tokens)
    title_overlap = len(question_tokens & title_tokens)

    return question_overlap * 2.0 + query_overlap * 1.0 + title_overlap * 2.5


def build_ranked_context(
    user_message: str,
    queries: List[str],
    sources: List[Dict[str, str]],
    max_chunks: int = 8,
) -> tuple[str, List[Dict[str, str]]]:
    """
    Convert source pages into ranked evidence chunks.
    Returns formatted context and citation-ready source list.
    """
    candidates = []

    for source in sources:
        chunks = chunk_text(source.get("content", ""))

        for chunk in chunks:
            score = score_chunk(
                question=user_message,
                query_terms=queries,
                chunk=chunk,
                title=source.get("title", ""),
            )

            candidates.append(
                {
                    "score": score,
                    "title": source.get("title", "Untitled"),
                    "url": source.get("url", ""),
                    "source_type": source.get("source_type", "unknown"),
                    "matched_query": source.get("matched_query", ""),
                    "content": chunk,
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected = candidates[:max_chunks]

    context_blocks = []
    citation_sources = []

    for index, item in enumerate(selected, start=1):
        citation_sources.append(
            {
                "title": item["title"],
                "url": item["url"],
                "source_type": item["source_type"],
            }
        )

        context_blocks.append(
            f"Source [{index}]\n"
            f"Title: {item['title']}\n"
            f"URL: {item['url']}\n"
            f"Source type: {item['source_type']}\n"
            f"Matched query: {item['matched_query']}\n"
            f"Content:\n{item['content']}"
        )

    return "\n\n---\n\n".join(context_blocks), citation_sources