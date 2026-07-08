"""
app.py — ModelSabha backend (FastAPI).

Three AI models debate your question, then a judge model delivers a verdict.
Every AI call routes through the Mesh API via mesh_client.py.

Run it:
    uvicorn app:app --reload
Then open http://127.0.0.1:8000
"""

import json
import re

from dotenv import load_dotenv

load_dotenv()  # read .env BEFORE importing mesh_client (it reads env vars)

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import mesh_client
import prompts

app = FastAPI(title="ModelSabha", version="1.0.0")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# The default council. Verify these ids exist on your key with GET /v1/models
# (the frontend does this automatically and falls back to this list).
DEFAULT_PANEL = [
    "openai/gpt-4o-mini",
    "anthropic/claude-haiku-4.5",
    "google/gemini-2.5-flash",
]
DEFAULT_JUDGE = "anthropic/claude-sonnet-4.6"

MAX_QUESTION_LEN = 1000

# ---------------------------------------------------------------------------
# Request/response models (Pydantic validates input for us)
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=MAX_QUESTION_LEN)
    models: list[str] = Field(min_length=2, max_length=4)


class ModelTurn(BaseModel):
    model: str
    content: str


class CritiqueRequest(BaseModel):
    question: str = Field(min_length=5, max_length=MAX_QUESTION_LEN)
    answers: list[ModelTurn] = Field(min_length=2, max_length=4)


class VerdictRequest(BaseModel):
    question: str
    answers: list[ModelTurn]
    critiques: list[ModelTurn]
    judge: str = DEFAULT_JUDGE


# ---------------------------------------------------------------------------
# API routes — one per debate stage, so the UI can animate progress
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    """Lets the UI warn early if the Mesh key is missing."""
    return {"ok": True, "mesh_key_configured": bool(mesh_client.MESH_API_KEY)}


@app.get("/api/models")
async def models():
    """
    Return models available on this Mesh key, so dropdowns show real options.
    Falls back to DEFAULT_PANEL if the call fails (e.g. offline demo).
    """
    try:
        available = await mesh_client.list_models()
        return {"models": available or DEFAULT_PANEL, "live": bool(available)}
    except Exception:
        return {"models": DEFAULT_PANEL + [DEFAULT_JUDGE], "live": False}


@app.post("/api/answers")
async def stage1_answers(req: AskRequest):
    """STAGE 1 — every council member answers independently, in parallel."""
    jobs = [
        {"model": m, "messages": prompts.opening_messages(req.question)}
        for m in req.models
    ]
    results = await mesh_client.chat_many(jobs)
    _fail_if_all_failed(results)
    return {"answers": results}


@app.post("/api/critiques")
async def stage2_critiques(req: CritiqueRequest):
    """STAGE 2 — each model reads its PEERS' answers and cross-examines them."""
    answers = [a.model_dump() for a in req.answers if a.content]
    jobs = []
    for own in answers:
        peers = [a for a in answers if a["model"] != own["model"]]
        jobs.append({
            "model": own["model"],
            "messages": prompts.critique_messages(req.question, own["content"], peers),
            "temperature": 0.5,
        })
    results = await mesh_client.chat_many(jobs)
    _fail_if_all_failed(results)
    return {"critiques": results}


@app.post("/api/verdict")
async def stage3_verdict(req: VerdictRequest):
    """STAGE 3 — an independent judge model rules and scores the consensus."""
    messages = prompts.verdict_messages(
        req.question,
        [a.model_dump() for a in req.answers],
        [c.model_dump() for c in req.critiques],
    )
    try:
        raw = await mesh_client.chat(req.judge, messages, temperature=0.2, max_tokens=900)
    except mesh_client.MeshError as err:
        raise HTTPException(status_code=err.status, detail=err.message)

    verdict = _parse_verdict_json(raw)
    return {"verdict": verdict, "judge": req.judge}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fail_if_all_failed(results: list[dict]) -> None:
    """One model failing is fine (the UI shows it); ALL failing is an error."""
    if not any(r["ok"] for r in results):
        first_error = results[0].get("error", "Unknown Mesh error")
        raise HTTPException(status_code=502, detail=first_error)


def _parse_verdict_json(raw: str) -> dict:
    """
    The judge is told to reply with pure JSON, but models sometimes wrap it
    in ```json fences or add a stray sentence. Parse defensively.
    """
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    # Grab the outermost {...} block if there's surrounding text.
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    candidate = match.group(0) if match else cleaned
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        # Graceful fallback: still show SOMETHING useful instead of crashing.
        return {
            "verdict": raw[:600],
            "one_liner": "The judge replied in prose — see the full verdict.",
            "consensus_score": 50,
            "agreements": [],
            "disagreements": [],
            "strongest_voice": "",
            "caution": "The judge's reply was not valid JSON; treat scores as approximate.",
        }

    # Clamp/normalise fields so the frontend can trust them.
    data["consensus_score"] = max(0, min(100, int(data.get("consensus_score", 50))))
    for key in ("agreements", "disagreements"):
        if not isinstance(data.get(key), list):
            data[key] = []
    for key in ("verdict", "one_liner", "strongest_voice", "caution"):
        data[key] = str(data.get(key, ""))
    return data


# ---------------------------------------------------------------------------
# Serve the frontend (a single static page in /static)
# ---------------------------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
