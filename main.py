import json
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)

Mode = Literal["answer", "explain", "quiz", "summarize", "path", "recommend"]

TASKS = {
    "answer": "Answer the student's question directly and accurately. Be concise; explain any uncertainty.",
    "explain": "Teach this idea in clear language with a concrete example and a brief check for understanding.",
    "summarize": "Summarize the supplied passage faithfully. Keep the main ideas and omit unsupported claims.",
    "path": "Build a practical beginner-to-advanced learning path. Include a realistic timeline, milestones, practice, and a small project.",
    "recommend": "Recommend what this learner should study next, with a short reason and one practical next step.",
}


class StudyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    mode: Mode
    prompt: str = Field(min_length=2, max_length=12000)


class QuizQuestion(BaseModel):
    question: str
    choices: list[str] = Field(min_length=2, max_length=5)
    answer_index: int = Field(ge=0)
    explanation: str


class StudyResponse(BaseModel):
    mode: Mode
    content: str
    source: str
    quiz: list[QuizQuestion] | None = None


def _provider() -> str:
    return os.getenv("AI_PROVIDER", "offline").strip().lower()


def _quiz_prompt(topic: str) -> str:
    return (
        "Create three distinct multiple-choice questions about the student's topic. "
        "Return only a JSON array. Every item must have: question (string), choices "
        "(array of four strings), answer_index (zero-based integer), and explanation "
        f"(string). Topic: {topic}"
    )


def _parse_quiz(content: str) -> list[QuizQuestion]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end < start:
        raise ValueError("The AI response did not contain a quiz.")
    payload = json.loads(cleaned[start : end + 1])
    questions = [QuizQuestion.model_validate(item) for item in payload]
    if not questions or any(question.answer_index >= len(question.choices) for question in questions):
        raise ValueError("The AI returned an incomplete quiz.")
    return questions


def _offline_quiz(topic: str) -> list[QuizQuestion]:
    if re.search(r"pythag|right triangle", topic, re.I):
        questions = [
            (
                "Which equation expresses the Pythagorean theorem?",
                ["a² + b² = c²", "a + b = c", "a² − b² = c²", "2a + 2b = c"],
                0,
                "For a right triangle, the squares of the two legs add up to the square of the hypotenuse.",
            ),
            (
                "A right triangle has legs measuring 5 and 12. How long is its hypotenuse?",
                ["13", "17", "7", "12"],
                0,
                "5² + 12² = 25 + 144 = 169, and √169 = 13.",
            ),
            (
                "Which side is c in a² + b² = c²?",
                ["The hypotenuse", "The shortest leg", "Any side you choose", "The triangle's perimeter"],
                0,
                "The hypotenuse is opposite the right angle and is the longest side.",
            ),
        ]
    else:
        questions = [
            (
                f"What is a useful first step when studying {topic}?",
                ["Identify its key terms and central idea", "Skip definitions", "Memorize unrelated facts", "Avoid examples"],
                0,
                "Knowing the key terms and central idea gives new details a place to connect.",
            ),
            (
                f"Which approach helps you understand {topic} more deeply?",
                ["Explain an example in your own words", "Only reread the title", "Study without taking a break", "Avoid practice"],
                0,
                "Explaining an example in your own words makes understanding easier to check.",
            ),
            (
                f"How can you check your understanding of {topic}?",
                ["Try a new practice question without notes", "Look only at the headings", "Reread one sentence", "Skip the hard parts"],
                0,
                "A fresh practice question checks whether you can use what you have learned.",
            ),
        ]
    return [
        QuizQuestion(question=question, choices=choices, answer_index=answer_index, explanation=explanation)
        for question, choices, answer_index, explanation in questions
    ]


def _offline_text(mode: Mode, prompt: str) -> str:
    topic = prompt.strip().rstrip("?.!")
    normalized = topic.casefold()

    if mode == "answer":
        if "ocean" in normalized and ("largest" in normalized or "biggest" in normalized):
            return "The Pacific Ocean is the largest ocean on Earth, covering more area than all the land combined."
        if "ocean" in normalized:
            return "Earth has five oceans: the Pacific, Atlantic, Indian, Southern, and Arctic. The Pacific is the largest."
        if "pythag" in normalized:
            return "For a right triangle, the Pythagorean theorem is a² + b² = c², where c is the hypotenuse."
        return (
            f'Your question: “{topic}.” Offline mode cannot verify this fact yet. '
            "Connect an AI provider in .env for a topic-specific answer."
        )

    if mode == "explain":
        if "pythag" in normalized:
            return (
                "## The Pythagorean theorem\n\n"
                "In any right triangle, the two shorter sides (the legs) fit this rule: **a² + b² = c²**. "
                "The side across from the right angle is the hypotenuse, labelled **c**.\n\n"
                "**Example:** if the legs are 3 and 4, then c² = 3² + 4² = 25, so the hypotenuse is 5. "
                "It is like combining the areas of squares built on the two shorter sides to match the square on the longest side."
            )
        return (
            f"## {topic}\n\n"
            "Start by finding the central idea and its key terms. Next, connect each part to a concrete example, "
            "then try explaining that example in your own words. For a topic-specific explanation, connect an AI provider in .env."
        )

    if mode == "summarize":
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", topic) if sentence.strip()]
        if not sentences:
            return "Add a passage above to create a summary."
        excerpt = " ".join(sentences[:2])
        if len(sentences) > 2:
            excerpt += " …"
        return f"{excerpt}\n\n*Offline preview: connect an AI provider for a fuller, passage-aware summary.*"

    if mode in ("path", "recommend"):
        if "sql" in normalized:
            if mode == "path":
                return (
                    "## A practical SQL learning path\n\n"
                    "**Weeks 1–2 · Foundations** — Tables, rows, data types, `SELECT`, `WHERE`, and `ORDER BY`. "
                    "Practice: explore a small movie or book catalog.\n\n"
                    "**Weeks 3–4 · Combining data** — Aggregates, `GROUP BY`, `HAVING`, and `JOIN`. "
                    "Practice: answer questions across customers and orders.\n\n"
                    "**Weeks 5–6 · Intermediate** — Subqueries, common table expressions, `CASE`, and window functions. "
                    "Practice: calculate monthly trends and rankings.\n\n"
                    "**Weeks 7–8 · Advanced & project** — Indexes, query plans, transactions, and data modeling. "
                    "Project: design a small library database and write ten useful reports.\n\n"
                    "*Suggestion: aim for four short practice sessions each week, and explain each query before running it.*"
                )
            return (
                "## Your next SQL steps\n\n"
                "1. Practice `SELECT`, `WHERE`, and `ORDER BY` on a tiny sample database.\n"
                "2. Once those feel comfortable, join two tables and explain what each join keeps.\n"
                "3. Try one real-world question, like finding each month's busiest day.\n\n"
                "*Build one small query at a time; connect an AI provider for recommendations tailored to your progress.*"
            )
        return (
            f"## A path for {topic}\n\n"
            "**Start:** learn the core vocabulary and explain the main idea.\n\n"
            "**Build:** study one foundational concept at a time; after each, solve a short practice task.\n\n"
            "**Connect:** work through an applied example that combines the concepts.\n\n"
            "**Go deeper:** take on a small project, then revisit the concepts that were hardest. "
            "Set a pace that fits your week; connect an AI provider in .env for a topic-specific plan."
        )

    return f"Try {topic} next: write down one key idea, explain it in your own words, and solve a related practice question."


async def _ask_ai(mode: Mode, prompt: str) -> str:
    provider = _provider()
    system_prompt = (
        "You are EduGenie, a careful and encouraging educational assistant. "
        "Use concise, age-appropriate language, define jargon, and do not invent facts. "
        + TASKS.get(mode, "")
    )
    user_prompt = _quiz_prompt(prompt) if mode == "quiz" else prompt

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            if provider == "ollama":
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
                response = await client.post(
                    f"{base_url}/api/chat",
                    json={
                        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                    },
                )
                response.raise_for_status()
                return response.json()["message"]["content"]

            base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            api_key = os.getenv("AI_API_KEY", "")
            if provider == "openai" and not api_key:
                raise HTTPException(status_code=503, detail="Set AI_API_KEY in .env to use the OpenAI provider.")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": os.getenv("AI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.5,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    except HTTPException:
        raise
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The configured AI provider could not answer. Check its URL, credentials, and model, then try again.",
        ) from exc


@asynccontextmanager
async def lifespan(_: FastAPI):
    provider = _provider()
    if provider not in {"offline", "openai", "ollama"}:
        raise RuntimeError("AI_PROVIDER must be 'offline', 'openai', or 'ollama'.")
    yield


app = FastAPI(title="EduGenie", version="1.0.0", lifespan=lifespan)


@app.get("/")
async def home() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    provider = _provider()
    ready = provider != "openai" or bool(os.getenv("AI_API_KEY"))
    return {"status": "ok", "provider": provider, "ready": ready}


@app.post("/api/assistant", response_model=StudyResponse)
async def assistant(request: StudyRequest) -> StudyResponse:
    prompt = request.prompt
    if request.mode == "quiz":
        if _provider() == "offline":
            return StudyResponse(mode=request.mode, content=f"A quick check on {prompt.rstrip('.?!')}", source="offline", quiz=_offline_quiz(prompt))
        content = await _ask_ai(request.mode, prompt)
        try:
            questions = _parse_quiz(content)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=502, detail="The AI provider returned a quiz in an unreadable format. Please try again.") from exc
        return StudyResponse(mode=request.mode, content=f"A quick check on {prompt.rstrip('.?!')}", source=_provider(), quiz=questions)

    if _provider() == "offline":
        return StudyResponse(mode=request.mode, content=_offline_text(request.mode, prompt), source="offline")
    return StudyResponse(mode=request.mode, content=await _ask_ai(request.mode, prompt), source=_provider())


@app.get("/{asset_name}")
async def asset(asset_name: Literal["styles.css", "app.js"]) -> FileResponse:
    content_types = {"styles.css": "text/css", "app.js": "text/javascript"}
    return FileResponse(ROOT / "static" / asset_name, media_type=content_types[asset_name])