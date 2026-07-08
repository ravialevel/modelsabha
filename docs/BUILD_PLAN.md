# Build plan — 5 days, honest commits

The hackathon rules require a real commit history: steady progress, not one giant
end-of-week dump. Follow this plan — type each piece into VS Code yourself,
run it, understand it, THEN commit. This also prepares you for judge questions.

## Day 1 (today, 7 July) — foundation
- [ ] Create repo `modelsabha` on GitHub (public), clone it
- [ ] Add `README.md` (just the title + one-line idea), `.gitignore`, `requirements.txt`
- [ ] `python -m venv .venv`, install deps
- [ ] Write `mesh_client.py` — get a single `chat()` call working with YOUR real
      Mesh key from a throwaway script; verify a response comes back
- 3–4 commits, e.g. "init project", "add mesh client with single chat call",
  "friendly error handling for mesh failures"

## Day 2 (8 July) — the debate engine
- [ ] `prompts.py` (opening / critique / verdict prompts)
- [ ] `chat_many()` parallel calls
- [ ] `app.py` with `/api/answers` and `/api/critiques`; test with curl
- Commits: "add debate prompts", "parallel model calls", "stage 1+2 endpoints"

## Day 3 (9 July) — judge + frontend skeleton
- [ ] `/api/verdict` with defensive JSON parsing
- [ ] `static/index.html` + basic `app.js` wiring (ugly is fine today)
- [ ] `tests/mock_mesh.py` so you stop burning credits while styling
- Commits: "judge verdict endpoint", "frontend skeleton", "mock mesh for offline dev"

## Day 4 (10 July) — polish
- [ ] Full CSS design system, consensus dial animation, history view
- [ ] Live `/api/models` dropdowns, key-missing warning, error states
- [ ] Test on your phone's browser (responsive check)
- Commits: "design system", "consensus dial", "history + model picker", "responsive fixes"

## Day 5 (11 July) — ship
- [ ] Finish README (setup guide, architecture diagram)
- [ ] Record the 2–3 min demo video (script in DEMO_AND_JUDGING.md)
- [ ] Fresh-clone test: clone your own repo into a new folder and follow your
      own README from scratch — if it doesn't run, fix the README
- [ ] Share repo access with contact@meshapi.ai, submit before the deadline
- Commits: "complete README", "final polish"

Buffer: 12 July morning for anything broken.

## Tips
- Commit messages describe WHAT changed, small and boring is perfect
- Never commit `.env` (it's gitignored — check with `git status` before pushing)
- Keep the Mesh dashboard open while testing to watch your spend
