/* =========================================================================
   ModelSabha frontend logic (no frameworks — plain browser JavaScript).

   The debate runs as three sequential API calls so the user WATCHES it happen:
     1. POST /api/answers    → opening statements (parallel on the server)
     2. POST /api/critiques  → cross-examination
     3. POST /api/verdict    → judge's ruling + consensus score
   ========================================================================= */

const SEAT_COLORS = ["var(--seat-a)", "var(--seat-b)", "var(--seat-c)", "var(--seat-a)"];
const DEFAULT_PANEL = ["openai/gpt-4o-mini", "anthropic/claude-3-5-haiku", "google/gemini-2.0-flash"];
const DEFAULT_JUDGE = "openai/gpt-4o";
const HISTORY_KEY = "modelsabha_history_v1";

const $ = (id) => document.getElementById(id);

let current = null; // { question, answers, critiques, verdict }

/* ---------------- view switching ---------------- */

function showView(name) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  $(`view-${name}`).classList.add("active");
  document.querySelectorAll(".navlink").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === name)
  );
  if (name === "history") renderHistory();
}

document.querySelectorAll(".navlink").forEach((btn) =>
  btn.addEventListener("click", () => showView(btn.dataset.view))
);

/* ---------------- setup: models + health ---------------- */

async function init() {
  // Example chips fill the textarea.
  document.querySelectorAll("#example-chips .chip").forEach((chip) =>
    chip.addEventListener("click", () => { $("question").value = chip.textContent; })
  );

  // Warn early if the Mesh key isn't configured.
  try {
    const health = await fetch("/api/health").then((r) => r.json());
    $("key-warning").hidden = health.mesh_key_configured;
  } catch { /* server not ready; ignore */ }

  // Populate the four model dropdowns from Mesh's live model list.
  let models = DEFAULT_PANEL.concat(DEFAULT_JUDGE);
  try {
    const data = await fetch("/api/models").then((r) => r.json());
    if (Array.isArray(data.models) && data.models.length) models = data.models;
  } catch { /* fall back to defaults */ }

  const selects = [
    [$("model-a"), DEFAULT_PANEL[0]],
    [$("model-b"), DEFAULT_PANEL[1]],
    [$("model-c"), DEFAULT_PANEL[2]],
    [$("model-judge"), DEFAULT_JUDGE],
  ];
  for (const [select, preferred] of selects) {
    select.innerHTML = "";
    for (const id of models) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id;
      select.appendChild(opt);
    }
    select.value = models.includes(preferred) ? preferred : models[0];
  }
  // Avoid three identical seats if the preferred defaults weren't available.
  if (models.length >= 3 && new Set(selects.slice(0, 3).map(([s]) => s.value)).size === 1) {
    $("model-b").value = models[1];
    $("model-c").value = models[2];
  }
}

/* ---------------- the debate ---------------- */

$("convene").addEventListener("click", runDebate);

async function runDebate() {
  const question = $("question").value.trim();
  const panel = [$("model-a").value, $("model-b").value, $("model-c").value];
  const judge = $("model-judge").value;

  $("ask-error").hidden = true;
  if (question.length < 5) return showError("ask-error", "Ask a real question — at least a few words.");
  if (new Set(panel).size < 2) return showError("ask-error", "Pick at least two different models for a real debate.");

  $("convene").disabled = true;
  current = { question, panel, judge, answers: [], critiques: [], verdict: null, when: Date.now() };
  buildChamber(question, panel);
  showView("chamber");

  try {
    // -------- Stage 1: opening statements --------
    setStage(1, "running");
    const a = await api("/api/answers", { question, models: panel });
    current.answers = a.answers;
    renderAnswers(a.answers);
    setStage(1, "done");

    // -------- Stage 2: cross-examination --------
    setStage(2, "running");
    const okAnswers = a.answers.filter((x) => x.ok).map((x) => ({ model: x.model, content: x.content }));
    if (okAnswers.length < 2) throw new Error("Too few models answered to hold a debate. Try different models.");
    const c = await api("/api/critiques", { question, answers: okAnswers });
    current.critiques = c.critiques;
    renderCritiques(c.critiques);
    setStage(2, "done");

    // -------- Stage 3: verdict --------
    setStage(3, "running");
    const okCritiques = c.critiques.filter((x) => x.ok).map((x) => ({ model: x.model, content: x.content }));
    const v = await api("/api/verdict", { question, answers: okAnswers, critiques: okCritiques, judge });
    current.verdict = v.verdict;
    setStage(3, "done");

    saveToHistory(current);
    renderVerdict(current);
    setTimeout(() => showView("verdict"), 600);
  } catch (err) {
    showError("chamber-error", err.message || "Something went wrong. Check the terminal running uvicorn.");
  } finally {
    $("convene").disabled = false;
  }
}

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI returns a string for our errors, an array for validation errors.
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

function showError(id, message) {
  const el = $(id);
  el.textContent = message;
  el.hidden = false;
}

/* ---------------- chamber rendering ---------------- */

function buildChamber(question, panel) {
  $("chamber-question").textContent = question;
  $("chamber-error").hidden = true;
  ["stage-1", "stage-2", "stage-3"].forEach((id) => ($(id).className = "stage"));

  const bench = $("bench");
  bench.innerHTML = "";
  panel.forEach((model, i) => {
    const card = document.createElement("article");
    card.className = "member";
    card.style.animationDelay = `${i * 0.12}s`;
    card.innerHTML = `
      <div class="member-head">
        <span class="seat-dot" style="background:${SEAT_COLORS[i]}"></span>
        <span class="member-name">${escapeHtml(model)}</span>
      </div>
      <div class="member-body thinking" id="body-${i}">Preparing opening statement…</div>
      <div id="rebuttal-slot-${i}"></div>`;
    bench.appendChild(card);
  });
}

function setStage(n, state) {
  $(`stage-${n}`).className = `stage ${state}`;
}

function renderAnswers(answers) {
  answers.forEach((a, i) => {
    const body = $(`body-${i}`);
    body.classList.remove("thinking");
    if (a.ok) {
      body.textContent = a.content;
    } else {
      body.innerHTML = `<span class="member-fail">Did not answer: ${escapeHtml(a.error)}</span>`;
    }
  });
}

function renderCritiques(critiques) {
  // Match each critique back to its member card by model id.
  const panel = current.panel;
  critiques.forEach((c) => {
    const i = panel.indexOf(c.model);
    if (i === -1 || !c.ok) return;
    const slot = $(`rebuttal-slot-${i}`);
    const div = document.createElement("div");
    div.className = "rebuttal";
    div.style.borderLeftColor = SEAT_COLORS[i];
    div.innerHTML = `<span class="rebuttal-label" style="color:${SEAT_COLORS[i]}">Cross-examination</span>`;
    div.appendChild(document.createTextNode(c.content));
    slot.appendChild(div);
  });
}

/* ---------------- verdict rendering ---------------- */

function renderVerdict(entry) {
  const v = entry.verdict;
  $("verdict-oneliner").textContent = v.one_liner || "";
  $("verdict-text").textContent = v.verdict || "";

  fillList("agreements", v.agreements, "The judge listed no explicit agreements.");
  fillList("disagreements", v.disagreements, "No major conflicts — the council largely agreed.");

  $("strongest-voice").innerHTML = v.strongest_voice
    ? `Most convincing voice: <strong>${escapeHtml(v.strongest_voice)}</strong> · judged by <strong>${escapeHtml(entry.judge)}</strong>`
    : "";
  $("caution").textContent = v.caution || "";

  animateDial(v.consensus_score);
}

function fillList(id, items, emptyText) {
  const ul = $(id);
  ul.innerHTML = "";
  const list = items && items.length ? items : [emptyText];
  for (const item of list) {
    const li = document.createElement("li");
    li.textContent = item;
    ul.appendChild(li);
  }
}

function animateDial(score) {
  const ARC = 251.3; // length of the semicircle path
  const fill = $("dial-fill");
  const num = $("dial-num");

  // Colour tells the story: red = conflict, brass = split, peacock = consensus.
  const color = score < 40 ? "var(--seat-c)" : score < 70 ? "var(--judge)" : "var(--seat-b)";
  fill.style.stroke = color;
  $("dial-caption").textContent =
    score < 40 ? "The models genuinely disagree — be careful with any single AI's answer here."
    : score < 70 ? "Partial agreement — the disagreements below are worth reading."
    : "Strong consensus across independent models.";

  // Reset, then animate on the next frame so the CSS transition fires.
  fill.style.strokeDashoffset = ARC;
  requestAnimationFrame(() =>
    requestAnimationFrame(() => {
      fill.style.strokeDashoffset = ARC * (1 - score / 100);
    })
  );

  // Count the number up in sync with the arc.
  const start = performance.now();
  const tick = (t) => {
    const p = Math.min(1, (t - start) / 1200);
    num.textContent = Math.round(score * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

$("new-question").addEventListener("click", () => showView("ask"));
$("back-to-chamber").addEventListener("click", () => showView("chamber"));

/* ---------------- history (saved in this browser) ---------------- */

function saveToHistory(entry) {
  const history = loadHistory();
  history.unshift({
    question: entry.question,
    verdict: entry.verdict,
    judge: entry.judge,
    panel: entry.panel,
    when: entry.when,
  });
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 30)));
}

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; }
  catch { return []; }
}

function renderHistory() {
  const history = loadHistory();
  const ul = $("history-list");
  ul.innerHTML = "";
  $("history-empty").hidden = history.length > 0;

  history.forEach((h) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "history-item";
    btn.innerHTML = `
      <span class="history-q">${escapeHtml(h.question)}</span>
      <span class="history-score">${h.verdict?.consensus_score ?? "–"}/100</span>`;
    btn.addEventListener("click", () => {
      current = { ...h, answers: [], critiques: [] };
      renderVerdict(h);
      showView("verdict");
    });
    li.appendChild(btn);
    ul.appendChild(li);
  });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

init();
