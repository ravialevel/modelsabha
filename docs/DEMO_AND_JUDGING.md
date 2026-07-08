# Demo script & judging prep

## The 2-minute demo video (with you on webcam, per the rules)

**0:00–0:20 — The hook (face to camera).**
"Last month I asked an AI whether to buy or rent a flat. It gave me a confident
answer. Then I asked a different AI — and got the opposite answer, just as
confidently. Which one do you trust? My answer: neither. You convene a sabha."

**0:20–0:40 — The ask.**
Screen-record: type the buy-vs-rent question, point at the three seats —
"GPT, Claude and Gemini, all through one Mesh API key" — click **Convene the Sabha**.

**0:40–1:10 — The debate.**
Let the chamber fill in live. Narrate briefly: "Opening statements arrive in
parallel — three models for the latency of one, because it's async through Mesh.
Now cross-examination: each model reads its peers and must say what it disputes."

**1:10–1:40 — The verdict (the money shot).**
The consensus dial animates. "72 out of 100 — good agreement, but look: they
clashed on whether property beats index funds. That disagreement is exactly what
a single chatbot hides from you."

**1:40–2:00 — Close.**
"Every call routes through Mesh — one key, any model, swappable from a dropdown.
ModelSabha: because a second opinion shouldn't require a second app. Repo's public,
try it yourself."

**Recording tips:** do a dry run first so responses are warm; keep the browser at
100% zoom; record 1080p; speak slightly slower than feels natural.

## Explaining the project confidently (likely judge questions)

**"Why does this need Mesh specifically?"**
Without Mesh I'd need three provider accounts, three SDKs, three billing setups and
three response formats. With Mesh it's one key and one endpoint —
`mesh_client.py` is 100 lines and it's the ONLY file that touches AI. Swapping a
council member is a dropdown, not a code change.

**"Isn't this just calling three APIs?"**
No — the three stages interact. Stage 2 feeds each model its *peers'* answers and
forces a specific dispute. Stage 3 is an independent judge that returns structured
JSON with a consensus score. The product isn't three answers; it's the *measured
disagreement* between them.

**"What was the hardest part?"**
Getting reliable structured output from the judge. Models sometimes wrap JSON in
markdown fences or add prose, so the backend strips fences, extracts the outermost
JSON block, validates and clamps every field, and has a graceful prose fallback.

**"How do you handle failures?"**
Show the code: friendly error mapping for 401/402/404/429, per-model failure
isolation (one dead model doesn't kill the debate), timeouts, and a mock Mesh
server in `tests/` so the app can be developed offline.

**"Who would use this?"**
Anyone making a decision they'd normally ask one chatbot: career moves, big
purchases, tech choices, health-adjacent questions where a single model's
confident error is dangerous. The consensus score tells you when to trust and
when to verify.

## "Wow" moments to point at

1. **The consensus dial** — a number for something invisible: how much AIs disagree.
2. **Parallel answers** — three models answering simultaneously (asyncio + Mesh).
3. **Cross-examination cards** — models quoting and disputing each other by name.
4. **Live model list** — dropdowns populated from Mesh's `/v1/models`, so any model
   on your key can take a seat, including Indian/OSS models.
5. **The caution line** — the judge always says what the human should still verify.
   Judges love AI products that are honest about their limits.
