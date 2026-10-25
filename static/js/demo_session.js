/**
 * Live Demo Session & Backend Activity Tracer Controller
 * Manages:
 * - Interactive live demo sessions with API key input
 * - Automatic tracking of user and agent steps
 * - Real-time engineering backend telemetry (LLM prompts, raw outputs, Playwright, ffmpeg, Critic QA)
 * - 1-click Tech Team PDF and JSON exports
 */

(function () {
  let sessionActive = false;
  let sessionId = null;
  let timerInterval = null;
  let startEpoch = null;
  let loggedStepCount = 0;
  let activeTechFilter = "ALL";
  let cachedTechEvents = [];

  // Initialize UI elements when DOM is ready
  document.addEventListener("DOMContentLoaded", initDemoSession);

  function initDemoSession() {
    createDemoUI();
    createTechConsoleUI();
    checkActiveSession();
    bindUserActivityTracking();
  }

  function createDemoUI() {
    // 1. Add Live Demo and Tech Trace buttons to topbar
    const topbarInner = document.querySelector(".sidebar-tools") || document.querySelector(".topbar-inner");
    if (topbarInner) {
      // Tech Trace Button
      const techBtn = document.createElement("button");
      techBtn.type = "button";
      techBtn.className = "btn btn-sm btn-ghost tool-btn";
      techBtn.id = "btn_tech_console";
      techBtn.setAttribute("aria-label", "Tech trace");
      techBtn.title = "Tech trace";
      techBtn.innerHTML = `<i class="fa-solid fa-terminal"></i><span class="tool-label">Tech trace</span>`;
      techBtn.addEventListener("click", openTechConsole);

      // Demo Session Button
      const demoBtn = document.createElement("button");
      demoBtn.type = "button";
      demoBtn.className = "btn btn-sm btn-demo tool-btn";
      demoBtn.setAttribute("aria-label", "Live demo");
      demoBtn.title = "Live demo";
      demoBtn.id = "btn_demo_session";
      demoBtn.innerHTML = `<span class="demo-dot" id="demo_dot"></span><span class="tool-label" id="demo_btn_label">Live demo</span>`;
      demoBtn.addEventListener("click", onDemoBtnClick);

      const keyBtn = document.getElementById("key_btn");
      if (keyBtn) {
        topbarInner.insertBefore(techBtn, keyBtn);
        topbarInner.insertBefore(demoBtn, keyBtn);
      } else {
        topbarInner.appendChild(techBtn);
        topbarInner.appendChild(demoBtn);
      }
    }

    // 2. Add Floating Live Recording Bar
    const recBar = document.createElement("div");
    recBar.className = "demo-recording-bar";
    recBar.id = "demo_recording_bar";
    recBar.hidden = true;
    recBar.innerHTML = `
      <div class="demo-bar-inner">
        <div class="demo-pulse-indicator"></div>
        <span class="demo-bar-title"><span class="demo-dot recording"></span> Recording live demo</span>
        <span class="demo-bar-divider">|</span>
        <span class="demo-bar-stat"><i class="fa-regular fa-clock"></i> <span id="demo_timer">00:00</span></span>
        <span class="demo-bar-stat"><i class="fa-solid fa-shoe-prints"></i> <span id="demo_step_counter">0 steps</span></span>
        <span class="demo-bar-brand" id="demo_brand_pill" hidden></span>
        <div class="demo-bar-actions">
          <button type="button" class="btn btn-sm btn-ghost" id="btn_bar_tech_view">
            <i class="fa-solid fa-terminal"></i> Traces
          </button>
          <button type="button" class="btn btn-sm btn-danger" id="btn_end_demo_session">
            <i class="fa-solid fa-stop"></i> End Session & Generate PDF
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(recBar);

    // 3. Add Demo Start Modal
    const startDialog = document.createElement("dialog");
    startDialog.id = "demo_start_dialog";
    startDialog.className = "demo-dialog";
    startDialog.innerHTML = `
      <form method="dialog" class="demo-dialog-body" id="demo_start_form">
        <div class="demo-modal-head">
          <div class="demo-icon-badge"><i class="fa-solid fa-video"></i></div>
          <div>
            <h3>Start Live Demo Session</h3>
            <p>Every step taken by you and the autonomous agents will be recorded into a publication-grade PDF report.</p>
          </div>
        </div>

        <div class="field" style="margin-top:14px;">
          <label class="label" for="demo_api_key_input">Gemini API Key</label>
          <input type="password" class="input" id="demo_api_key_input" placeholder="AIzaSy..." autocomplete="off">
          <span class="hint">Powers research, Gemini Vision product locks, prompt writers, and Omni Flash renders.</span>
        </div>

        <div class="field">
          <label class="label" for="demo_name_input">Session Title / Topic</label>
          <input type="text" class="input" id="demo_name_input" value="End-to-End Campaign Creative Demo">
        </div>

        <div class="field">
          <label class="label">Quick Preset Brand (or use current)</label>
          <div class="demo-presets-row">
            <button type="button" class="btn btn-sm btn-preset" data-brand="https://letshyphen.com/">HYPHEN Skincare</button>
            <button type="button" class="btn btn-sm btn-preset" data-brand="https://greensoul.online/">GreenSoul Ergonomics</button>
            <button type="button" class="btn btn-sm btn-preset" data-brand="https://arrivfresh.com/">Arriv Fresh</button>
          </div>
        </div>

        <div class="demo-modal-foot">
          <button type="button" class="btn btn-ghost" id="demo_start_cancel">Cancel</button>
          <button type="submit" class="btn btn-primary" id="demo_start_submit"><i class="fa-solid fa-circle-play"></i> Start Recording Live Demo</button>
        </div>
      </form>
    `;
    document.body.appendChild(startDialog);

    // 4. Add Demo End Modal
    const endDialog = document.createElement("dialog");
    endDialog.id = "demo_end_dialog";
    endDialog.className = "demo-dialog";
    endDialog.innerHTML = `
      <div class="demo-dialog-body" id="demo_end_body">
        <div class="demo-modal-head">
          <div class="demo-icon-badge success"><i class="fa-solid fa-check"></i></div>
          <div>
            <h3>Live Demo Session Completed!</h3>
            <p id="demo_end_summary_text">Session trace compiled and PDF report generated successfully.</p>
          </div>
        </div>

        <div class="demo-stats-summary" id="demo_end_stats"></div>

        <div class="demo-modal-foot">
          <button type="button" class="btn btn-ghost" id="demo_end_close">Close</button>
          <a href="#" class="btn btn-primary" id="demo_end_download_btn" target="_blank">
            <i class="fa-solid fa-file-pdf"></i> Download Session PDF Report
          </a>
        </div>
      </div>
    `;
    document.body.appendChild(endDialog);

    // Bind event listeners
    document.getElementById("btn_end_demo_session").addEventListener("click", endDemoSession);
    document.getElementById("btn_bar_tech_view").addEventListener("click", openTechConsole);
    document.getElementById("demo_start_cancel").addEventListener("click", () => startDialog.close());
    document.getElementById("demo_end_close").addEventListener("click", () => endDialog.close());

    document.getElementById("demo_start_form").addEventListener("submit", (e) => {
      e.preventDefault();
      const apiKey = document.getElementById("demo_api_key_input").value.trim();
      const sessionName = document.getElementById("demo_name_input").value.trim();
      const brandUrl = document.getElementById("brand_url") ? document.getElementById("brand_url").value.trim() : "";
      startDemoSession(sessionName, apiKey, brandUrl);
      startDialog.close();
    });

    document.querySelectorAll(".btn-preset").forEach((b) => {
      b.addEventListener("click", () => {
        const url = b.getAttribute("data-brand");
        const brandInput = document.getElementById("brand_url");
        if (brandInput) {
          brandInput.value = url;
          brandInput.dispatchEvent(new Event("input", { bubbles: true }));
        }
        notify(`Selected preset: ${url}`, "info");
      });
    });
  }

  function createTechConsoleUI() {
    const techDialog = document.createElement("dialog");
    techDialog.id = "tech_console_dialog";
    techDialog.className = "tech-dialog";
    techDialog.innerHTML = `
      <div class="tech-dialog-body">
        <div class="tech-head">
          <div>
            <h3><i class="fa-solid fa-terminal"></i> Backend Activity & Prompt Trace Inspector</h3>
            <span style="font-size:0.75rem; color:var(--text-2);">Granular telemetry of raw prompts, responses, tool calls, and critic QA loops.</span>
          </div>
          <div style="display:flex; gap:8px;">
            <a href="/api/demo-session/tech-trace/export-json" class="btn btn-sm btn-ghost" download="backend_telemetry_traces.json">
              <i class="fa-solid fa-download"></i> Export JSON
            </a>
            <a href="/api/demo-session/tech-trace/export-pdf" class="btn btn-sm btn-primary" target="_blank">
              <i class="fa-solid fa-file-pdf"></i> Download Tech PDF
            </a>
            <button type="button" class="btn btn-sm btn-ghost" id="tech_close_btn"><i class="fa-solid fa-xmark"></i></button>
          </div>
        </div>

        <div class="tech-filter-bar">
          <button type="button" class="tech-tab active" data-category="ALL">All Traces</button>
          <button type="button" class="tech-tab" data-category="LLM_PROMPT">LLM Prompts & Responses</button>
          <button type="button" class="tech-tab" data-category="CRITIC_QA">Critic QA Rubrics</button>
          <button type="button" class="tech-tab" data-category="BROWSER_PLAYWRIGHT">Playwright Browser</button>
          <button type="button" class="tech-tab" data-category="MEDIA_FFMPEG">ffmpeg Hook Slices</button>
          <button type="button" class="tech-tab" data-category="RENDER_GPU">GPU Renders</button>
        </div>

        <div class="tech-content-list" id="tech_event_list">
          <div style="text-align:center; padding:20px; color:var(--text-3);">Loading telemetry events...</div>
        </div>
      </div>
    `;
    document.body.appendChild(techDialog);

    document.getElementById("tech_close_btn").addEventListener("click", () => techDialog.close());

    techDialog.querySelectorAll(".tech-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        techDialog.querySelectorAll(".tech-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        activeTechFilter = tab.getAttribute("data-category");
        renderTechEvents();
      });
    });
  }

  async function openTechConsole() {
    const dialog = document.getElementById("tech_console_dialog");
    if (!dialog) return;
    dialog.showModal();
    await loadTechEvents();
  }

  async function loadTechEvents() {
    const listEl = document.getElementById("tech_event_list");
    listEl.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-3);"><span class="spinner" style="width:14px; height:14px; border-width:2px;"></span> Loading telemetry traces...</div>`;

    try {
      const res = await fetch("/api/demo-session/tech-trace/events");
      if (!res.ok) throw new Error("Could not fetch telemetry traces");
      const data = await res.json();
      cachedTechEvents = data.events || [];
      renderTechEvents();
    } catch (e) {
      listEl.innerHTML = `<div style="color:var(--danger); padding:20px; text-align:center;">Failed to load traces: ${e.message}</div>`;
    }
  }

  function renderTechEvents() {
    const listEl = document.getElementById("tech_event_list");
    if (!listEl) return;

    let filtered = cachedTechEvents;
    if (activeTechFilter !== "ALL") {
      filtered = cachedTechEvents.filter((e) => e.category === activeTechFilter);
    }

    if (!filtered.length) {
      listEl.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-3);">No traces recorded for this category yet.</div>`;
      return;
    }

    let html = "";
    filtered.slice().reverse().forEach((ev) => {
      const cat = ev.category || "SYSTEM";
      let detailsHtml = "";

      if (cat === "LLM_PROMPT") {
        detailsHtml = `
          <div class="tech-code-title">
            <span>Model: ${ev.model} · Latency: ${ev.duration_ms}ms · Tokens: ${ev.token_metrics ? ev.token_metrics.total_tokens : '-'}</span>
            <button type="button" class="btn-copy-code" onclick="navigator.clipboard.writeText(${JSON.stringify(ev.prompt_content)}); notify('Prompt copied to clipboard', 'info');">Copy Prompt</button>
          </div>
          <div class="tech-code-block"><pre>${escapeHtml(ev.prompt_content)}</pre></div>
          <div class="tech-code-title" style="color:var(--success); margin-top:6px;">
            <span>Model Response:</span>
            <button type="button" class="btn-copy-code" onclick="navigator.clipboard.writeText(${JSON.stringify(ev.response_content)}); notify('Response copied to clipboard', 'info');">Copy Response</button>
          </div>
          <div class="tech-code-block" style="border-left:2px solid var(--success);"><pre>${escapeHtml(ev.response_content)}</pre></div>
        `;
      } else if (cat === "CRITIC_QA") {
        const scores = ev.rubric_scores || {};
        const scoreTags = Object.entries(scores).map(([k, v]) => `<span class="stat-tag">${k}: ${v}</span>`).join(" ");
        detailsHtml = `
          <div style="margin-bottom:6px;">${scoreTags}</div>
          <div class="tech-code-title"><span>Prompt Evaluated:</span></div>
          <div class="tech-code-block"><pre>${escapeHtml(ev.prompt_text)}</pre></div>
          <div style="font-size:0.75rem; color:var(--text-2); margin-top:4px;"><strong>Feedback:</strong> ${escapeHtml(ev.rewrite_feedback)}</div>
        `;
      } else if (cat === "BROWSER_PLAYWRIGHT") {
        detailsHtml = `
          <div style="font-size:0.75rem; margin-bottom:4px;"><strong>Target URL:</strong> <code>${escapeHtml(ev.url)}</code></div>
          <div class="tech-code-title"><span>Executed DOM Evaluator:</span></div>
          <div class="tech-code-block"><pre>${escapeHtml(ev.code_executed)}</pre></div>
        `;
      } else if (cat === "MEDIA_FFMPEG") {
        detailsHtml = `
          <div style="font-size:0.75rem; margin-bottom:4px;"><strong>Source:</strong> <code>${escapeHtml(ev.input_file)}</code></div>
          <div class="tech-code-title"><span>Outputs (${ev.output_count}):</span></div>
          <div class="tech-code-block"><pre>${escapeHtml((ev.output_files || []).join('\n'))}</pre></div>
        `;
      } else if (cat === "RENDER_GPU") {
        detailsHtml = `
          <div style="font-size:0.75rem; margin-bottom:4px;"><strong>Engine:</strong> ${escapeHtml(ev.engine)} · <strong>Resolution:</strong> ${ev.resolution}</div>
          <div class="tech-code-block"><pre>${escapeHtml(JSON.stringify(ev.prompt_blueprint, null, 2))}</pre></div>
        `;
      }

      html += `
        <div class="tech-event-card">
          <div class="tech-card-header">
            <div>
              <span class="badge ${getCategoryBadge(cat)}">${cat}</span>
              <strong style="margin-left:6px; color:var(--text);">${escapeHtml(ev.title)}</strong>
            </div>
            <div style="display:flex; gap:10px; align-items:center; color:var(--text-2); font-family:var(--font-mono); font-size:0.75rem;">
              <span>${ev.timestamp}</span>
              <span class="latency-badge">${ev.duration_ms || 0}ms</span>
            </div>
          </div>
          <div class="tech-card-body">
            ${detailsHtml}
          </div>
        </div>
      `;
    });

    listEl.innerHTML = html;
  }

  function getCategoryBadge(cat) {
    if (cat === "LLM_PROMPT") return "badge-agent";
    if (cat === "CRITIC_QA") return "badge-critic";
    if (cat === "RENDER_GPU") return "badge-gpu";
    if (cat === "BROWSER_PLAYWRIGHT") return "badge-user";
    return "badge-info";
  }

  function onDemoBtnClick() {
    if (sessionActive) {
      if (confirm("Live demo session is currently recording. Do you want to end it and compile the PDF report?")) {
        endDemoSession();
      }
    } else {
      const savedKey = typeof getGeminiKey === "function" ? getGeminiKey() : (localStorage.getItem("gemini_api_key") || "");
      const keyInput = document.getElementById("demo_api_key_input");
      if (keyInput) keyInput.value = savedKey;

      const startDialog = document.getElementById("demo_start_dialog");
      if (startDialog) startDialog.showModal();
    }
  }

  async function checkActiveSession() {
    try {
      const res = await fetch("/api/demo-session/status");
      if (res.ok) {
        const data = await res.json();
        if (data.active) {
          sessionId = data.session_id;
          loggedStepCount = data.total_events || 0;
          setSessionActiveState(true, data.session_name, data.brand_url, data.duration_seconds);
        }
      }
    } catch (e) {
      console.warn("Could not check demo session status:", e);
    }
  }

  async function startDemoSession(sessionName, apiKey, brandUrl) {
    if (apiKey && typeof setGeminiKey === "function") {
      setGeminiKey(apiKey);
    }

    try {
      const formData = new FormData();
      formData.append("session_name", sessionName || "Live System Demo");
      formData.append("api_key", apiKey || "");
      formData.append("brand_url", brandUrl || "");

      const res = await fetch("/api/demo-session/start", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Could not start demo session: " + res.statusText);

      const data = await res.json();
      sessionId = data.session_id;
      loggedStepCount = 1;
      setSessionActiveState(true, sessionName, brandUrl, 0);
      notify("🔴 Live Demo Session started. All actions are now being recorded!", "success");

      recordUserAction("SESSION_START", `User started live demo session: ${sessionName}`, { brand_url: brandUrl });
    } catch (e) {
      notify(e.message, "error");
    }
  }

  function setSessionActiveState(active, sessionName, brandUrl, initialDuration = 0) {
    sessionActive = active;
    const bar = document.getElementById("demo_recording_bar");
    const dot = document.getElementById("demo_dot");
    const label = document.getElementById("demo_btn_label");
    const brandPill = document.getElementById("demo_brand_pill");

    if (active) {
      bar.hidden = false;
      dot.classList.add("recording");
      label.textContent = "Recording...";
      document.getElementById("btn_demo_session").classList.add("recording");

      if (brandUrl && brandPill) {
        brandPill.textContent = brandUrl.replace(/^https?:\/\//, "");
        brandPill.hidden = false;
      }

      startEpoch = Date.now() - (initialDuration * 1000);
      updateTimer();
      clearInterval(timerInterval);
      timerInterval = setInterval(updateTimer, 1000);
    } else {
      bar.hidden = true;
      dot.classList.remove("recording");
      label.textContent = "Live demo";
      document.getElementById("btn_demo_session").classList.remove("recording");
      clearInterval(timerInterval);
    }
  }

  function updateTimer() {
    if (!startEpoch) return;
    const elapsedSec = Math.floor((Date.now() - startEpoch) / 1000);
    const mins = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
    const secs = String(elapsedSec % 60).padStart(2, "0");
    const timerEl = document.getElementById("demo_timer");
    if (timerEl) timerEl.textContent = `${mins}:${secs}`;

    const counterEl = document.getElementById("demo_step_counter");
    if (counterEl) counterEl.textContent = `${loggedStepCount} steps`;
  }

  async function endDemoSession() {
    const endBtn = document.getElementById("btn_end_demo_session");
    if (endBtn) {
      endBtn.disabled = true;
      endBtn.innerHTML = `<span class="spinner" style="width:12px; height:12px; border-width:2px;"></span> Compiling PDF Report...`;
    }

    try {
      const res = await fetch("/api/demo-session/end", { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Could not end demo session.");
      }

      const data = await res.json();
      setSessionActiveState(false);

      const endDialog = document.getElementById("demo_end_dialog");
      const downloadBtn = document.getElementById("demo_end_download_btn");
      const statsBox = document.getElementById("demo_end_stats");

      if (downloadBtn) downloadBtn.href = data.download_url;

      if (statsBox) {
        statsBox.innerHTML = `
          <div class="stat-pill"><div class="stat-pill-val">${data.duration_seconds}s</div><div class="stat-pill-lbl">Duration</div></div>
          <div class="stat-pill"><div class="stat-pill-val">${data.total_events}</div><div class="stat-pill-lbl">Audit Events</div></div>
          <div class="stat-pill"><div class="stat-pill-val" style="color:var(--success);">Ready</div><div class="stat-pill-lbl">PDF Status</div></div>
        `;
      }

      if (endDialog) endDialog.showModal();
      notify("Demo session finished! PDF report is ready for download.", "success");

      const tempLink = document.createElement("a");
      tempLink.href = data.download_url;
      tempLink.download = data.pdf_filename;
      tempLink.click();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      if (endBtn) {
        endBtn.disabled = false;
        endBtn.innerHTML = `<i class="fa-solid fa-stop"></i> End Session & Generate PDF`;
      }
    }
  }

  window.recordUserAction = async function (actionType, message, details = null) {
    if (!sessionActive) return;
    loggedStepCount++;
    const counterEl = document.getElementById("demo_step_counter");
    if (counterEl) counterEl.textContent = `${loggedStepCount} steps`;

    try {
      await fetch("/api/demo-session/log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actor: "USER",
          action_type: actionType,
          step: "Live Demo",
          level: "ACTION",
          message: message,
          details: details,
        }),
      });
    } catch (e) {
      console.warn("Could not log user action:", e);
    }
  };

  function bindUserActivityTracking() {
    document.querySelectorAll(".nav-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const view = btn.getAttribute("data-view");
        window.recordUserAction("NAVIGATION", `User switched view to: ${view.toUpperCase()}`);
      });
    });

    const brandInput = document.getElementById("brand_url");
    if (brandInput) {
      brandInput.addEventListener("change", () => {
        if (brandInput.value.trim()) {
          window.recordUserAction("INPUT", `User specified brand URL: ${brandInput.value.trim()}`);
        }
      });
    }

    const btnContinue = document.getElementById("btn_continue");
    if (btnContinue) {
      btnContinue.addEventListener("click", () => {
        window.recordUserAction("BUTTON_CLICK", "User clicked 'Continue' to advance from Brand to Research step.");
      });
    }

    const btnStartResearch = document.getElementById("btn_start_research");
    if (btnStartResearch) {
      btnStartResearch.addEventListener("click", () => {
        window.recordUserAction("BUTTON_CLICK", "User launched autonomous competitor research (Agent A3).");
      });
    }

    const btnSkipComp = document.getElementById("btn_skip_competitors");
    if (btnSkipComp) {
      btnSkipComp.addEventListener("click", () => {
        window.recordUserAction("BUTTON_CLICK", "User chose to skip competitors and analyze brand site alone.");
      });
    }

    const brandFiles = document.getElementById("brand_files");
    if (brandFiles) {
      brandFiles.addEventListener("change", () => {
        if (brandFiles.files && brandFiles.files.length) {
          const names = Array.from(brandFiles.files).map((f) => `${f.name} (${Math.round(f.size / 1024)} KB)`).join(", ");
          window.recordUserAction("UPLOAD", `User uploaded reference photos: ${names}`);
        }
      });
    }

    const logoFile = document.getElementById("logo_file");
    if (logoFile) {
      logoFile.addEventListener("change", () => {
        if (logoFile.files && logoFile.files.length) {
          window.recordUserAction("UPLOAD", `User uploaded brand logo: ${logoFile.files[0].name}`);
        }
      });
    }
  }
})();
