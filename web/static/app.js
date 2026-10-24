const $ = (id) => document.getElementById(id);
const STATUS_TEXT = { pending: "Line e achhe, model er opekkha...", processing: "Model solve korche..." };

async function refreshStatus() {
  try {
    const r = await fetch("/api/status");
    const j = await r.json();
    const el = $("status");
    el.className = "badge " + (j.worker_online ? "on" : "off");
    el.textContent = j.worker_online
      ? "🟢 Model online"
      : "🔴 Model offline (question save hobe, model online hole answer pabe)";
  } catch (e) { /* ignore */ }
}

function renderMath(el) {
  if (window.renderMathInElement) {
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
}

// textContent use kora hocche, jeno model/web theke asha text HTML hishebe run na hoy
function add(parent, tag, text, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  e.textContent = text;
  parent.appendChild(e);
  return e;
}

function renderAnswer(a) {
  const box = $("answer");
  box.textContent = "";
  box.classList.remove("hidden");

  if (a.understood_question) {
    add(box, "h3", "Question");
    add(box, "div", a.understood_question);
  }
  if (a.approach) {
    add(box, "h3", "Approach");
    add(box, "div", a.approach);
  }
  if (Array.isArray(a.steps) && a.steps.length) {
    add(box, "h3", "Step-by-step");
    a.steps.forEach((s, i) => {
      const d = add(box, "div", "", "step");
      add(d, "h4", `${i + 1}. ${s.title || ""}`);
      if (s.latex) add(d, "div", s.latex);
      if (s.explain) add(d, "div", s.explain);
    });
  }
  if (a.final_answer) {
    add(box, "h3", "Final answer");
    add(box, "div", a.final_answer, "final");
  }
  if (a.expert_solution) {
    const det = document.createElement("details");
    add(det, "summary", "Expert model er mul solution (verify korar jonno)");
    add(det, "pre", a.expert_solution);
    box.appendChild(det);
  }
  const meta = add(box, "div", "", "meta");
  if (a.verification) add(meta, "div", "Verification: " + (a.verification.method || "-") + (a.verification.passed ? " ✓" : ""));
  if (a.confidence) add(meta, "div", "Confidence: " + a.confidence);
  (a.sources || []).forEach((s) => {
    const p = add(meta, "div", "");
    if (/^https?:\/\//.test(s.url || "")) {
      const l = document.createElement("a");
      l.href = s.url; l.target = "_blank"; l.rel = "noopener noreferrer";
      l.textContent = s.title || s.url;
      p.appendChild(l);
    }
  });
  // notun feature er extra field (jemon graph_url) pore ekhane render korba
  renderMath(box);
}

async function poll(id, tries = 0) {
  if (tries > 300) { $("progress").textContent = "Onek shomoy lagche. Pore abar dekho."; $("askBtn").disabled = false; return; }
  const r = await fetch(`/api/result/${id}`);
  const j = await r.json();
  if (j.status === "done") {
    $("progress").classList.add("hidden");
    $("askBtn").disabled = false;
    return renderAnswer(j.answer || {});
  }
  if (j.status === "error" || j.error) {
    $("progress").textContent = "⚠ " + (j.error || "Error");
    $("askBtn").disabled = false;
    return;
  }
  $("progress").textContent = STATUS_TEXT[j.status] || "...";
  setTimeout(() => poll(id, tries + 1), 2000);
}

const MAX_FILE = 10 * 1024 * 1024;

$("file").addEventListener("change", () => {
  const f = $("file").files[0];
  $("fileName").textContent = f ? f.name : "";
  $("clearFile").classList.toggle("hidden", !f);
});
$("clearFile").addEventListener("click", () => {
  $("file").value = "";
  $("fileName").textContent = "";
  $("clearFile").classList.add("hidden");
});

$("askBtn").addEventListener("click", async () => {
  const q = $("question").value.trim();
  const f = $("file").files[0];
  if (!q && !f) return;
  if (f && f.size > MAX_FILE) { $("progress").classList.remove("hidden"); $("progress").textContent = "⚠ File 10 MB er beshi"; return; }

  $("askBtn").disabled = true;
  $("answer").classList.add("hidden");
  $("progress").classList.remove("hidden");
  $("progress").textContent = f ? "File upload hocche..." : "Pathano hocche...";

  const fd = new FormData();
  fd.append("question", q);
  fd.append("language", $("language").value);
  if (f) fd.append("file", f);

  try {
    const r = await fetch("/api/ask", { method: "POST", body: fd });   // Content-Type browser nijei dey
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Request fail");
    poll(j.job_id);
  } catch (e) {
    $("progress").textContent = "⚠ " + e.message;
    $("askBtn").disabled = false;
  }
});

refreshStatus();
setInterval(refreshStatus, 15000);
