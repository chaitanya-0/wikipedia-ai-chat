import os
import json
import re
from typing import List
from datetime import date
from dotenv import load_dotenv
from google import genai
from wikipedia_tool import retrieve_wikipedia_sources
from web_tool import retrieve_web_context
from rag_utils import build_ranked_context


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing. Check your .env file.")

client = genai.Client(api_key=api_key.strip())

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")


def extract_json_array(text: str) -> List[str]:
    """
    Gemini should return a JSON array, but models sometimes wrap it in text.
    This function safely extracts the JSON array.
    """

    text = text.strip()

    try:
        parsed = json.loads(text)

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[[\s\S]*\]", text)

    if not match:
        return []

    try:
        parsed = json.loads(match.group(0))

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        return []

    return []


def generate_wikipedia_queries(user_message: str) -> List[str]:
    """
    Turn the user's natural-language question into focused Wikipedia search queries.
    This is what makes the app much smarter.
    """

    prompt = f"""
You convert user questions into strong Wikipedia search queries.

Rules:
- Return ONLY a JSON array of strings.
- Do not include explanations.
- Create 3 to 5 search queries.
- Queries should be short and factual.
- Prefer Wikipedia-style article/search titles.
- Include alternate wording when useful.

Examples:

User question:
In World War 2, who faced the highest losses of soldiers?

Output:
[
  "World War II casualties",
  "World War II casualties by country",
  "World War II military deaths Soviet Union",
  "World War II casualties military deaths"
]

User question:
What were the causes of World War 2?

Output:
[
  "Causes of World War II",
  "World War II causes",
  "German invasion of Poland",
  "Treaty of Versailles World War II",
  "Rise of Nazi Germany"
]

User question:
{user_message}

Output:
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    queries = extract_json_array(response.text or "")

    cleaned_queries = []

    for query in queries:
        query = query.strip()

        if query and query.lower() not in [q.lower() for q in cleaned_queries]:
            cleaned_queries.append(query)

    # Fallback: if Gemini fails to generate clean JSON, use the original question.
    if not cleaned_queries:
        cleaned_queries = [user_message]

    # Keep the original user message as a fallback query, but do not let it dominate.
    if user_message.lower() not in [q.lower() for q in cleaned_queries]:
        cleaned_queries.append(user_message)

    return cleaned_queries[:4]


def ask_gemini_with_wikipedia(user_message: str) -> str:
    """
    Main RAG function:
    1. Generate search queries.
    2. Retrieve Wikipedia and web sources.
    3. Chunk and rank evidence.
    4. Ask Gemini to answer using only the selected evidence.
    """
    queries = generate_wikipedia_queries(user_message)

    wiki_sources = retrieve_wikipedia_sources(
        queries=queries,
        pages_per_query=2,
        max_pages=4,
    )

    web_sources = retrieve_web_context(
        queries=queries,
        results_per_query=3,
        max_pages=4,
    )

    all_sources = wiki_sources + web_sources

    if not all_sources:
        return "I could not find useful sources for this question."

    ranked_context, citation_sources = build_ranked_context(
        user_message=user_message,
        queries=queries,
        sources=all_sources,
        max_chunks=8,
    )

    source_list = "\n".join(
        [
            f"- [{index}] {source['title']}: {source['url']}"
            for index, source in enumerate(citation_sources, start=1)
        ]
    )

    prompt = f"""
You are a careful research assistant.

Your job is to answer the user's exact question using only the retrieved context below.

Rules:
- Do not use outside knowledge.
- Do not merely summarize the sources.
- Answer the exact question.
- If the evidence is weak or incomplete, say so directly.
- Use inline citations like [1], [2], [3].
- Only cite source numbers that appear in the provided context.
- Every major factual claim should have an inline citation.
- Do not create a References section. The backend will add it.
- Use markdown formatting.
- Be concise, but not vague.

User question:
{user_message}

Search queries used:
{json.dumps(queries, indent=2)}

Retrieved context:
{ranked_context}

Available sources:
{source_list}

Answer:
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    answer = (response.text or "").strip()

    if not answer:
        return "I could not generate an answer from the retrieved context."

    bibliography = build_bibliography(citation_sources)
    return answer + bibliography

def build_bibliography(sources) -> str:
    """
    Build a deterministic bibliography from the actual retrieved sources.
    This prevents Gemini from inventing sources.
    """
    if not sources:
        return ""

    retrieved_date = date.today().strftime("%B %d, %Y")
    bibliography_lines = ["\n\n## References"]

    for index, source in enumerate(sources, start=1):
        title = source.get("title", "Untitled source")
        url = source.get("url", "")
        source_type = source.get("source_type", "web")

        if source_type == "wikipedia":
            publisher = "Wikipedia"
            author = "Wikipedia contributors"
        else:
            publisher = "Web source"
            author = title

        if url:
            bibliography_lines.append(
                f"{index}. {author}. (n.d.). "
                f"*[{title}]({url})*. {publisher}. Retrieved {retrieved_date}."
            )
        else:
            bibliography_lines.append(
                f"{index}. {author}. (n.d.). "
                f"*{title}*. {publisher}. Retrieved {retrieved_date}."
            )

    return "\n".join(bibliography_lines)