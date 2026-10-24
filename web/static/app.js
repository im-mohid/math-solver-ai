const $ = (id) => document.getElementById(id);
const chatEl = $("chat");
const MAX_FILE = 10 * 1024 * 1024;
let history = [];      // {role, content}: server ke pathano hoy, jeno chat mone thake
let busy = false;

// ---------- status ----------
async function refreshStatus() {
  try {
    const j = await (await fetch("/api/status")).json();
    const el = $("status");
    el.className = "badge " + (j.worker_online ? "on" : "off");
    el.textContent = j.worker_online ? "🟢 Model online" : "🔴 Model offline (message save hobe)";
  } catch (e) { /* ignore */ }
}

// ---------- helpers ----------
function renderMath(el) {
  if (!window.renderMathInElement) return;
  renderMathInElement(el, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "$", right: "$", display: false },
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true },
    ],
    throwOnError: false,
  });
}
// textContent: model/web theke asha text kokhono HTML hishebe run hobe na
function add(parent, tag, text, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text) e.textContent = text;
  parent.appendChild(e);
  return e;
}
function bubble(role, text) {
  const d = add(chatEl, "div", "", "msg " + role);
  if (text) { add(d, "div", text, "body"); }
  chatEl.scrollTop = chatEl.scrollHeight;
  return d;
}
function answerToText(a) {
  const parts = (a.steps || []).map((s) => [s.latex, s.explain].filter(Boolean).join("\n")).filter(Boolean);
  if (a.final_answer) parts.push("Final answer: " + a.final_answer);
  return parts.join("\n\n").slice(0, 3500);
}

function renderAnswer(a, box) {
  box.textContent = "";
  (a.steps || []).forEach((s) => {
    const multi = (a.steps || []).length > 1;
    const d = add(box, "div", "", multi ? "step" : "body");
    if (multi && s.title) add(d, "div", s.title).style.fontWeight = "600";
    if (s.latex) add(d, "div", s.latex);
    if (s.explain) add(d, "div", s.explain);
  });
  if (a.final_answer) add(box, "div", "✅ " + a.final_answer, "final");
  if (a.read_text) {
    const rd = add(box, "details", "");
    add(rd, "summary", "📄 File theke ami ja pelam (thik ache kina dekho)");
    add(rd, "pre", a.read_text);
  }
  if (a.expert_solution) {
    const det = add(box, "details", "");
    add(det, "summary", "Expert model er mul solution");
    add(det, "pre", a.expert_solution);
  }
  const meta = add(box, "div", "", "meta");
  if (a.search_query) add(meta, "div", "🔎 Search: " + a.search_query);
  if (a.search_note) add(meta, "div", a.search_note);
  (a.sources || []).forEach((s, i) => {
    if (!/^https?:\/\//.test(s.url || "")) return;
    const p = add(meta, "div", `[${i + 1}] `);
    const l = document.createElement("a");
    l.href = s.url; l.target = "_blank"; l.rel = "noopener noreferrer";
    l.textContent = s.title || s.url;
    p.appendChild(l);
  });
  if (!meta.childNodes.length) meta.remove();
  renderMath(box);
  chatEl.scrollTop = chatEl.scrollHeight;
}

// ---------- polling ----------
const STATUS_TEXT = { pending: "Line e achhe, model er opekkha...", processing: "Model bhabche..." };

async function poll(id, box, userMsg, tries = 0) {
  if (tries > 450) { box.textContent = "Onek shomoy lagche. Pore abar dekho."; return finish(); }
  try {
    const j = await (await fetch(`/api/result/${id}`)).json();
    if (j.status === "done") {
      renderAnswer(j.answer || {}, box);
      history.push({ role: "user", content: userMsg });
      history.push({ role: "assistant", content: answerToText(j.answer || {}) });
      history = history.slice(-12);
      return finish();
    }
    if (j.status === "error" || j.error) {
      box.classList.add("err"); box.textContent = "⚠ " + (j.error || "Error");
      return finish();
    }
    box.textContent = STATUS_TEXT[j.status] || "...";
  } catch (e) { /* network hiccup: abar try */ }
  setTimeout(() => poll(id, box, userMsg, tries + 1), 2000);
}

function finish() { busy = false; $("askBtn").disabled = false; chatEl.scrollTop = chatEl.scrollHeight; }

// ---------- send ----------
async function send() {
  if (busy) return;
  const q = $("question").value.trim();
  const f = $("file").files[0];
  if (!q && !f) return;
  if (f && f.size > MAX_FILE) { bubble("assistant err", "⚠ File 10 MB er beshi"); return; }

  busy = true; $("askBtn").disabled = true;
  bubble("user", (q || "") + (f ? `\n📎 ${f.name}` : ""));
  const box = bubble("assistant", "");
  box.classList.add("typing"); box.textContent = f ? "File upload hocche..." : "Pathano hocche...";

  const fd = new FormData();
  fd.append("question", q);
  fd.append("language", $("language").value);
  fd.append("search", $("search").value);
  fd.append("think", $("think").checked ? "1" : "0");
  fd.append("history", JSON.stringify(history));
  if (f) fd.append("file", f);

  $("question").value = ""; autosize();
  clearFile();

  try {
    const r = await fetch("/api/ask", { method: "POST", body: fd });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Request fail");
    poll(j.job_id, box, q || (f ? `[file: ${f.name}]` : ""));
  } catch (e) {
    box.classList.add("err"); box.textContent = "⚠ " + e.message; finish();
  }
}

function clearFile() {
  $("file").value = ""; $("fileRow").classList.add("hidden"); $("fileName").textContent = "";
}
function autosize() {
  const t = $("question"); t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 160) + "px";
}

$("askBtn").addEventListener("click", send);
$("question").addEventListener("input", autosize);
$("question").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("file").addEventListener("change", () => {
  const f = $("file").files[0];
  if (f) { $("fileName").textContent = "📎 " + f.name; $("fileRow").classList.remove("hidden"); }
});
$("clearFile").addEventListener("click", clearFile);
$("newChat").addEventListener("click", () => {
  if (busy) return;
  history = [];
  chatEl.querySelectorAll(".msg:not(#welcome)").forEach((n) => n.remove());
});

refreshStatus();
setInterval(refreshStatus, 15000);
