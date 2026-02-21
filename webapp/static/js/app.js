/* ============================================================
   Who Am I? – LLM Persona Guessing Game
   Single-page application logic
   ============================================================ */

"use strict";

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  username: localStorage.getItem("whoami_username") || "",
  questionCount: 0,
  activeGame: null, // { mode, characterName, challengeDate }
  currentView: "home",
};

// ── DOM helpers ───────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function showView(name) {
  $$(".view").forEach((v) => v.classList.remove("active"));
  $$(".nav-btn[data-view]").forEach((b) => b.classList.remove("active"));
  const view = $(`#view-${name}`);
  if (view) view.classList.add("active");
  const btn = $(`.nav-btn[data-view="${name}"]`);
  if (btn) btn.classList.add("active");
  state.currentView = name;
  if (name === "leaderboard") loadLeaderboard();
  if (name === "facts") loadFacts();
}

// ── Toast notifications ───────────────────────────────────────────────────
function toast(msg, type = "info") {
  const container = $("#toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Username modal ────────────────────────────────────────────────────────
function openUsernameModal(onConfirm) {
  const overlay = $("#modal-username");
  overlay.classList.remove("hidden");
  const input = $("#modal-username-input");
  input.value = state.username;
  input.focus();

  const confirm = () => {
    const val = input.value.trim();
    if (!val) { toast("Please enter a name!", "error"); return; }
    state.username = val;
    localStorage.setItem("whoami_username", val);
    overlay.classList.add("hidden");
    onConfirm(val);
  };

  $("#modal-username-confirm").onclick = confirm;
  input.onkeydown = (e) => { if (e.key === "Enter") confirm(); };
  $("#modal-username-cancel").onclick = () => overlay.classList.add("hidden");
}

function requireUsername(cb) {
  if (state.username) { cb(state.username); return; }
  openUsernameModal(cb);
}

// ── Copy to clipboard ─────────────────────────────────────────────────────
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Prompt copied to clipboard!", "success");
  } catch {
    // fallback
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    toast("Prompt copied!", "success");
  }
}

// ── API helpers ───────────────────────────────────────────────────────────
async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ── Loading state helper ──────────────────────────────────────────────────
function setLoading(btn, loading, text = "") {
  if (loading) {
    btn.dataset.origText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span> ${text || "Loading…"}`;
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.origText || text;
    btn.disabled = false;
  }
}

// ── Render prompt card ────────────────────────────────────────────────────
function renderGameCard({ mode, promptText, introClue, characterName, challengeDate, category }) {
  state.activeGame = { mode, characterName, challengeDate };
  state.questionCount = 0;

  const section = $("#game-section");
  section.classList.remove("hidden");
  section.innerHTML = `
    <div class="clue-card">
      <div class="mystery-label">🔍 Mystery Persona — ${category}</div>
      <div class="clue-text">${introClue}</div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">📋 Your Persona Prompt</span>
        <span class="tag tag-purple">${mode === "daily" ? "Daily Challenge" : "Free Play"}</span>
      </div>
      <p class="text-muted mb-2" style="font-size:.85rem">
        Copy this prompt and paste it into <strong>any LLM</strong> (ChatGPT, Claude, Gemini…).
        Then ask it questions to figure out who it is!
      </p>
      <div class="prompt-box" id="prompt-text">${escapeHtml(promptText)}</div>
      <div class="copy-row">
        <span class="copy-hint">Tip: Paste into your favourite LLM and start asking yes/no questions.</span>
        <button class="btn btn-secondary btn-sm" id="btn-copy">📋 Copy Prompt</button>
      </div>
    </div>

    <div class="card mt-2">
      <div class="card-header">
        <span class="card-title">🤔 Ready to Guess?</span>
        <div class="q-counter">
          Questions asked: <span class="count" id="q-count">0</span>
        </div>
      </div>
      <p class="text-muted mb-2" style="font-size:.85rem">
        Increment the counter each time you ask the LLM a question, then submit your guess!
      </p>
      <div class="flex gap-2 items-center mb-2" style="flex-wrap:wrap">
        <button class="btn btn-secondary btn-sm" id="btn-q-minus">−</button>
        <button class="btn btn-secondary btn-sm" id="btn-q-plus">+ Add Question</button>
      </div>
      <div class="guess-form mt-2">
        <input class="input" id="guess-input" placeholder="Who is this character?" autocomplete="off" />
        <button class="btn btn-primary" id="btn-guess">Submit Guess</button>
      </div>
      <div id="guess-result" class="mt-2"></div>
    </div>
  `;

  // Wire events
  $("#btn-copy").onclick = () => copyText(promptText);
  $("#btn-q-plus").onclick = () => updateQCount(1);
  $("#btn-q-minus").onclick = () => updateQCount(-1);
  $("#btn-guess").onclick = submitGuess;
  $("#guess-input").onkeydown = (e) => { if (e.key === "Enter") submitGuess(); };

  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function updateQCount(delta) {
  state.questionCount = Math.max(0, state.questionCount + delta);
  const el = $("#q-count");
  if (el) el.textContent = state.questionCount;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Submit guess ──────────────────────────────────────────────────────────
async function submitGuess() {
  if (!state.activeGame) return;
  requireUsername(async (username) => {
    const guessInput = $("#guess-input");
    const guess = guessInput ? guessInput.value.trim() : "";
    if (!guess) { toast("Please type your guess first!", "error"); return; }

    const btn = $("#btn-guess");
    setLoading(btn, true, "Checking…");

    try {
      const body = {
        username,
        guess,
        question_count: state.questionCount,
        mode: state.activeGame.mode,
      };
      if (state.activeGame.mode === "daily") {
        body.challenge_date = state.activeGame.challengeDate;
      } else {
        body.character_name = state.activeGame.characterName;
      }

      const result = await api("/guess", {
        method: "POST",
        body: JSON.stringify(body),
      });

      const resultEl = $("#guess-result");
      if (resultEl) {
        resultEl.innerHTML = `
          <div class="result-banner ${result.correct ? "correct" : "incorrect"}">
            <span class="result-icon">${result.correct ? "🎉" : "🤔"}</span>
            <span class="result-message">${result.message}</span>
          </div>
        `;
      }

      if (result.correct) {
        if (btn) btn.disabled = true;
        toast("Brilliant! Check the leaderboard!", "success");
        setTimeout(() => showView("leaderboard"), 2500);
      }
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setLoading(btn, false);
    }
  });
}

// ── Daily challenge ───────────────────────────────────────────────────────
async function startDaily() {
  const btn = $("#btn-daily");
  setLoading(btn, true, "Loading today's challenge…");
  try {
    const data = await api("/daily");
    showView("game");
    renderGameCard({
      mode: "daily",
      promptText: data.generated_prompt,
      introClue: data.intro_clue,
      characterName: null,       // hidden for daily – validated server-side
      challengeDate: data.date,
      category: data.category,
    });
  } catch (err) {
    toast(`Failed to load daily challenge: ${err.message}`, "error");
  } finally {
    setLoading(btn, false);
  }
}

// ── Free play ─────────────────────────────────────────────────────────────
async function startFreePlay() {
  const btn = $("#btn-freeplay");
  setLoading(btn, true, "Generating character…");
  try {
    const data = await api("/generate", { method: "POST" });
    showView("game");
    renderGameCard({
      mode: "freeplay",
      promptText: data.generated_prompt,
      introClue: data.intro_clue,
      characterName: data.character_name,  // safe to keep in JS – game is self-contained
      challengeDate: null,
      category: data.category,
    });
  } catch (err) {
    toast(`Failed to generate character: ${err.message}`, "error");
  } finally {
    setLoading(btn, false);
  }
}

// ── Leaderboard ───────────────────────────────────────────────────────────
async function loadLeaderboard() {
  const tbody = $("#lb-tbody");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="padding:2rem">Loading…</td></tr>`;

  try {
    const rows = await api("/leaderboard?mode=daily&limit=20");
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="padding:2rem">No entries yet – be the first! 🏆</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map((r) => {
      const rankClass = r.rank <= 3 ? `rank-${r.rank}` : "rank-n";
      const time = r.solved_at ? new Date(r.solved_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";
      return `
        <tr>
          <td><span class="rank-badge ${rankClass}">${r.rank}</span></td>
          <td><strong>${escapeHtml(r.username)}</strong></td>
          <td><span class="tag tag-yellow">${r.question_count} Qs</span></td>
          <td class="text-muted">${time}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted" style="padding:2rem">Could not load leaderboard.</td></tr>`;
  }
}

// ── Fun facts ─────────────────────────────────────────────────────────────
const FACT_ICONS = ["🧠","💡","⚡","🔬","🤖","🎯","🌐","📊","🔮","💬"];

async function loadFacts() {
  const grid = $("#facts-grid");
  if (!grid) return;
  grid.innerHTML = `<p class="text-muted">Loading facts…</p>`;
  try {
    const data = await api("/funfacts?count=6");
    grid.innerHTML = data.facts.map((f, i) => `
      <div class="fact-card">
        <div class="fact-icon">${FACT_ICONS[i % FACT_ICONS.length]}</div>
        <div class="fact-text">${escapeHtml(f)}</div>
      </div>
    `).join("");
  } catch {
    grid.innerHTML = `<p class="text-muted">Could not load facts.</p>`;
  }
}

async function refreshOneFact() {
  const btn = $("#btn-new-fact");
  if (btn) btn.disabled = true;
  try {
    const data = await api("/funfact");
    toast(data.fact, "info");
  } catch { /* ignore */ }
  if (btn) btn.disabled = false;
}

// ── Daily countdown ───────────────────────────────────────────────────────
function updateCountdown() {
  const el = $("#daily-countdown");
  if (!el) return;
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(0, 0, 0, 0);
  const diff = tomorrow - now;
  const h = String(Math.floor(diff / 3600000)).padStart(2, "0");
  const m = String(Math.floor((diff % 3600000) / 60000)).padStart(2, "0");
  const s = String(Math.floor((diff % 60000) / 1000)).padStart(2, "0");
  el.textContent = `${h}:${m}:${s}`;
}

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Nav buttons
  $$(".nav-btn[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });

  // Home CTA buttons
  const btnDaily   = $("#btn-daily");
  const btnFreeplay = $("#btn-freeplay");
  if (btnDaily)   btnDaily.addEventListener("click", startDaily);
  if (btnFreeplay) btnFreeplay.addEventListener("click", startFreePlay);

  // Game view buttons
  const btnNewRound = $("#btn-new-round");
  if (btnNewRound) btnNewRound.addEventListener("click", startFreePlay);

  // Username header button
  const btnUser = $("#btn-set-user");
  if (btnUser) btnUser.addEventListener("click", () => openUsernameModal(() => {}));

  // Leaderboard refresh
  const btnRefreshLb = $("#btn-refresh-lb");
  if (btnRefreshLb) btnRefreshLb.addEventListener("click", loadLeaderboard);

  // Facts refresh
  const btnNewFact = $("#btn-new-fact");
  if (btnNewFact) btnNewFact.addEventListener("click", loadFacts);

  // Show username in header if set
  updateUserDisplay();

  // Daily countdown ticker
  updateCountdown();
  setInterval(updateCountdown, 1000);

  // Start on home
  showView("home");
});

function updateUserDisplay() {
  const el = $("#header-username");
  if (el) el.textContent = state.username ? `👤 ${state.username}` : "Set Name";
}
