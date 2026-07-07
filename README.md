# ModelSabha ॥

**Don't trust one AI. Convene a sabha.**

Ask one question. Three different AI models answer it independently, cross-examine
each other's answers, and a fourth "judge" model delivers a final verdict — with an
honest **consensus score (0–100)** showing how much the models actually agreed.

A single AI can be confidently wrong. ModelSabha makes model disagreement *visible*,
so you know when an answer is solid and when you should dig deeper.

Built for the **Mesh API Hackathon 2026** (Multi-model track).

---

## How it works

```
                        ┌───────────────────────────┐
      your question ──▶ │        FastAPI backend    │
                        └────────────┬──────────────┘
                                     │  every call goes through
                                     ▼  ONE gateway: Mesh API
                        ┌───────────────────────────┐
                        │   api.meshapi.ai/v1/...   │
                        └──┬─────────┬──────────┬───┘
        Stage 1 (parallel) ▼         ▼          ▼
                      GPT-4o-mini  Claude    Gemini      opening statements
        Stage 2 (parallel) ▼         ▼          ▼
                       each model critiques its peers    cross-examination
        Stage 3                      ▼
                            judge model (GPT-4o)         JSON verdict +
                                                         consensus score
```

- **Stage 1 — Opening statements.** All council models answer in parallel
  (`asyncio.gather`), so three answers cost the time of one.
- **Stage 2 — Cross-examination.** Each model sees only its *peers'* answers and
  must name the most important thing it disputes.
- **Stage 3 — Verdict.** An independent judge model returns strict JSON:
  the verdict, agreements, disagreements, and a 0–100 consensus score.

Because Mesh exposes every provider behind one OpenAI-compatible endpoint, swapping
GPT ↔ Claude ↔ Gemini ↔ Llama is a *dropdown*, not a code change. This app is
impossible to build this simply without a router like Mesh.

## Project structure

```
modelsabha/
├── app.py               # FastAPI routes — one endpoint per debate stage
├── mesh_client.py       # THE ONLY FILE THAT CALLS AI — all traffic → Mesh API
├── prompts.py           # all prompt engineering, in one readable place
├── static/
│   ├── index.html       # 4 views: Ask · Chamber · Verdict · History
│   ├── style.css        # handcrafted design system (no CSS framework)
│   └── app.js           # orchestrates the 3 stages, animates the consensus dial
├── tests/
│   └── mock_mesh.py     # fake Mesh server → develop/demo offline, spend ₹0
├── requirements.txt
└── .env.example
```

## Setup (5 minutes)

Requirements: Python 3.10+ and a Mesh API key from <https://app.meshapi.ai>
(API Keys → create key → add a small balance in Billing).

```bash
git clone <your-repo-url>
cd modelsabha

python -m venv .venv
# Windows:  .venv\Scripts\activate     macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt

# add your key
cp .env.example .env        # Windows: copy .env.example .env
# open .env and paste your rsk_... key

uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>, type a question, and convene the sabha.

### Run without spending credits (mock mode)

```bash
# terminal 1 — fake Mesh API
uvicorn tests.mock_mesh:app --port 9100

# terminal 2 — app pointed at the fake
MESH_BASE_URL=http://127.0.0.1:9100/v1 MESH_API_KEY=rsk_test uvicorn app:app
```

## Configuration

| Variable        | What it is                                   |
|-----------------|----------------------------------------------|
| `MESH_API_KEY`  | Your `rsk_...` key from the Mesh dashboard   |
| `MESH_BASE_URL` | Defaults to `https://api.meshapi.ai/v1`      |

Default council: `openai/gpt-4o-mini`, `anthropic/claude-3-5-haiku`,
`google/gemini-2.0-flash`, judged by `openai/gpt-4o`. The dropdowns are populated
live from Mesh's `GET /v1/models`, so you can seat any model your key can access.

## Error handling

- Mesh failures (bad key, empty balance, rate limits, unknown model) are translated
  into plain-language messages in the UI, not stack traces.
- One model failing does **not** kill the debate — its seat shows the failure and
  the remaining models continue.
- The judge is instructed to return strict JSON; if it drifts into prose anyway,
  the backend falls back gracefully instead of crashing.

## Future improvements

- Streaming (SSE) so answers appear word by word
- A fourth round where models can *change their vote* after cross-examination
- Hindi / Hinglish debate mode
- Shareable verdict links and a public "disagreement leaderboard" of questions
  where models conflict the most
