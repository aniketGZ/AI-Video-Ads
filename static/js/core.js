// Shared helpers: API key, toasts, fetch errors, job polling, view switching and image dropzones.
const GEMINI_KEY_STORAGE = "gemini_api_key";

function getGeminiKey() {
  try {
    return (localStorage.getItem(GEMINI_KEY_STORAGE) || "").trim();
  } catch (e) {
    return "";
  }
}

function setGeminiKey(value) {
  try {
    localStorage.setItem(GEMINI_KEY_STORAGE, (value || "").trim());
  } catch (e) {
    notify("Could not save the key in this browser.", "error");
  }
  updateKeyDot();
}

function apiHeaders(extra = {}) {
  const key = getGeminiKey();
  return key ? { ...extra, "x-api-key": key } : { ...extra };
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function notify(message, type = "info") {
  const stack = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => el.remove(), type === "error" ? 8000 : 4500);
}

async function readErrorDetail(res, fallback) {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
  } catch (e) { /* not JSON */ }
  return `${fallback} (HTTP ${res.status})`;
}

async function pollJob(jobId, { intervalMs = 5000, maxMs = 30 * 60 * 1000, onProgress } = {}) {
  const started = Date.now();
  let failures = 0;
  while (Date.now() - started < maxMs) {
    await new Promise((r) => setTimeout(r, intervalMs));
    let res;
    try {
      res = await fetch(`/api/video-status/${encodeURIComponent(jobId)}`);
    } catch (e) {
      if (++failures >= 5) throw new Error("Lost connection to the server.");
      continue;
    }
    if (!res.ok) {
      if (++failures >= 5) throw new Error(await readErrorDetail(res, "Could not check the render"));
      continue;
    }
    failures = 0;
    const job = await res.json();
    if (job.status === "success") return job;
    if (job.status === "failed") throw new Error(job.error || "Rendering failed.");
    if (onProgress) onProgress(job);
  }
  throw new Error("Rendering is taking longer than expected. Please try again later.");
}

// ---------------------------------------------------------------- render loader
// A frame in the ad's aspect ratio whose tiles develop in a diagonal wave under a sweeping scan line,
// with the status text and an elapsed timer. Calling it again on the same host only swaps the text,
// so progress updates keep the timer and the animation running instead of restarting them.
// { ratio: "4:5", fill: true } fills a host that already has the ad's shape (a campaign card).
function renderLoader(host, text, { ratio = "1:1", fill = false } = {}) {
  if (typeof host === "string") host = document.getElementById(host);
  if (!host) return;
  const existing = host.querySelector(".render-loader");
  if (existing) {
    existing.querySelector(".rl-label").textContent = text;
    return;
  }
  const [w, h] = String(ratio).split(":").map(Number);
  const cols = w >= h ? 8 : 6;
  const rows = Math.max(3, Math.round((cols * h) / w));
  let tiles = "";
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) tiles += `<i style="--d:${r + c}"></i>`;
  }
  // The frame's height is capped, so its width follows the ratio
  const size = fill ? "" : `width: min(100%, ${Math.round((340 * w) / h)}px);`;
  host.innerHTML = `
    <div class="render-loader${fill ? " is-fill" : ""}" role="status">
      <div class="rl-frame" style="aspect-ratio: ${w} / ${h}; ${size}">
        <div class="rl-tiles" style="grid-template-columns: repeat(${cols}, 1fr)">${tiles}</div>
        <div class="rl-scan"></div>
      </div>
      <div class="rl-meta"><span class="rl-label">${escapeHtml(text)}</span><span class="rl-time" data-start="${Date.now()}">0:00</span></div>
    </div>`;
  tickRenderTimers();
}

let renderTimer = null;
function tickRenderTimers() {
  const clocks = document.querySelectorAll(".rl-time[data-start]");
  clocks.forEach((el) => {
    const s = Math.floor((Date.now() - Number(el.dataset.start)) / 1000);
    el.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  });
  if (clocks.length && !renderTimer) renderTimer = setInterval(tickRenderTimers, 1000);
  if (!clocks.length && renderTimer) { clearInterval(renderTimer); renderTimer = null; }
}

// Plays the top-to-bottom "develop" reveal once on media that just finished rendering.
function revealRendered(el) {
  if (!el) return;
  el.classList.remove("rl-develop");
  void el.offsetWidth; // restart the animation if it already ran
  el.classList.add("rl-develop");
  el.addEventListener("animationend", () => el.classList.remove("rl-develop"), { once: true });
}

// Every network call needs the key; send people to the key dialog instead of letting the request fail.
function requireKey() {
  if (getGeminiKey()) return true;
  notify("Add your Gemini API key first.", "warning");
  openKeyDialog();
  return false;
}

// ---------------------------------------------------------------- confirm dialog
// In-page replacement for window.confirm(), which some embedded browsers block (returning false).
function askConfirm(title, text, okLabel = "Continue") {
  const dialog = document.getElementById("confirm_dialog");
  document.getElementById("confirm_title").textContent = title;
  document.getElementById("confirm_text").textContent = text || "";
  document.getElementById("confirm_ok").textContent = okLabel;
  dialog.returnValue = "";
  dialog.showModal();
  document.getElementById("confirm_ok").focus();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true });
  });
}

// ---------------------------------------------------------------- API key dialog
function updateKeyDot() {
  const ok = !!getGeminiKey();
  document.getElementById("key_dot").classList.toggle("ok", ok);
  const state = document.getElementById("key_state");
  if (state) state.textContent = ok ? "Saved" : "Not set";
}

function openKeyDialog() {
  const dialog = document.getElementById("key_dialog");
  document.getElementById("key_input").value = getGeminiKey();
  dialog.showModal();
}

document.getElementById("key_btn").addEventListener("click", openKeyDialog);
document.getElementById("key_cancel").addEventListener("click", () => document.getElementById("key_dialog").close());
document.getElementById("key_form").addEventListener("submit", () => {
  setGeminiKey(document.getElementById("key_input").value);
  notify(getGeminiKey() ? "API key saved." : "API key removed.", "success");
});
updateKeyDot();

// ---------------------------------------------------------------- views
function showView(name) {
  document.querySelectorAll("[data-view-panel]").forEach((p) => { p.hidden = p.dataset.viewPanel !== name; });
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  try { localStorage.setItem("ad_studio_view", name); } catch (e) { /* ignore */ }
  window.dispatchEvent(new CustomEvent("viewchange", { detail: name }));
}

document.querySelectorAll(".nav-btn").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));

// ---------------------------------------------------------------- segmented controls
// Wires a .segmented group; returns a getter for the active button's data value.
function segmented(id, attr, onChange) {
  const group = document.getElementById(id);
  group.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn || !group.contains(btn)) return;
    group.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
    if (onChange) onChange(btn.dataset[attr]);
  });
  return () => (group.querySelector("button.active") || {}).dataset?.[attr];
}

// ---------------------------------------------------------------- image dropzones
// Wires a dropzone + hidden file input + thumbnail strip. Returns { files(), clear() }.
function imageDropzone({ zone, input, thumbs, max = 4 }) {
  const zoneEl = document.getElementById(zone);
  const inputEl = document.getElementById(input);
  const thumbsEl = document.getElementById(thumbs);
  let files = [];

  function render() {
    thumbsEl.innerHTML = "";
    files.forEach((file, i) => {
      const wrap = document.createElement("div");
      wrap.className = "thumb";
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.alt = file.name;
      const rm = document.createElement("button");
      rm.type = "button";
      rm.setAttribute("aria-label", `Remove ${file.name}`);
      rm.innerHTML = '<i class="fa-solid fa-xmark"></i>';
      rm.addEventListener("click", (e) => {
        e.stopPropagation();
        files.splice(i, 1);
        render();
      });
      wrap.append(img, rm);
      thumbsEl.appendChild(wrap);
    });
  }

  function add(list) {
    const images = Array.from(list || []).filter((f) => f.type.startsWith("image/"));
    files = max === 1 ? images.slice(0, 1) : files.concat(images).slice(0, max);
    if (images.length && files.length === max && max > 1) notify(`Up to ${max} images are used.`, "info");
    render();
  }

  zoneEl.addEventListener("click", (e) => { if (!e.target.closest(".thumb")) inputEl.click(); });
  zoneEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputEl.click(); }
  });
  inputEl.addEventListener("change", () => { add(inputEl.files); inputEl.value = ""; });
  zoneEl.addEventListener("dragover", (e) => { e.preventDefault(); zoneEl.classList.add("dragover"); });
  zoneEl.addEventListener("dragleave", () => zoneEl.classList.remove("dragover"));
  zoneEl.addEventListener("drop", (e) => {
    e.preventDefault();
    zoneEl.classList.remove("dragover");
    add(e.dataTransfer.files);
  });

  return {
    files: () => files.slice(),
    clear: () => { files = []; render(); },
    setMax: (m) => {
      max = Number(m) || 4;
      if (files.length > max) {
        files = files.slice(0, max);
        render();
      }
    },
  };
}

// Restore the last view after the other scripts have registered their listeners
window.addEventListener("DOMContentLoaded", () => {
  let view = "campaign";
  try { view = localStorage.getItem("ad_studio_view") || "campaign"; } catch (e) { /* ignore */ }
  showView(["campaign", "image", "video", "batch"].includes(view) ? view : "campaign");
});
