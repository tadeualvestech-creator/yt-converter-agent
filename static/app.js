/* =====================================================
   YTConvert — Frontend Logic (app.js)
   ===================================================== */

let selectedFormat = "MP3";
let currentEventSource = null;

// ── Format Selection ──────────────────────────────────
function selectFormat(fmt) {
  selectedFormat = fmt;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.getElementById(`tab-${fmt.toLowerCase()}`).classList.add("active");
}

// ── Paste from Clipboard ──────────────────────────────
async function pasteURL() {
  try {
    const text = await navigator.clipboard.readText();
    const input = document.getElementById("url-input");
    input.value = text;
    input.focus();
  } catch {
    document.getElementById("url-input").focus();
  }
}

// ── Format duration (seconds → MM:SS or HH:MM:SS) ────
function formatDuration(secs) {
  secs = Math.floor(secs);
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
  return `${m}:${String(s).padStart(2,"0")}`;
}

// ── Start Conversion ──────────────────────────────────
async function startConversion() {
  const url = document.getElementById("url-input").value.trim();
  if (!url) {
    shakeInput();
    return;
  }

  // Basic client-side domain check
  if (!/youtube\.com|youtu\.be/.test(url)) {
    showError("Link inválido", "Cole um link válido do YouTube (youtube.com ou youtu.be).");
    return;
  }

  resetSections();
  setConverting(true);
  addStep("🔍 Validando o link...");
  showSection("progress");

  try {
    const res = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, format: selectedFormat }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError("Erro ao iniciar", data.error || "Não foi possível iniciar a conversão.");
      setConverting(false);
      return;
    }

    openEventStream(data.session_id);
  } catch (err) {
    showError("Erro de conexão", "Não foi possível contactar o servidor. Verifique se ele está rodando.");
    setConverting(false);
  }
}

// ── SSE Stream ────────────────────────────────────────
function openEventStream(sessionId) {
  if (currentEventSource) currentEventSource.close();

  currentEventSource = new EventSource(`/api/events/${sessionId}`);

  currentEventSource.addEventListener("message", (e) => {
    const ev = JSON.parse(e.data);
    handleEvent(ev, sessionId);
  });

  currentEventSource.addEventListener("close", () => {
    currentEventSource.close();
    currentEventSource = null;
  });

  currentEventSource.onerror = () => {
    currentEventSource.close();
    currentEventSource = null;
    // Only show error if not already in result/error state
    const rs = document.getElementById("result-section");
    const es = document.getElementById("error-section");
    if (rs.classList.contains("hidden") && es.classList.contains("hidden")) {
      showError("Conexão perdida", "A conexão com o servidor foi interrompida.");
    }
    setConverting(false);
  };
}

// ── Event Handler ─────────────────────────────────────
function handleEvent(ev, sessionId) {
  switch (ev.type) {
    case "status":
      setProgressStatus(ev.message);
      addStep(ev.message);
      break;

    case "metadata":
      showVideoPreview(ev.thumbnail, ev.title, ev.channel, ev.duration);
      addStep(`✅ Vídeo encontrado: ${ev.title}`);
      break;

    case "progress": {
      const pct = Math.min(Math.max(ev.percent, 0), 99);
      setProgressBar(pct);
      setProgressStatus(`⬇️ Baixando... ${pct.toFixed(1)}%`);
      document.getElementById("progress-details").textContent =
        `${ev.size} — ${ev.speed} — ETA ${ev.eta}`;
      break;
    }

    case "retry":
      addStep(`🔄 ${ev.message}`);
      setProgressStatus(ev.message);
      break;

    case "success":
      setProgressBar(100);
      showResult(ev, sessionId);
      setConverting(false);
      if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }
      break;

    case "error":
      showError("Não foi possível converter", ev.message);
      setConverting(false);
      if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }
      break;

    default:
      break;
  }
}

// ── UI Helpers ────────────────────────────────────────
function showSection(name) {
  ["progress","result","error","preview"].forEach(s => {
    const id = s === "preview" ? "video-preview" : `${s}-section`;
    document.getElementById(id).classList.add("hidden");
  });
  if (name === "progress") {
    document.getElementById("progress-section").classList.remove("hidden");
  } else if (name === "result") {
    document.getElementById("result-section").classList.remove("hidden");
  } else if (name === "error") {
    document.getElementById("error-section").classList.remove("hidden");
  }
}

function setConverting(active) {
  const btn = document.getElementById("convert-btn");
  const input = document.getElementById("url-input");
  btn.disabled = active;
  input.disabled = active;
  btn.querySelector(".btn-text").textContent = active ? "Processando..." : "Converter";
}

function setProgressStatus(msg) {
  document.getElementById("progress-status").textContent = msg;
}

function setProgressBar(pct) {
  document.getElementById("progress-bar").style.width = `${pct}%`;
}

function addStep(msg) {
  const steps = document.getElementById("progress-steps");
  const el = document.createElement("div");
  el.className = "step-item";
  el.textContent = msg;
  steps.appendChild(el);
  steps.scrollTop = steps.scrollHeight;
}

function showVideoPreview(thumb, title, channel, duration) {
  document.getElementById("preview-thumb").src = thumb || "";
  document.getElementById("preview-title").textContent = title || "";
  document.getElementById("preview-meta").textContent =
    [channel, duration ? formatDuration(duration) : ""].filter(Boolean).join(" · ");
  document.getElementById("video-preview").classList.remove("hidden");
}

function showResult(ev) {
  showSection("result");
  document.getElementById("download-btn").href = ev.download_url;
  document.getElementById("download-btn").download = ev.filename;

  const metaEl = document.getElementById("result-meta");
  metaEl.innerHTML = [
    ev.filename     ? `<span>📁 ${ev.filename}</span>` : "",
    ev.filesize_mb  ? `<span>💾 ${ev.filesize_mb} MB</span>` : "",
    ev.quality      ? `<span>🎚️ ${ev.quality}</span>` : "",
    ev.duration     ? `<span>⏱️ ${formatDuration(ev.duration)}</span>` : "",
  ].filter(Boolean).join("");
}

function showError(title, msg) {
  showSection("error");
  document.getElementById("error-title").textContent = title;
  document.getElementById("error-msg").textContent = msg;
}

function shakeInput() {
  const w = document.getElementById("input-group");
  w.style.animation = "none";
  requestAnimationFrame(() => {
    w.style.animation = "shake 0.4s ease";
  });
}

function resetSections() {
  document.getElementById("progress-steps").innerHTML = "";
  document.getElementById("progress-details").textContent = "";
  setProgressBar(0);
  setProgressStatus("Iniciando...");
  document.getElementById("video-preview").classList.add("hidden");
  document.getElementById("result-section").classList.add("hidden");
  document.getElementById("error-section").classList.add("hidden");
  document.getElementById("progress-section").classList.add("hidden");
}

function resetUI() {
  resetSections();
  document.getElementById("url-input").value = "";
  document.getElementById("url-input").disabled = false;
  setConverting(false);
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }
}

// ── Keyboard shortcut: Enter to convert ──────────────
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("url-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") startConversion();
  });
});

// Inject shake keyframe dynamically
const style = document.createElement("style");
style.textContent = `
@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%      { transform: translateX(-8px); }
  40%      { transform: translateX(8px); }
  60%      { transform: translateX(-6px); }
  80%      { transform: translateX(6px); }
}`;
document.head.appendChild(style);
