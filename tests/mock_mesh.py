"""
tests/mock_mesh.py — a tiny fake Mesh API for local testing.

Run this, point MESH_BASE_URL at it, and the whole app works offline:
    uvicorn tests.mock_mesh:app --port 9100
    MESH_BASE_URL=http://127.0.0.1:9100/v1 MESH_API_KEY=rsk_test uvicorn app:app

Useful for developing the UI without spending Mesh credits, and as proof
in the repo that the integration was built carefully.
"""

import json
from fastapi import FastAPI, Request

app = FastAPI(title="Mock Mesh")

VERDICT = {
    "verdict": "Rent for now: in most Indian metros current price-to-rent ratios favour renting while investing the difference. Revisit once you are certain you will stay 7+ years in one city.",
    "one_liner": "Rent, invest the difference, and buy only when your city is certain.",
    "consensus_score": 72,
    "agreements": ["Price-to-rent ratios in metros currently favour renting", "Buying only makes sense with a 7+ year horizon"],
    "disagreements": ["gpt disagreed with gemini on whether property appreciation will beat index funds"],
    "strongest_voice": "anthropic/claude-3-5-haiku",
    "caution": "These models cannot see your city, salary, or family plans — verify EMI affordability yourself.",
}


@app.get("/v1/models")
async def models():
    return {"data": [
        {"id": "openai/gpt-4o-mini"}, {"id": "anthropic/claude-3-5-haiku"},
        {"id": "google/gemini-2.0-flash"}, {"id": "openai/gpt-4o"},
    ]}


@app.post("/v1/chat/completions")
async def completions(request: Request):
    body = await request.json()
    model = body.get("model", "unknown")
    system = body["messages"][0]["content"]

    if "presiding judge" in system:
        content = json.dumps(VERDICT)
    elif "reviewing your peers" in system:
        content = f"[mock {model}] I dispute the claim that appreciation always beats inflation — historically that varies by city. My peer was right about maintenance costs, which I missed."
    else:
        content = f"[mock {model}] Rent for now. Ratios favour renting, flexibility matters early in a career, and investing the EMI difference usually compounds better."

    return {"choices": [{"message": {"role": "assistant", "content": content}}]}
