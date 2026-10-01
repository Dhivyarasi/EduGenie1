# EduGenie

EduGenie is a small study assistant for asking questions, getting simpler explanations, taking a quick quiz, summarizing a passage, and planning what to study next. The FastAPI backend serves a responsive HTML/CSS/JavaScript dashboard and supports **offline sample responses**, a local **Ollama** model, or an **OpenAI-compatible** chat completion API.

## Set up

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000). The app starts in offline mode and needs no API key. Offline mode includes a Pythagorean-theorem quiz, an SQL learning path, and a short list of example answers; it identifies these answers as local previews rather than implying that an AI model is connected.

## Connect an AI provider

To use a locally running [Ollama](https://ollama.com/) model, pull a model and set the following values in `.env`:

```dotenv
AI_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

To use OpenAI, copy `.env.example`, then provide your API key:

```dotenv
AI_PROVIDER=openai
AI_API_KEY=your-api-key
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
```

Restart Uvicorn after changing provider settings. API keys are read only by the server and must not be put in the frontend.

## API

- `GET /api/health` reports the current provider and its configuration status.
- `POST /api/assistant` accepts `{"mode":"answer","prompt":"Which is the largest ocean?"}`. Modes: `answer`, `explain`, `quiz`, `summarize`, `path`, `recommend`.
- `GET /docs` opens the interactive FastAPI API documentation.

Quiz responses include multiple-choice questions, answer indexes, and explanations. On the dashboard, answers can be checked immediately and study notes saved to the current browser.

## Run tests

```bash
python -m unittest discover -s tests -v
```