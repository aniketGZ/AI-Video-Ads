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

const MOD_KEY = /Mac|iPhone|iPad/.test(navigator.platform) ? "⌘" : "Ctrl";

// ---------------------------------------------------------------- toasts
// Timers wait while you are reading (hovering the stack) or away (tab hidden). A repeat of a message on screen
// restarts its timer instead of stacking a copy. Swipe right to dismiss; a quick flick is enough.
const TOAST_MS = { error: 9000, warning: 6000 };
const toastLife = new Map();

function dismissToast(el) {
  if (!el.isConnected || el.classList.contains("is-leaving")) return;
  toastLife.delete(el);
  const below = [];
  for (let n = el.nextElementSibling; n; n = n.nextElementSibling) below.push(n);
  const before = below.map((n) => n.getBoundingClientRect().top);
  el.classList.remove("is-dragging");
  el.style.transform = "";
  el.classList.add("is-leaving");
  setTimeout(() => {
    el.remove();
    // the toasts below close the gap instead of jumping into it
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    below.forEach((n, i) => {
      if (!n.isConnected) return;
      const delta = before[i] - n.getBoundingClientRect().top;
      if (delta) n.animate([{ translate: `0 ${delta}px` }, { translate: "0 0" }], { duration: 220, easing: "cubic-bezier(0.23, 1, 0.32, 1)" });
    });
  }, 180);
}

function wireToastSwipe(el) {
  let start = null;
  el.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button") || e.button !== 0) return;
    start = { x: e.clientX, t: e.timeStamp, id: e.pointerId };
    el.setPointerCapture(e.pointerId);
  });
  el.addEventListener("pointermove", (e) => {
    if (!start || e.pointerId !== start.id) return;
    const dx = e.clientX - start.x;
    if (Math.abs(dx) < 4 && !el.classList.contains("is-dragging")) return;
    el.classList.add("is-dragging");
    // free to the right, the way it leaves; resists to the left, where there is nothing to do
    el.style.transform = `translateX(${dx > 0 ? dx : dx * 0.15}px)`;
  });
  const end = (e) => {
    if (!start || e.pointerId !== start.id) return;
    const dx = e.clientX - start.x;
    const velocity = dx / Math.max(e.timeStamp - start.t, 1);
    start = null;
    if (dx > 72 || (dx > 8 && velocity > 0.11)) return dismissToast(el);
    el.classList.remove("is-dragging");
    el.style.transform = "";
  };
  el.addEventListener("pointerup", end);
  el.addEventListener("pointercancel", end);
}

function notify(message, type = "info") {
  const stack = document.getElementById("toasts");
  const twin = Array.from(stack.children).find((t) => t.dataset.message === message && !t.classList.contains("is-leaving"));
  if (twin) {
    toastLife.get(twin).left = TOAST_MS[type] || 4500;
    return;
  }
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.dataset.message = message;
  el.setAttribute("role", type === "error" ? "alert" : "status");
  const text = document.createElement("span");
  text.className = "toast-text";
  text.textContent = message;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "toast-close";
  close.setAttribute("aria-label", "Dismiss");
  close.innerHTML = '<i class="fa-solid fa-xmark"></i>';
  close.addEventListener("click", () => dismissToast(el));
  el.append(text, close);
  stack.appendChild(el);
  toastLife.set(el, { left: TOAST_MS[type] || 4500 });
  wireToastSwipe(el);
  // The oldest quiet toast gives way once the stack is full; errors stay until read
  const live = Array.from(stack.children).filter((t) => !t.classList.contains("is-leaving"));
  if (live.length > 4) dismissToast(live.find((t) => !t.classList.contains("error")) || live[0]);
  startToastClock();
}

let toastClock = null;
function startToastClock() {
  if (toastClock) return;
  let last = performance.now();
  toastClock = setInterval(() => {
    const now = performance.now();
    const elapsed = now - last;
    last = now;
    if (!toastLife.size) {
      clearInterval(toastClock);
      toastClock = null;
      return;
    }
    if (document.hidden || document.getElementById("toasts").matches(":hover")) return;
    toastLife.forEach((life, el) => {
      life.left -= elapsed;
      if (life.left <= 0) dismissToast(el);
    });
  }, 200);
}

async function readErrorDetail(res, fallback) {
  // The server refused a feature this plan doesn't include: offer the upgrade, not just an error
  if (res.status === 403 && res.headers.get("x-upgrade-required")) openUpgradeDialog();
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

// Every network call needs the key; send people to the key dialog instead of letting the request fail.
// Once the key is saved the interrupted action carries on, so nobody has to press the same button twice.
let afterKeySaved = null;
function requireKey(retry) {
  if (getGeminiKey()) return true;
  const from = document.activeElement;
  afterKeySaved = retry || (() => {
    const form = from && from.closest && from.closest("form");
    if (form && form.classList.contains("composer")) form.requestSubmit();
    else if (from && from.tagName === "BUTTON" && from.isConnected) from.click();
  });
  openKeyDialog("Add your Gemini API key to continue.");
  return false;
}

// ---------------------------------------------------------------- confirm dialog
// In-page replacement for window.confirm(), which some embedded browsers block (returning false).
// With { skipKey }, the dialog offers "Don't ask again this session"; once ticked and confirmed,
// later calls with the same key resolve true straight away until the tab is closed.
function askConfirm(title, text, okLabel = "Continue", { skipKey } = {}) {
  const storeKey = skipKey && `confirm_skip_${skipKey}`;
  if (storeKey) {
    try {
      if (sessionStorage.getItem(storeKey) === "1") return Promise.resolve(true);
    } catch (e) { /* storage blocked: just ask */ }
  }
  const dialog = document.getElementById("confirm_dialog");
  const skipRow = document.getElementById("confirm_skip_row");
  const skip = document.getElementById("confirm_skip");
  document.getElementById("confirm_title").textContent = title;
  document.getElementById("confirm_text").textContent = text || "";
  document.getElementById("confirm_ok").textContent = okLabel;
  skipRow.hidden = !storeKey;
  skip.checked = false;
  dialog.returnValue = "";
  dialog.showModal();
  document.getElementById("confirm_ok").focus();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => {
      const ok = dialog.returnValue === "ok";
      if (ok && storeKey && skip.checked) {
        try { sessionStorage.setItem(storeKey, "1"); } catch (e) { /* storage blocked: keep asking */ }
      }
      resolve(ok);
    }, { once: true });
  });
}

// ---------------------------------------------------------------- API key dialog
function updateKeyDot() {
  const ok = !!getGeminiKey();
  document.getElementById("key_dot").classList.toggle("ok", ok);
  document.getElementById("key_btn").classList.toggle("is-missing", !ok);
  document.getElementById("key_label").textContent = ok ? "API key" : "Add API key";
  const state = document.getElementById("key_state");
  if (state) state.textContent = ok ? "Saved" : "";
}

function setKeyVisible(visible) {
  const toggle = document.getElementById("key_toggle");
  document.getElementById("key_input").type = visible ? "text" : "password";
  toggle.setAttribute("aria-pressed", String(visible));
  toggle.setAttribute("aria-label", visible ? "Hide key" : "Show key");
  toggle.querySelector("i").className = visible ? "fa-regular fa-eye-slash" : "fa-regular fa-eye";
}

const KEY_DIALOG_INTRO = document.querySelector("#key_dialog h3").textContent;
function openKeyDialog(title) {
  const dialog = document.getElementById("key_dialog");
  document.querySelector("#key_dialog h3").textContent = typeof title === "string" ? title : KEY_DIALOG_INTRO;
  document.getElementById("key_input").value = getGeminiKey();
  setKeyVisible(false);
  dialog.showModal();
  document.getElementById("key_input").focus();
}

document.getElementById("key_btn").addEventListener("click", () => openKeyDialog());
document.getElementById("key_toggle").addEventListener("click", () => setKeyVisible(document.getElementById("key_input").type === "password"));
document.getElementById("key_cancel").addEventListener("click", () => document.getElementById("key_dialog").close());
let keyJustSaved = false;
document.getElementById("key_form").addEventListener("submit", () => {
  setGeminiKey(document.getElementById("key_input").value);
  keyJustSaved = !!getGeminiKey();
  notify(keyJustSaved ? "API key saved." : "API key removed.", "success");
});
document.getElementById("key_dialog").addEventListener("close", () => {
  const retry = keyJustSaved ? afterKeySaved : null;
  keyJustSaved = false;
  afterKeySaved = null;
  if (retry) retry();
});
updateKeyDot();

// ---------------------------------------------------------------- dialogs
// A click on the backdrop dismisses, as long as the press started there too (not a text selection that ended there).
let pressedBackdrop = false;
const onBackdrop = (e) => {
  const d = e.target;
  if (!d || d.tagName !== "DIALOG" || !d.open || d.classList.contains("viewer")) return false;
  const r = d.getBoundingClientRect();
  return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
};
document.addEventListener("pointerdown", (e) => { pressedBackdrop = onBackdrop(e); });
document.addEventListener("click", (e) => {
  if (pressedBackdrop && onBackdrop(e)) e.target.close();
  pressedBackdrop = false;
});

// A file dropped beside a dropzone would otherwise replace the whole app, and the campaign with it
["dragover", "drop"].forEach((type) => document.addEventListener(type, (e) => {
  if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files")) e.preventDefault();
}));

// ---------------------------------------------------------------- sliding selection
// A shared thumb moves between the options, so the eye follows the change instead of finding it again.
// It sits on the active button however that button became active, and re-measures when fonts or layout move.
function slidingThumb(group) {
  const thumb = document.createElement("span");
  thumb.className = "seg-thumb";
  thumb.setAttribute("aria-hidden", "true");
  group.prepend(thumb);
  group.classList.add("has-thumb");
  const place = () => {
    const active = Array.from(group.children).find((c) => c.tagName === "BUTTON" && c.classList.contains("active"));
    if (!active || !active.offsetWidth) return;
    thumb.style.width = `${active.offsetWidth}px`;
    thumb.style.height = `${active.offsetHeight}px`;
    thumb.style.transform = `translate(${active.offsetLeft}px, ${active.offsetTop}px)`;
    if (!thumb.classList.contains("is-live")) requestAnimationFrame(() => requestAnimationFrame(() => thumb.classList.add("is-live")));
  };
  new MutationObserver(place).observe(group, { subtree: true, attributes: true, attributeFilter: ["class"] });
  new ResizeObserver(place).observe(group);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);
  place();
}

document.querySelectorAll(".nav, .segmented:not(.seg-list)").forEach(slidingThumb);

// ---------------------------------------------------------------- views
const VIEWS = ["campaign", "image", "video", "batch"];

const viewScroll = {};
let currentView = null;

function showView(name, { push = false } = {}) {
  if (currentView) viewScroll[currentView] = window.scrollY; // each view keeps your place in it
  currentView = name;
  document.querySelectorAll("[data-view-panel]").forEach((p) => { p.hidden = p.dataset.viewPanel !== name; });
  window.scrollTo(0, viewScroll[name] || 0);
  document.querySelectorAll(".nav-btn").forEach((b) => {
    const on = b.dataset.view === name;
    b.classList.toggle("active", on);
    if (on) {
      b.setAttribute("aria-current", "page");
      b.scrollIntoView({ block: "nearest", inline: "nearest" }); // the tab row scrolls on phones
    } else {
      b.removeAttribute("aria-current");
    }
  });
  try { localStorage.setItem("ad_studio_view", name); } catch (e) { /* ignore */ }
  // Each studio has its own address, so Back works and a tab can be reopened where it was
  if (push && location.hash !== `#${name}`) history.pushState(null, "", `#${name}`);
  window.dispatchEvent(new CustomEvent("viewchange", { detail: name }));
}

document.querySelectorAll(".nav-btn").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view, { push: true })));
window.addEventListener("popstate", () => {
  const view = location.hash.slice(1);
  showView(VIEWS.includes(view) ? view : "campaign");
});

// ---------------------------------------------------------------- segmented controls
// Wires a .segmented group; returns a getter for the active button's data value.
function segmented(id, attr, onChange) {
  const group = document.getElementById(id);
  const mark = () => group.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.classList.contains("active"))));
  mark();
  group.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn || !group.contains(btn)) return;
    group.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
    mark();
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

  let shown = 0;
  function render() {
    thumbsEl.querySelectorAll("img").forEach((img) => URL.revokeObjectURL(img.src));
    thumbsEl.innerHTML = "";
    files.forEach((file, i) => {
      const wrap = document.createElement("div");
      wrap.className = i >= shown ? "thumb is-new" : "thumb"; // only what was just added arrives
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
    shown = files.length;
  }

  function add(list) {
    const dropped = Array.from(list || []);
    const images = dropped.filter((f) => f.type.startsWith("image/"));
    if (dropped.length && !images.length) notify("That file isn't an image, so it wasn't added.", "warning");
    if (max > 1 && files.length + images.length > max) notify(`Only ${max} images can be used here, so the extras were left out.`, "info");
    if (max === 1 && images.length) shown = 0;
    files = max === 1 ? images.slice(0, 1).concat(images.length ? [] : files) : files.concat(images).slice(0, max);
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

// ---------------------------------------------------------------- plan
// Every tab opens for every plan. A feature the plan leaves out is asked for at the moment it is
// used (requireFeature opens the upgrade dialog); the server refuses it too (HTTP 403).
let planFeatures = null; // null = unknown (offline/old server): leave everything open

async function loadPlan() {
  try {
    const res = await fetch("/api/plan");
    if (res.ok) planFeatures = (await res.json()).features || [];
  } catch (e) { /* keep unknown */ }
}

function hasFeature(name) {
  return planFeatures === null || planFeatures.includes(name);
}

function applyPlanLocks() {
  const locked = !hasFeature("campaign_manager");
  const btn = document.querySelector('.nav-btn[data-view="campaign"]');
  if (btn && locked && !btn.querySelector(".nav-plan-tag")) {
    btn.insertAdjacentHTML("beforeend", '<span class="nav-plan-tag">Pro</span>');
    btn.title = "Campaign builder: Pro and Studio plans";
  }
  // A link kept from the upgrade page or the upgrade dialog goes back into the field
  try {
    const pending = localStorage.getItem("pending_brand_url");
    const field = document.getElementById("brand_url");
    if (pending && field && !field.value) {
      field.value = pending;
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (pending && !locked) localStorage.removeItem("pending_brand_url");
  } catch (e) { /* storage blocked: nothing to fill */ }
}

// ---------------------------------------------------------------- upgrade dialog
let plansCache = null;

async function fillUpgradePlans() {
  if (!plansCache) {
    try {
      const res = await fetch("/api/plans");
      if (res.ok) plansCache = (await res.json()).plans;
    } catch (e) { /* keep the prices written in the page */ }
  }
  if (!plansCache) return;
  const nf = new Intl.NumberFormat("en-US");
  for (const key of ["pro", "studio"]) {
    const p = plansCache[key];
    if (!p) continue;
    const price = document.querySelector(`#upgrade_dialog [data-price="${key}"]`);
    const credits = document.querySelector(`#upgrade_dialog [data-credits="${key}"]`);
    if (price) price.innerHTML = `$${nf.format(p.price_usd_month)}<small>/mo</small>`;
    if (credits) credits.textContent = `${nf.format(p.credits)} credits a month`;
  }
}

function openUpgradeDialog({ savedUrl = null } = {}) {
  const dlg = document.getElementById("upgrade_dialog");
  if (!dlg) return;
  if (savedUrl) {
    try { localStorage.setItem("pending_brand_url", savedUrl); } catch (e) { /* not kept */ }
  }
  document.getElementById("upgrade_lede").textContent = savedUrl
    ? "Your link is saved. Upgrade and the campaign builder picks up right where you left off."
    : "Research the brand, study its competitors' ads and render a full campaign from one link.";
  fillUpgradePlans();
  if (!dlg.open) dlg.showModal();
  const video = dlg.querySelector("video");
  if (video && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) video.play().catch(() => {});
}

// Call before a gated action; returns false (and asks for the upgrade) when the plan lacks it
function requireFeature(name, { savedUrl = null } = {}) {
  if (hasFeature(name)) return true;
  openUpgradeDialog({ savedUrl });
  return false;
}

(function wireUpgradeDialog() {
  const dlg = document.getElementById("upgrade_dialog");
  if (!dlg) return;
  const cta = document.getElementById("upgrade_cta");
  dlg.querySelectorAll('input[name="upgrade_plan"]').forEach((r) => r.addEventListener("change", () => {
    const plan = r.value;
    cta.href = `/upgrade/checkout?plan=${plan}`;
    const label = plan === "studio" ? "Studio" : "Pro";
    cta.textContent = `Upgrade to ${label}`;
    document.getElementById("upgrade_title").textContent = `Build this campaign on ${label}`;
  }));
  document.getElementById("upgrade_close").addEventListener("click", () => dlg.close());
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); }); // click on the backdrop
  dlg.addEventListener("close", () => dlg.querySelector("video")?.pause());
})();

// The example fan plays its reel only while the Campaign tab is showing
window.addEventListener("viewchange", (e) => {
  const reel = document.querySelector("#campaign_showcase video");
  if (!reel) return;
  if (e.detail === "campaign" && !document.getElementById("campaign_showcase").hidden
      && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) reel.play().catch(() => {});
  else reel.pause();
});

// Restore the last view after the other scripts have registered their listeners
window.addEventListener("DOMContentLoaded", async () => {
  await loadPlan();
  applyPlanLocks();
  let view = location.hash.slice(1);
  if (!VIEWS.includes(view)) {
    try { view = localStorage.getItem("ad_studio_view") || "campaign"; } catch (e) { view = "campaign"; }
  }
  showView(VIEWS.includes(view) ? view : "campaign");
});
