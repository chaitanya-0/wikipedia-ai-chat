# Wikipedia AI Chat

Wikipedia AI Chat is a small Flask web app that answers user questions using Wikipedia context and Gemini. The app turns a natural-language question into focused Wikipedia search queries, retrieves relevant Wikipedia pages, sends that context to Gemini, and returns a concise answer with inline citations and a generated reference list.

## What it does

- Provides a browser-based chat interface.
- Accepts user questions through a `/chat` API endpoint.
- Uses Gemini to generate 3 to 5 focused Wikipedia search queries from the user's question.
- Searches Wikipedia through the MediaWiki API.
- Fetches plain-text Wikipedia article extracts and source URLs.
- Deduplicates retrieved pages before building the final context.
- Asks Gemini to answer using only the retrieved Wikipedia context.
- Returns markdown-formatted answers with inline citations and references.

## Tech stack

- Python
- Flask
- Google Gemini API through `google-genai`
- Wikipedia MediaWiki API
- Requests

## Project structure

```text
wikipedia-ai-chat/
├── app.py                 # Flask app and routes
├── gemini_service.py      # Gemini prompting, query generation, answer generation, references
├── wikipedia_tool.py      # Wikipedia search and page retrieval helpers
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Chat page template
├── static/
│   └── style.css          # Chat UI styling
└── .gitignore             # Ignores .env, cache files, virtual environments, editor files
```

## How the app works

1. The user opens the home page served by Flask.
2. The frontend sends the user's message to `POST /chat`.
3. `app.py` validates the request and passes the message to `ask_gemini_with_wikipedia()`.
4. `gemini_service.py` asks Gemini to convert the question into better Wikipedia search queries.
5. `wikipedia_tool.py` searches Wikipedia, fetches article extracts, deduplicates pages, and returns formatted context.
6. Gemini receives the original question, generated queries, Wikipedia context, and available sources.
7. The response is returned to the frontend as JSON.

## Requirements

Before running the app, you need:

- Python 3.10 or newer
- A Gemini API key
- Internet access for:
  - Gemini API calls
  - Wikipedia API requests

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/chaitanya-0/wikipedia-ai-chat.git
cd wikipedia-ai-chat
```

### 2. Create and activate a virtual environment

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Dependency note: the code imports `load_dotenv` from `dotenv`. If the install fails or `load_dotenv` cannot be imported, install the standard package explicitly:

```bash
pip install python-dotenv
```

You can also update `requirements.txt` by replacing `dotenv` with `python-dotenv`.

### 4. Create a `.env` file

Create a file named `.env` in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Do not commit this file. The repository already ignores `.env`.

### 5. Run the app

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## API usage

### `GET /`

Returns the chat UI.

### `POST /chat`

Sends a user message to the backend and returns an AI-generated answer.

Request body:

```json
{
  "message": "What caused World War II?"
}
```

Example with `curl`:

```bash
curl -X POST http://127.0.0.1:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What caused World War II?"}'
```

Successful response:

```json
{
  "answer": "Markdown-formatted answer with citations and references."
}
```

Error examples:

```json
{
  "error": "Missing message"
}
```

```json
{
  "error": "Empty message"
}
```

## Environment variables

| Variable | Required | Description |
|---|---:|---|
| `GEMINI_API_KEY` | Yes | API key used to call Gemini through `google-genai`. |

## Main files

### `app.py`

Creates the Flask app, serves the homepage, validates chat requests, calls the Gemini/Wikipedia service, and returns JSON responses.

### `gemini_service.py`

Handles the AI workflow:

- Loads the Gemini API key.
- Creates the Gemini client.
- Generates Wikipedia search queries.
- Builds the answer-generation prompt.
- Appends a deterministic references section based on retrieved sources.

### `wikipedia_tool.py`

Handles Wikipedia retrieval:

- Searches Wikipedia page titles.
- Fetches article extracts and canonical page URLs.
- Deduplicates pages.
- Formats retrieved article content into source blocks for Gemini.

### `templates/index.html`

Provides the browser chat interface.

### `static/style.css`

Styles the app shell, chat messages, composer, markdown output, loading state, and responsive layout.

## Troubleshooting

### `RuntimeError: GEMINI_API_KEY is missing. Check your .env file.`

Create a `.env` file in the project root and add:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Then restart the Flask app.
