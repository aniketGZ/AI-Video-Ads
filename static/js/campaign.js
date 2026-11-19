// Campaign page: one guided flow.
//   1. Brand      URL + reference images
//   2. Research   competitor discovery -> confirm -> competitor agent (top 50 ads) -> /api/flow/analyze
//   3. Ads        /api/flow/prompts -> 25 image ads + 25 Omni Flash video ads (each renders only on click)
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = escapeHtml;

  const IMAGE_COUNT = 25;
  const VIDEO_COUNT = 25;
  const IMAGE_RENDER_CONCURRENCY = 3;
  const MAX_VIDEO_REFS = 7;
  const STREAM_POLL_MS = 2000;

  const refs = imageDropzone({ zone: "brand_drop", input: "brand_files", thumbs: "brand_thumbs", max: 4 });
  const logoDrop = imageDropzone({ zone: "logo_drop", input: "logo_file", thumbs: "logo_thumbs", max: 1 });

  const flow = {
    token: 0,           // bumps on every reset so late responses from an old campaign are ignored
    url: "",
    files: [],
    discovery: null,
    competitors: [],
    runId: null,
    pollTimer: null,    // non-null while research is being polled; polls never overlap
    analysing: false,   // brand analysis / prompt writing in flight: only one at a time
    productPaths: [],
    intelligence: null,
    selectedPresetId: "diverse",
    allPresets: [],
    presetIndustryFilter: "all",
    presetSearchQuery: "",
    competitor: null,
    prompts: null,
    aspect: "4:5",
    images: {},         // id -> render result
    videos: {},         // id -> video url
    activeRenders: 0,
    rendering: new Set(), // image ad ids with a render in flight
  };

  // ------------------------------------------------------------ step state
  function setStep(id, state) {
    $(id).dataset.state = state;
  }

  function badge(id, text, kind) {
    const el = $(id);
    el.hidden = !text;
    el.className = `badge ${kind || ""}`;
    el.innerHTML = kind === "running" ? `<span class="spinner"></span>${esc(text)}` : esc(text);
  }

  function showResearchPart(part) {
    ["research_discovering", "research_confirm", "research_running", "research_analysing", "research_error"].forEach((id) => {
      $(id).hidden = id !== part;
    });
  }

  function stopPolling() {
    if (flow.pollTimer) clearTimeout(flow.pollTimer);
    flow.pollTimer = null;
  }

  // ------------------------------------------------------------ creative reference presets
  async function loadCreativePresets() {
    try {
      const res = await fetch("/api/campaign/presets");
      if (res.ok) {
        const data = await res.json();
        flow.allPresets = data.presets || [];
        const active = getActivePreset();
        const toolbarName = $("active_preset_name");
        if (toolbarName && active) toolbarName.textContent = active.name;
      }
    } catch (err) {
      console.warn("Could not load creative presets:", err);
    }
  }
  loadCreativePresets();

  function getActivePreset() {
    const selId = flow.selectedPresetId || "diverse";
    if (flow.allPresets.length) {
      const found = flow.allPresets.find((p) => p.id === selId);
      if (found) return found;
      const diverse = flow.allPresets.find((p) => p.id === "diverse");
      if (diverse) return diverse;
    }
    if (flow.intelligence && flow.intelligence.detected_preset) {
      return flow.intelligence.detected_preset;
    }
    return flow.allPresets[0] || null;
  }

  function openPresetModal() {
    const modal = $("preset_modal");
    if (!modal) return;
    renderPresetCards();
    if (typeof modal.showModal === "function") modal.showModal();
    else modal.hidden = false;
  }

  function closePresetModal() {
    const modal = $("preset_modal");
    if (!modal) return;
    if (typeof modal.close === "function") modal.close();
    else modal.hidden = true;
  }

  function selectPreset(presetId) {
    flow.selectedPresetId = presetId;
    const preset = flow.allPresets.find((p) => p.id === presetId);
    if (preset) {
      const toolbarName = $("active_preset_name");
      if (toolbarName) toolbarName.textContent = preset.name;
      const intelName = $("preset_intel_active_name");
      if (intelName) intelName.textContent = preset.name;
      const intelMv = $("preset_intel_active_movement");
      if (intelMv) intelMv.textContent = preset.movement;
      notify(`Design preset set to "${preset.name}".`, "success");
    }
    closePresetModal();
  }

  function renderPresetCards(industry = flow.presetIndustryFilter, query = flow.presetSearchQuery) {
    flow.presetIndustryFilter = industry;
    flow.presetSearchQuery = query;

    const grid = $("preset_cards_grid");
    if (!grid) return;

    let filtered = flow.allPresets.slice();
    if (industry && industry !== "all") {
      filtered = filtered.filter((p) => p.industry_slug === industry);
    }
    if (query && query.trim()) {
      const q = query.toLowerCase().trim();
      filtered = filtered.filter((p) =>
        p.name.toLowerCase().includes(q) ||
        p.movement.toLowerCase().includes(q) ||
        p.industry_label.toLowerCase().includes(q) ||
        p.summary.toLowerCase().includes(q)
      );
    }

    if (!filtered.length) {
      grid.innerHTML = `<div class="media-empty" style="grid-column: 1 / -1; padding: 40px;"><i class="fa-solid fa-magnifying-glass"></i><span>No presets found matching "${esc(query || industry)}".</span></div>`;
      return;
    }

    const activePreset = getActivePreset();
    const activeId = activePreset ? activePreset.id : null;

    grid.innerHTML = filtered.map((p) => {
      const isSel = p.id === activeId;
      const refPins = (p.reference_pins || []).slice(0, 3);
      const palette = (p.colors?.palette || []).slice(0, 5);
      const fonts = (p.typography?.recommended_headline_fonts || []).slice(0, 2);

      return `
      <article class="preset-card ${isSel ? "is-active" : ""}" data-preset-id="${esc(p.id)}">
        <div class="preset-card-head">
          <div class="preset-card-title">
            <span class="preset-card-industry">${esc(p.industry_label)}</span>
            <h4>${esc(p.name)}</h4>
            <div class="preset-card-movement">${esc(p.movement)}</div>
          </div>
          ${isSel ? '<span class="badge done"><i class="fa-solid fa-check"></i> Active</span>' : ""}
        </div>

        <p class="preset-card-desc">${esc(p.summary)}</p>

        <div class="preset-ref-gallery">
          ${refPins.map((pin) => `
            <a class="preset-ref-item" href="${esc(pin.pin_url || pin.image_url)}" target="_blank" rel="noopener" title="${esc(pin.title || 'Pinterest Reference')}">
              <img src="${esc(pin.image_url)}" alt="${esc(pin.title || 'Reference')}" loading="lazy">
              <div class="pin-overlay"><i class="fa-brands fa-pinterest"></i></div>
            </a>
          `).join("")}
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <div class="preset-palette-chips" title="Color Mood: ${esc(p.colors?.mood || '')}">
            ${palette.map((hex) => `<span class="preset-color-dot" style="background:${esc(hex)}" title="${esc(hex)}"></span>`).join("")}
          </div>
          <div class="preset-typography-chips">
            ${fonts.map((f) => `<span class="preset-tag"><i class="fa-solid fa-font"></i> ${esc(f)}</span>`).join("")}
          </div>
        </div>

        <div class="preset-card-foot">
          <span class="muted small"><i class="fa-solid fa-lightbulb"></i> ${(p.decorative_elements || []).slice(0, 2).join(", ")}</span>
          <button type="button" class="btn btn-sm ${isSel ? "btn-ghost" : "btn-primary"}" data-select-preset="${esc(p.id)}">
            ${isSel ? '<i class="fa-solid fa-check"></i> Selected' : '<i class="fa-solid fa-wand-magic-sparkles"></i> Use Preset'}
          </button>
        </div>
      </article>`;
    }).join("");
  }

  function resetCampaign({ keepBrand }) {
    flow.token++;
    stopPolling();
    if (flow.runId && $("research_running").hidden === false) {
      fetch(`/api/competitor-agent/stop/${encodeURIComponent(flow.runId)}`, { method: "POST" }).catch(() => {});
    }
    Object.assign(flow, {
      discovery: null, competitors: [], runId: null, productPaths: [], intelligence: null,
      competitor: null, prompts: null, images: {}, videos: {}, activeRenders: 0,
      analysing: false, rendering: new Set(),
    });
    if (!keepBrand) {
      $("brand_url").value = "";
      refs.clear();
      logoDrop.clear();
    }
    setStep("step_brand", "active");
    $("brand_body").hidden = false;
    $("btn_edit_brand").hidden = true;
    $("brand_summary").textContent = "Paste the product page and add reference images.";
    setStep("step_research", "locked");
    $("research_body").hidden = true;
    $("btn_toggle_research").hidden = true;
    $("research_results").hidden = true;
    $("research_results").innerHTML = "";
    badge("research_badge", "");
    setStep("step_ads", "locked");
    $("ads_body").hidden = true;
    badge("ads_badge", "");
    $("image_grid").innerHTML = "";
    $("video_grid").innerHTML = "";
    $("btn_new_campaign").hidden = true;
    $("campaign_showcase").hidden = false;
  }

  // ------------------------------------------------------------ step 1: brand
  function normalizeUrl(raw) {
    let url = (raw || "").trim();
    if (!url) return null;
    if (!/^https?:\/\//i.test(url)) url = "https://" + url;
    try {
      new URL(url);
      return url;
    } catch (e) {
      return null;
    }
  }

  $("btn_continue").addEventListener("click", () => {
    const url = normalizeUrl($("brand_url").value);
    if (!url) {
      showUrlError($("brand_url").value.trim() ? "That doesn't look like a web address. Try https://yourbrand.com" : "Paste your brand or product URL to start.");
      return;
    }
    // Everyone can look around the builder; starting a campaign needs Pro or Studio
    if (!requireFeature("campaign_manager", { savedUrl: url })) return;
    if (!requireKey(() => $("btn_continue").click())) return;
    flow.url = url;
    $("campaign_showcase").hidden = true;
    $("campaign_showcase").querySelector("video")?.pause();
    flow.files = refs.files();
    flow.logoFile = logoDrop.files()[0] || null;

    setStep("step_brand", "done");
    $("brand_body").hidden = true;
    $("btn_edit_brand").hidden = false;
    $("brand_summary").textContent = `${url} · ${flow.files.length ? `${flow.files.length} reference image${flow.files.length > 1 ? "s" : ""}` : "no reference images"}`;
    $("btn_new_campaign").hidden = false;
    discoverCompetitors();
  });
  $("brand_url").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault(); // otherwise the same Enter lands on whatever dialog Continue opens
    $("btn_continue").click();
  });

  // The error sits on the field it is about, and leaves as soon as the field changes
  function showUrlError(message) {
    const input = $("brand_url");
    const box = input.closest(".input-with-icon");
    $("brand_url_error").innerHTML = `<i class="fa-solid fa-circle-exclamation"></i><span>${esc(message)}</span>`;
    $("brand_url_error").hidden = false;
    input.setAttribute("aria-invalid", "true");
    box.classList.remove("shake");
    void box.offsetWidth; // restart the shake on a repeat attempt
    box.classList.add("shake");
    input.focus();
  }
  $("brand_url").addEventListener("input", () => {
    $("brand_url_error").hidden = true;
    $("brand_url").removeAttribute("aria-invalid");
  });

  // Research holds a lot of reading; once it is done it can fold away to leave room for the ads
  $("btn_toggle_research").addEventListener("click", () => {
    const body = $("research_body");
    body.hidden = !body.hidden;
    $("btn_toggle_research").textContent = body.hidden ? "Show" : "Hide";
    $("btn_toggle_research").setAttribute("aria-expanded", String(!body.hidden));
  });

  $("btn_edit_brand").addEventListener("click", async () => {
    if (flow.pollTimer && !(await askConfirm("Stop research?", "Research is running. Stop it and edit your brand?", "Stop and edit"))) return;
    resetCampaign({ keepBrand: true });
    $("brand_url").focus();
  });

    $("btn_close_presets")?.addEventListener("click", closePresetModal);
  $("btn_active_preset")?.addEventListener("click", openPresetModal);

  $("preset_search_input")?.addEventListener("input", (e) => {
    renderPresetCards(flow.presetIndustryFilter, e.target.value);
  });

  $("preset_industry_pills")?.addEventListener("click", (e) => {
    const pill = e.target.closest("[data-industry]");
    if (!pill) return;
    $("preset_industry_pills").querySelectorAll(".preset-pill").forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");
    renderPresetCards(pill.dataset.industry, flow.presetSearchQuery);
  });

  $("preset_cards_grid")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-select-preset]");
    if (btn) {
      selectPreset(btn.dataset.selectPreset);
    }
  });

  $("btn_new_campaign").addEventListener("click", async () => {
    if ((flow.pollTimer || flow.prompts) && !(await askConfirm("Start a new campaign?", "The current one will be cleared from this page.", "Start new"))) return;
    resetCampaign({ keepBrand: false });
    window.scrollTo({ top: 0, behavior: "smooth" });
    $("brand_url").focus();
  });

  // ------------------------------------------------------------ step 2a: competitors
  async function discoverCompetitors() {
    const token = flow.token;
    setStep("step_research", "active");
    $("research_body").hidden = false;
    $("research_results").hidden = true;
    showResearchPart("research_discovering");
    badge("research_badge", "Finding competitors", "running");
    $("step_research").scrollIntoView({ behavior: "smooth", block: "start" });

    const fd = new FormData();
    fd.append("url", flow.url);
    try {
      const res = await fetch("/api/competitor-agent/discover", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Could not find competitors"));
      const data = await res.json();
      if (token !== flow.token) return;
      flow.discovery = data;
      flow.competitors = (data.competitors || []).map((c) => ({ name: c.name, reason: c.reason || "", selected: c.selected !== false }));
      renderCompetitorChoice();
    } catch (err) {
      if (token !== flow.token) return;
      researchError(err.message, [
        { label: "Try again", primary: true, action: discoverCompetitors },
        { label: "Skip competitors, analyse my brand only", action: () => analyseBrand(null) },
      ]);
    }
  }

  function renderCompetitorChoice() {
    const d = flow.discovery || {};
    $("research_brand_line").innerHTML =
      `We read this as <strong>${esc(d.brand_name || "your brand")}</strong>${d.category ? ` · ${esc(d.category)}` : ""}` +
      `${d.market && d.market.country ? ` · selling in ${esc(d.market.country)}` : ""}. ` +
      "Pick the competitors whose live Meta ads we should study.";
    $("comp_list").innerHTML = flow.competitors.map((c, i) => `
      <label class="comp-item">
        <input type="checkbox" data-comp="${i}" ${c.selected ? "checked" : ""}>
        <span><strong>${esc(c.name)}</strong>${c.reason ? `<span class="comp-reason">${esc(c.reason)}</span>` : ""}</span>
      </label>`).join("");
    showResearchPart("research_confirm");
    badge("research_badge", "Confirm competitors");
  }

  $("comp_list").addEventListener("change", (e) => {
    const i = e.target.dataset.comp;
    if (i !== undefined) flow.competitors[Number(i)].selected = e.target.checked;
  });

  $("comp_add_form").addEventListener("submit", (e) => {
    e.preventDefault();
    const name = $("comp_add_input").value.trim();
    if (!name) return;
    if (flow.competitors.some((c) => c.name.toLowerCase() === name.toLowerCase())) {
      notify(`${name} is already in the list.`, "info");
      return;
    }
    flow.competitors.push({ name, reason: "Added by you", selected: true });
    $("comp_add_input").value = "";
    renderCompetitorChoice();
  });

  $("btn_skip_competitors").addEventListener("click", () => analyseBrand(null));

  // ------------------------------------------------------------ step 2b: competitor agent
  $("btn_start_research").addEventListener("click", async () => {
    const selected = flow.competitors.filter((c) => c.selected);
    if (!selected.length) {
      notify("Tick at least one competitor, or skip competitor research.", "warning");
      return;
    }
    if (!requireKey()) return;
    const token = flow.token;
    $("btn_start_research").disabled = true;

    const fd = new FormData();
    fd.append("url", flow.url);
    if (flow.files[0]) fd.append("product_image", flow.files[0]);
    fd.append("competitors", JSON.stringify(selected.map((c) => ({ name: c.name }))));
    if (flow.discovery && flow.discovery.demographics) fd.append("demographics", JSON.stringify(flow.discovery.demographics));
    if (flow.discovery && flow.discovery.market) fd.append("market", JSON.stringify(flow.discovery.market));

    try {
      const res = await fetch("/api/competitor-agent/start", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Could not start research"));
      const data = await res.json();
      if (token !== flow.token) return;
      flow.runId = data.run_id;
      lastEventIndex = 0;
      showResearchPart("research_running");
      badge("research_badge", "Researching", "running");
      updateProgress({ stats: {}, current_step: 0, status: "running", events: [] });
      flow.pollTimer = setTimeout(() => pollResearch(token), STREAM_POLL_MS);
    } catch (err) {
      if (token !== flow.token) return;
      notify(err.message, "error");
    } finally {
      $("btn_start_research").disabled = false;
    }
  });

  let lastEventIndex = 0;
  // Each poll schedules the next only after it returns, so a slow response can never
  // let two polls both see "complete" and start the brand analysis twice.
  async function pollResearch(token) {
    if (token !== flow.token || !flow.runId) return stopPolling();
    let data = null;
    try {
      const res = await fetch(`/api/competitor-agent/runs/${encodeURIComponent(flow.runId)}/stream?last_index=${lastEventIndex}`);
      if (res.ok) data = await res.json();
    } catch (e) {
      data = null;
    }
    if (token !== flow.token || !flow.pollTimer) return;
    if (!data) {
      flow.pollTimer = setTimeout(() => pollResearch(token), STREAM_POLL_MS);
      return;
    }
    lastEventIndex = data.next_index || lastEventIndex;
    updateProgress(data);

    const stats = data.stats || {};
    if (stats.campaign_ready || data.status === "complete") {
      stopPolling();
      analyseBrand(flow.runId);
    } else if (data.status === "failed" || data.status === "stopped") {
      stopPolling();
      researchError(
        data.status === "stopped" ? "Competitor research was stopped." : `Competitor research failed: ${data.error || "unknown error"}`,
        [{ label: "Continue with my brand only", primary: true, action: () => analyseBrand(null) }],
      );
    } else {
      flow.pollTimer = setTimeout(() => pollResearch(token), STREAM_POLL_MS);
    }
  }

  function updateProgress(data) {
    const stats = data.stats || {};
    const target = stats.target_selected_ads || 50;
    const selected = stats.ads_selected || 0;
    $("meter_value").innerHTML = `${selected} <small>/ ${target}</small>`;
    $("meter_fill").style.width = `${Math.min(100, (selected / target) * 100)}%`;
    const step = Number(data.current_step || 0);
    document.querySelectorAll("#stages .stage").forEach((el) => {
      const n = Number(el.dataset.stage);
      el.classList.toggle("done", n < step || !!stats.campaign_ready);
      el.classList.toggle("active", n === step && !stats.campaign_ready);
    });
    const events = data.events || [];
    if (events.length) $("research_log").textContent = events[events.length - 1].message || "";
    if (stats.ads_analyzed && step >= 4) {
      $("research_log").textContent = `Analysed ${stats.ads_analyzed} of ${selected} ads…`;
    }
  }

  $("btn_stop_research").addEventListener("click", async () => {
    if (!flow.runId) return;
    $("btn_stop_research").disabled = true;
    try {
      await fetch(`/api/competitor-agent/stop/${encodeURIComponent(flow.runId)}`, { method: "POST" });
    } finally {
      $("btn_stop_research").disabled = false;
    }
  });

  function researchError(message, actions) {
    const box = $("research_error");
    box.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i><span>${esc(message)}</span>`;
    actions.forEach((a) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = a.primary ? "btn btn-sm btn-primary" : "btn-link";
      b.textContent = a.label;
      b.addEventListener("click", a.action);
      box.appendChild(b);
    });
    showResearchPart("research_error");
    badge("research_badge", "Needs attention", "error");
  }

  // ------------------------------------------------------------ step 2c: brand intelligence
  async function analyseBrand(runId) {
    if (flow.analysing) return;
    const token = flow.token;
    flow.analysing = true;
    stopPolling();
    setStep("step_research", "active");
    $("research_body").hidden = false;
    showResearchPart("research_analysing");
    badge("research_badge", "Analysing brand", "running");

    const fd = new FormData();
    fd.append("url", flow.url);
    flow.files.forEach((f) => fd.append("images", f));
    if (flow.logoFile) fd.append("logo", flow.logoFile);
    if (runId) fd.append("competitor_run_id", runId);

    try {
      const res = await fetch("/api/flow/analyze", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Brand analysis failed"));
      const data = await res.json();
      if (token !== flow.token) return;
      flow.intelligence = data.intelligence;
      flow.productPaths = data.product_image_paths || [];
      flow.competitor = data.competitor;
    } catch (err) {
      if (token !== flow.token) return;
      flow.analysing = false;
      researchError(err.message, [{ label: "Try again", primary: true, action: () => analyseBrand(runId) }]);
      return;
    }

    $("research_analysing").hidden = true;
    renderIntelligence();
    setStep("step_research", "done");
    badge("research_badge", "Done", "done");
    $("btn_toggle_research").hidden = false;
    $("btn_toggle_research").textContent = "Hide";
    $("btn_toggle_research").setAttribute("aria-expanded", "true");
    flow.analysing = false;
    writePrompts();
  }

  function list(items) {
    const clean = (items || []).filter(Boolean);
    return clean.length ? `<ul class="list">${clean.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : `<p class="muted small">None found</p>`;
  }

  function kv(pairs) {
    return `<dl class="kv">${pairs.filter(([, v]) => v).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>`;
  }

  function renderIntelligence() {
    const i = flow.intelligence || {};
    const s = i.brand_sentiment || {};
    const d = i.demographics || {};
    const a = i.audience || {};
    const b = i.bullseye_target || {};
    const c = i.competitor_takeaways || {};
    const comp = flow.competitor || {};

    const compBody = comp.used
      ? `<p class="muted small">${esc((comp.competitors || []).join(", "))} · ${esc(comp.total_ads)} live ads studied</p>
         <div class="subhead">Winning patterns</div>${list(c.winning_patterns)}
         <div class="subhead">Saturated — avoid</div>${list(c.saturated_angles)}
         <div class="subhead">White space — own it</div>${list(c.whitespace)}`
      : `<p class="muted small">${esc(comp.note || "Competitor research was skipped for this campaign.")}</p>`;

    const v = i.voice || {};
    const market = (i.markets || [])[0] || null;
    const proof = i.proof_bank || [];
    const themes = (i.review_themes || []).slice().sort((x, y) => (y.mentions || 0) - (x.mentions || 0)).slice(0, 5);
    const voiceCard = `
        <div class="intel-card">
          <h4><i class="fa-solid fa-pen-nib"></i> Voice &amp; claims</h4>
          ${kv([["Tone", v.tone], ["Talks to you as", v.address_as], ["Style", v.sentence_style], ["Emoji", v.tone ? (v.uses_emoji ? "Yes" : "Never") : ""]])}
          ${(v.use_words || []).length ? `<div class="subhead">Words it uses</div><div class="chips">${v.use_words.map((w) => `<span class="chip">${esc(w)}</span>`).join("")}</div>` : ""}
          ${(v.avoid_words || []).length ? `<div class="subhead">Words it never uses</div><div class="chips">${v.avoid_words.map((w) => `<span class="chip chip-avoid">${esc(w)}</span>`).join("")}</div>` : ""}
          <div class="subhead">Claims found on your site (${proof.length})</div>
          ${proof.length ? `<ul class="list">${proof.slice(0, 8).map((c) => `<li>${esc(c.claim)} <a class="muted small" href="${esc(c.source_url)}" target="_blank" rel="noopener">source</a></li>`).join("")}</ul>`
                         : `<p class="muted small">No checkable claims found, so ads will sell benefits without numbers or ratings.</p>`}
          ${(i.unverified_claims || []).length ? `<p class="muted small">${i.unverified_claims.length} claim(s) left out because they couldn't be found on your site.</p>` : ""}
        </div>`;
    const customersCard = `
        <div class="intel-card">
          <h4><i class="fa-regular fa-comments"></i> What customers say</h4>
          ${i.review_rating ? `<p class="small">${esc(i.review_rating)}</p>` : ""}
          ${themes.length ? themes.map((t) => `
            <div class="subhead">${esc(t.theme_type)} · ${esc(t.mentions)} mentions</div>
            <p class="small">${esc(t.summary)}</p>
            ${(t.customer_phrases || []).slice(0, 2).map((q) => `<p class="quote small">“${esc(q)}”</p>`).join("")}`).join("")
          : `<p class="muted small">No public reviews were found for this brand.</p>`}
        </div>`;

    const kit = i.brand_kit || {};
    const logo = i.logo || null;
    const refCount = ((i.references || {}).image || []).length;
    const vRefCount = ((i.references || {}).video || []).length;
    const swatch = (label, hex) => hex ? `<span class="swatch" title="${esc(label)}"><i style="background:${esc(hex)}"></i>${esc(label)} ${esc(hex)}</span>` : "";
    const brandStrip = `
      <div class="brand-strip">
        ${logo ? `<img class="brand-logo ${logo.tone === "light" ? "light" : ""}" src="${esc(logo.path)}" alt="${esc(i.brand_name || "Brand")} logo">`
               : `<span class="muted small">No logo found on the site. Add one in step 1 to brand the ads.</span>`}
        <div class="swatches">
          ${swatch("Primary", kit.primary_hex)}${swatch("CTA", kit.accent_hex)}${swatch("Background", kit.background_hex)}${swatch("Text", kit.text_hex)}
        </div>
        <div class="brand-type">${esc([kit.headline_type, kit.visual_mood, market && market.country ? `Selling in ${market.country}${market.language ? ` (${market.language})` : ""}` : ""].filter(Boolean).join(" · "))}${
          refCount ? ` · Layouts and concepts from ${refCount} analysed competitor image ads${vRefCount ? ` and ${vRefCount} video ads` : ""}` : " · No competitor ads analysed, so built-in layouts are used"}</div>
      </div>`;
    const activePreset = getActivePreset();
    if (activePreset && !flow.selectedPresetId) {
      flow.selectedPresetId = activePreset.id;
    }
    if (flow.intelligence && !flow.intelligence.detected_preset && activePreset) {
      flow.intelligence.detected_preset = activePreset;
    }
    const presetToolbarName = $("active_preset_name");
    if (presetToolbarName && activePreset) presetToolbarName.textContent = activePreset.name;

    const presetBanner = activePreset ? `
      <div class="preset-intel-card" id="preset_intel_card">
        <div class="preset-intel-info">
          <div class="preset-intel-eyebrow"><i class="fa-solid fa-wand-magic-sparkles"></i> Creative Reference Preset  Pinterest Atlas</div>
          <div class="preset-intel-name" id="preset_intel_active_name">${esc(activePreset.name)}</div>
          <div class="preset-intel-movement" id="preset_intel_active_movement">${esc(activePreset.movement)}</div>
          <div class="muted small">${esc(activePreset.summary || "")}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 14px;">
          <div class="preset-intel-refs">
            ${(activePreset.reference_pins || []).slice(0, 3).map((pin) => `
              <a href="${esc(pin.pin_url || pin.image_url)}" target="_blank" rel="noopener" title="${esc(pin.title || 'Pinterest Reference')}">
                <img class="preset-intel-ref-thumb" src="${esc(pin.image_url)}" alt="" loading="lazy">
              </a>
            `).join("")}
          </div>
          <button type="button" class="btn btn-sm btn-ghost" id="btn_change_preset">
            <i class="fa-solid fa-palette"></i> Change preset
          </button>
        </div>
      </div>` : "";

    $("research_results").innerHTML = brandStrip + presetBanner + `
      <div class="bullseye">
        <div class="bullseye-icon"><i class="fa-solid fa-bullseye"></i></div>
        <div>
          <div class="eyebrow">Bullseye customer</div>
          <h3>${esc(b.persona_name)} <span class="muted">· ${esc([b.age, b.gender, b.occupation, b.location].filter(Boolean).join(" · "))}</span></h3>
          <p>${esc(b.snapshot)}</p>
          <dl class="kv kv-2">
            ${[["Trigger moment", b.trigger_moment], ["Core pain", b.core_pain], ["Core desire", b.core_desire], ["Where they scroll", b.scroll_habits]]
              .filter(([, v]) => v).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}
          </dl>
        </div>
      </div>
      <div class="intel-grid">
        <div class="intel-card">
          <h4><i class="fa-regular fa-face-smile"></i> Brand sentiment</h4>
          ${kv([["Tone", s.tone], ["Emotional promise", s.emotional_promise], ["Customer perception", s.customer_perception]])}
          <div class="chips">${(s.voice_keywords || []).map((k) => `<span class="chip">${esc(k)}</span>`).join("")}</div>
        </div>
        <div class="intel-card">
          <h4><i class="fa-solid fa-users"></i> Demographics</h4>
          ${kv([["Age", d.age_range], ["Gender", d.gender], ["Geography", d.geography], ["Income", d.income_level], ["Lifestyle", d.lifestyle], ["Culture", d.cultural_context]])}
        </div>
        <div class="intel-card">
          <h4><i class="fa-solid fa-heart-pulse"></i> Audience</h4>
          <div class="subhead">Pain points</div>${list(a.pain_points)}
          <div class="subhead">Desires</div>${list(a.desires)}
          <div class="subhead">Objections</div>${list(a.objections)}
        </div>
        <div class="intel-card">
          <h4><i class="fa-solid fa-chess"></i> Competitors</h4>
          ${compBody}
        </div>
        ${voiceCard}
        ${customersCard}
      </div>`;
    $("research_results").hidden = false;
    $("btn_change_preset")?.addEventListener("click", openPresetModal);
  }

  // ------------------------------------------------------------ step 3: prompts
  async function writePrompts() {
    if (flow.analysing) return;
    const token = flow.token;
    flow.analysing = true;
    setStep("step_ads", "active");
    $("ads_body").hidden = false;
    badge("ads_badge", "Writing prompts", "running");
    adsStatus(`Writing ${IMAGE_COUNT} image ads and ${VIDEO_COUNT} video ads for ${(flow.intelligence.bullseye_target || {}).persona_name || "your bullseye customer"}…`, "busy");
    $("image_grid").innerHTML = "";
    $("video_grid").innerHTML = "";

    try {
      const res = await fetch("/api/flow/prompts", {
        method: "POST",
        headers: apiHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          intelligence: flow.intelligence,
          has_reference_images: flow.productPaths.length > 0,
          aspect_ratio: flow.aspect,
          image_count: IMAGE_COUNT,
          video_count: VIDEO_COUNT,
          meta_refs: (flow.intelligence || {}).references || null,
          preset_id: flow.selectedPresetId || ((flow.intelligence && flow.intelligence.detected_preset) ? flow.intelligence.detected_preset.id : null),
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Prompt writing failed"));
      const data = await res.json();
      if (token !== flow.token) return;
      flow.prompts = data;
    } catch (err) {
      if (token !== flow.token) return;
      flow.analysing = false;
      badge("ads_badge", "Needs attention", "error");
      adsStatus(err.message, "error", { label: "Try again", action: writePrompts });
      return;
    }

    $("count_images").textContent = flow.prompts.image_ads.length;
    $("count_videos").textContent = flow.prompts.video_ads.length;
    renderImageCards();
    renderVideoCards();
    flow.analysing = false;
    $("step_ads").scrollIntoView({ behavior: "smooth", block: "start" });
    badge("ads_badge", "Ready", "done");
    adsStatus(`${flow.prompts.image_ads.length} image ads and ${flow.prompts.video_ads.length} video ads written. Click Render on the ones you want.`, "done");
  }

  function adsStatus(text, kind, action) {
    const el = $("ads_status");
    if (!text) {
      el.innerHTML = "";
      return;
    }
    el.className = `inline-status status-line ${kind === "error" ? "error" : ""}`;
    const icon = kind === "busy" ? '<span class="spinner"></span>'
      : kind === "error" ? '<i class="fa-solid fa-circle-exclamation"></i>'
      : '<i class="fa-solid fa-circle-check" style="color: var(--success)"></i>';
    el.innerHTML = `${icon}<span>${esc(text)}</span>`;
    if (action) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "btn btn-sm";
      b.textContent = action.label;
      b.addEventListener("click", action.action);
      el.appendChild(b);
    }
  }

  // ------------------------------------------------------------ ads tabs & toolbar
  segmented("aspect_group", "ratio", (ratio) => {
    flow.aspect = ratio;
    document.querySelectorAll("#image_grid .media").forEach((m) => { m.className = `media ${ratioClass(ratio)}`; });
    if (Object.keys(flow.images).length) notify("New size applies to the next render. Use Render all to render every image.", "info");
  });

  flow.videoRes = "1080p";
  segmented("video_res_group", "res", (res) => {
    flow.videoRes = res;
    (flow.prompts?.video_ads || []).forEach((ad) => {
      if (!ad.custom_res) {
        ad.resolution = res;
        const sel = document.querySelector(`select[data-vad-res="${ad.id}"]`);
        if (sel) sel.value = res;
        const tag = document.querySelector(`#vcard_${ad.id} .vcard-res`);
        if (tag) tag.textContent = res;
      }
    });
  });

  document.querySelectorAll("[data-ads-tab]").forEach((btn) => btn.addEventListener("click", () => {
    const tab = btn.dataset.adsTab;
    document.querySelectorAll("[data-ads-tab]").forEach((b) => {
      b.classList.toggle("active", b === btn);
      b.setAttribute("aria-selected", String(b === btn));
    });
    $("image_grid").hidden = tab !== "images";
    $("image_tools").hidden = tab !== "images";
    $("video_grid").hidden = tab !== "videos";
    $("video_tools").hidden = tab !== "videos";
  }));

  $("btn_render_all").addEventListener("click", () => renderAllImages());

  function ratioClass(r) {
    return "r-" + String(r).replace(":", "-");
  }

  // ------------------------------------------------------------ image ads
  function imageAd(id) {
    return ((flow.prompts && flow.prompts.image_ads) || []).find((a) => a.id === id);
  }

  // Voice and claim checks the server ran on this ad's copy
  function checksLine(checks) {
    if (!checks) return "";
    const bank = Object.fromEntries(((flow.intelligence || {}).proof_bank || []).map((c) => [c.id, c.claim]));
    const problems = [];
    if ((checks.avoid_words || []).length) problems.push(`uses off-brand words: ${checks.avoid_words.join(", ")}`);
    if ((checks.unknown_proof_ids || []).length) problems.push(`cites claims not on your site (${checks.unknown_proof_ids.join(", ")})`);
    if (problems.length) {
      return `<div class="check-line flag"><i class="fa-solid fa-triangle-exclamation"></i>Check the copy: ${esc(problems.join("; "))}</div>`;
    }
    const cited = (checks.proof_ids || []).filter((id) => bank[id]);
    return cited.length
      ? `<div class="check-line ok"><i class="fa-solid fa-circle-check"></i>Claims from your site: ${cited.map((id) => `“${esc(bank[id])}”`).join(" · ")}</div>`
      : "";
  }

  function renderImageCards() {
    $("image_grid").innerHTML = flow.prompts.image_ads.map((ad) => {
      const bp = ad.blueprint;
      return `
      <article class="ad-card" id="card_${ad.id}">
        <div class="media ${ratioClass(flow.aspect)}">
          <div class="media-empty" id="empty_${ad.id}"><i class="fa-regular fa-image"></i><span>Not rendered yet</span></div>
          <img id="img_${ad.id}" alt="${esc(bp.image_headline)}" hidden>
        </div>
        <div class="ad-body">
          <div class="ad-tag">${esc(ad.angle_name)}${ad.product_name ? ` · ${esc(ad.product_name)}` : ""}</div>
          ${ad.preset_name ? `<div class="preset-chip" title="${esc(ad.preset_movement || '')}"><i class="fa-solid fa-wand-magic-sparkles"></i> ${esc(ad.preset_name)}</div>` : ""}
          <div class="ad-headline" id="hl_${ad.id}">${esc(bp.image_headline)}</div>
          <div class="ad-sub">${esc(bp.primary_text)}</div>
          <details>
            <summary>Edit text &amp; copy</summary>
            <div class="edit-grid">
              <label class="label" for="in_hl_${ad.id}">Headline in image (max 6 words)</label>
              <input class="input" id="in_hl_${ad.id}" data-ad="${ad.id}" data-field="image_headline" value="${esc(bp.image_headline)}">
              <label class="label" for="in_cta_${ad.id}">CTA button</label>
              <input class="input" id="in_cta_${ad.id}" data-ad="${ad.id}" data-field="cta" value="${esc(bp.cta)}">
              <label class="label" for="in_scene_${ad.id}">Scene</label>
              <textarea class="textarea" id="in_scene_${ad.id}" rows="3" data-ad="${ad.id}" data-field="visual_prompt">${esc(bp.visual_prompt)}</textarea>
              <div><button type="button" class="btn btn-sm" data-copy="${ad.id}"><i class="fa-regular fa-copy"></i> Copy ad copy</button></div>
              <pre class="pre">${esc(ad.prompt_preview)}</pre>
            </div>
          </details>
          <div class="why"><i class="fa-solid fa-lightbulb"></i>${esc(ad.rationale)} · ${esc(ad.template_name)}</div>
          ${checksLine(ad.checks)}
          ${(ad.preset_references && ad.preset_references.length) ? `
            <a class="ref-chip" href="${esc(ad.preset_references[0].pin_url || ad.preset_references[0].image_url)}" target="_blank" rel="noopener">
              <img src="${esc(ad.preset_references[0].image_url)}" alt="">Design reference: ${esc(ad.preset_references[0].title || ad.preset_name || 'Pinterest Pin')}
            </a>` : (ad.reference ? `<a class="ref-chip" href="${esc(ad.reference.image_url)}" target="_blank" rel="noopener"><img src="${esc(ad.reference.image_url)}" alt="">Concept and layout from this ${esc(ad.reference.competitor)} ad</a>` : "")}
          <div class="ad-actions">
            <button type="button" class="btn btn-sm" id="btn_${ad.id}" data-render="${ad.id}"><i class="fa-solid fa-play"></i> Render</button>
            <a class="btn btn-sm" id="dl_${ad.id}" hidden download><i class="fa-solid fa-download"></i> Download</a>
          </div>
        </div>
      </article>`;
    }).join("");
  }

  $("image_grid").addEventListener("input", (e) => {
    const { ad, field } = e.target.dataset;
    const item = ad && imageAd(ad);
    if (!item) return;
    item.blueprint[field] = e.target.value;
    if (field === "image_headline") $(`hl_${ad}`).textContent = e.target.value;
  });

  $("image_grid").addEventListener("click", (e) => {
    const render = e.target.closest("[data-render]");
    if (render) return renderImage(render.dataset.render);
    const copy = e.target.closest("[data-copy]");
    if (copy) {
      const bp = imageAd(copy.dataset.copy).blueprint;
      navigator.clipboard.writeText(`Primary text: ${bp.primary_text}\nHeadline: ${bp.headline}\nCTA: ${bp.cta}`)
        .then(() => notify("Ad copy copied.", "success"));
    }
  });

  function setImageState(id, state, message) {
    const has = !!flow.images[id];
    const empty = $(`empty_${id}`);
    const img = $(`img_${id}`);
    const btn = $(`btn_${id}`);
    if (!empty) return;
    const showImage = has && state !== "rendering";
    const wasRendering = empty.classList.contains("is-rendering");
    empty.hidden = showImage;
    img.hidden = !showImage;
    empty.className = `media-empty ${state === "error" ? "error" : state === "rendering" ? "is-rendering" : ""}`;
    if (state === "rendering") renderLoader(empty, "Rendering…", { ratio: flow.aspect, fill: true });
    else empty.innerHTML = state === "error" ? `<i class="fa-solid fa-triangle-exclamation"></i><span>${esc(message)}</span>`
      : `<i class="fa-regular fa-image"></i><span>${esc(message || "Not rendered yet")}</span>`;
    if (wasRendering && showImage) revealRendered(img);
    btn.disabled = state === "rendering";
    btn.innerHTML = has ? '<i class="fa-solid fa-rotate-right"></i> Re-render' : '<i class="fa-solid fa-play"></i> Render';
  }

  async function renderImage(id) {
    const ad = imageAd(id);
    const intel = flow.intelligence;
    if (!ad || !intel || flow.rendering.has(id)) return false;
    if (!getGeminiKey()) {
      requireKey();
      return false;
    }
    const token = flow.token;
    const rendering = flow.rendering;
    rendering.add(id);
    setImageState(id, "rendering");
    flow.activeRenders++;

    const bullseye = intel.bullseye_target || {};
    const fd = new FormData();
    fd.append("blueprint_json", JSON.stringify(ad.blueprint));
    const activePreset = ad.preset_id || ad.blueprint.preset_id || flow.selectedPresetId || "";
    if (activePreset) fd.append("preset_id", activePreset);
    fd.append("brand_name", intel.brand_name || "");
    fd.append("product_name", ad.product_name || intel.product_name || "");
    fd.append("product_category", intel.product_category || "");
    fd.append("target_audience_persona", bullseye.snapshot || "");
    fd.append("product_visual_description", ad.product_lock || intel.product_visual_description || "");
    fd.append("color_palette", intel.color_palette || "");
    fd.append("business_type", intel.business_type || "");
    fd.append("setting", intel.setting || "");
    fd.append("on_screen_talent", bullseye.casting_description || "");
    fd.append("aspect_ratio", flow.aspect);
    if (intel.brand_kit) fd.append("brand_kit_json", JSON.stringify(intel.brand_kit));
    if (intel.logo && intel.logo.path) {
      fd.append("logo_path", intel.logo.path);
      fd.append("logo_tone", intel.logo.tone || "dark");
    }
    // The reference photo locks the product only for physical products (apps/services get a generated hero)
    // Render with the photo of the product this ad is about, not just the first upload
    const productPath = flow.productPaths[ad.product_image_index || 0];
    if (flow.prompts.uses_product_lock && productPath) fd.append("product_image_path", productPath);
    fd.append("model", "nano-banana-2.1");

    try {
      const res = await fetch("/api/campaign/meta-creative-suite/render-one", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Render failed"));
      const result = await res.json();
      if (token !== flow.token) return false;
      flow.images[id] = result;
      $(`img_${id}`).src = result.image_url;
      const dl = $(`dl_${id}`);
      dl.href = result.image_url;
      dl.setAttribute("download", `${(intel.brand_name || "ad").replace(/\W+/g, "_")}_${id}.png`);
      dl.hidden = false;
      setImageState(id, "done");
      return true;
    } catch (err) {
      if (token !== flow.token) return false;
      setImageState(id, "error", err.message);
      return false;
    } finally {
      rendering.delete(id);
      flow.activeRenders = Math.max(0, flow.activeRenders - 1);
    }
  }

  async function renderAllImages() {
    const ads = (flow.prompts && flow.prompts.image_ads) || [];
    if (!ads.length) return;
    if (!(await askConfirm(`Render all ${ads.length} image ads?`, "Each one is a separate image generation.", `Render ${ads.length}`))) return;
    const token = flow.token;
    $("btn_render_all").disabled = true;
    badge("ads_badge", "Rendering images", "running");
    const queue = ads.map((a) => a.id).filter((id) => !flow.rendering.has(id));
    queue.forEach((id) => setImageState(id, "queued", "Queued"));

    let done = 0;
    let failed = 0;
    const progress = () => adsStatus(`Rendering image ads: ${done} of ${ads.length} done${failed ? ` (${failed} failed)` : ""}…`, "busy");
    progress();
    async function worker() {
      while (queue.length && token === flow.token) {
        const ok = await renderImage(queue.shift());
        done++;
        if (!ok) failed++;
        if (token === flow.token) progress();
      }
    }
    await Promise.all(Array.from({ length: IMAGE_RENDER_CONCURRENCY }, worker));
    if (token !== flow.token) return;
    $("btn_render_all").disabled = false;
    badge("ads_badge", "Ready", "done");
    setStep("step_ads", "done");
    adsStatus(
      failed
        ? `${ads.length - failed} of ${ads.length} image ads rendered. Use Render on the failed cards to retry.`
        : `All ${ads.length} image ads rendered.`,
      failed ? "error" : "done",
    );
  }

  // ------------------------------------------------------------ video ads
  function videoAd(id) {
    return ((flow.prompts && flow.prompts.video_ads) || []).find((a) => a.id === id);
  }

  function renderVideoCards() {
    $("video_grid").innerHTML = flow.prompts.video_ads.map((ad) => {
      const resVal = ad.resolution || flow.videoRes || "720p";
      return `
      <article class="ad-card" id="vcard_${ad.id}">
        <div class="media r-9-16">
          <div class="media-empty" id="vempty_${ad.id}"><i class="fa-solid fa-film"></i><span>Not rendered yet</span></div>
          <video id="video_${ad.id}" controls playsinline hidden></video>
        </div>
        <div class="ad-body">
          <div class="ad-tag">${esc(ad.angle_name)}${(ad.product_names || []).length ? ` · ${esc(ad.product_names.join(" + "))}` : ""} · ${esc(ad.duration_s)}s · <span class="vcard-res">${esc(resVal)}</span></div>
          <div class="ad-headline">“${esc(ad.hook_line)}”</div>
          <div class="ad-sub">${esc(ad.voiceover)}</div>
          <details>
            <summary>Script &amp; Omni Flash prompt</summary>
            <ol class="beats" style="margin-top: 8px;">
              ${(ad.beats || []).map((b) => `<li><span class="t">${esc(b.time)}</span> ${esc(b.visual)}${b.on_screen_text ? ` <em>“${esc(b.on_screen_text)}”</em>` : ""}</li>`).join("")}
            </ol>
            <div class="edit-grid">
              <label class="label" for="vprompt_${ad.id}">Omni Flash prompt (editable)</label>
              <textarea class="textarea" id="vprompt_${ad.id}" rows="10" data-vad="${ad.id}" style="font-family: var(--font-mono); font-size: 0.74rem;">${esc(ad.omni_prompt)}</textarea>
            </div>
          </details>
          <div class="why"><i class="fa-solid fa-lightbulb"></i>${esc(ad.rationale)}${ad.reference ? ` · Hook adapted from a ${esc(ad.reference.competitor)} ad` : ""}</div>
          ${checksLine(ad.checks)}
          <div class="ad-actions">
            <select class="select select-sm ad-res-select" data-vad-res="${ad.id}" title="Video resolution">
              <option value="720p" ${resVal === "720p" ? "selected" : ""}>720p</option>
              <option value="1080p" ${resVal === "1080p" ? "selected" : ""}>1080p</option>
              <option value="4k" ${resVal === "4k" ? "selected" : ""}>4K</option>
            </select>
            <button type="button" class="btn btn-sm" id="vbtn_${ad.id}" data-vrender="${ad.id}"><i class="fa-solid fa-clapperboard"></i> Render video</button>
            <a class="btn btn-sm" id="vdl_${ad.id}" hidden download><i class="fa-solid fa-download"></i> Download</a>
          </div>
        </div>
      </article>`;
    }).join("");
  }

  $("video_grid").addEventListener("input", (e) => {
    const ad = e.target.dataset.vad && videoAd(e.target.dataset.vad);
    if (ad) ad.omni_prompt = e.target.value;
  });

  $("video_grid").addEventListener("change", (e) => {
    const sel = e.target.closest("[data-vad-res]");
    if (sel) {
      const ad = videoAd(sel.dataset.vadRes);
      if (ad) {
        ad.resolution = sel.value;
        ad.custom_res = true;
        const tag = $(`vcard_${ad.id}`)?.querySelector(".vcard-res");
        if (tag) tag.textContent = sel.value;
      }
    }
  });

  $("video_grid").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-vrender]");
    if (btn) renderVideo(btn.dataset.vrender);
  });

  function setVideoState(id, state, message) {
    const has = !!flow.videos[id];
    const empty = $(`vempty_${id}`);
    const video = $(`video_${id}`);
    const btn = $(`vbtn_${id}`);
    const showVideo = has && state !== "rendering";
    const wasRendering = empty.classList.contains("is-rendering");
    empty.hidden = showVideo;
    video.hidden = !showVideo;
    empty.className = `media-empty ${state === "error" ? "error" : state === "rendering" ? "is-rendering" : ""}`;
    if (state === "rendering") renderLoader(empty, message || "Rendering with Omni Flash…", { ratio: "9:16", fill: true });
    else empty.innerHTML = state === "error" ? `<i class="fa-solid fa-triangle-exclamation"></i><span>${esc(message)}</span>`
      : `<i class="fa-solid fa-film"></i><span>Not rendered yet</span>`;
    if (wasRendering && showVideo) revealRendered(video);
    btn.disabled = state === "rendering";
    btn.innerHTML = has ? '<i class="fa-solid fa-rotate-right"></i> Re-render' : '<i class="fa-solid fa-clapperboard"></i> Render video';
  }

  async function renderVideo(id) {
    const ad = videoAd(id);
    if (!ad || !requireKey()) return;
    const token = flow.token;
    const chosenRes = ad.resolution || flow.videoRes || "1080p";
    setVideoState(id, "rendering", `Sending ${chosenRes} video to Omni Flash…`);
    flow.activeRenders++;

    const fd = new FormData();
    fd.append("mode", "prompt_images");
    fd.append("prompt", ad.omni_prompt);
    fd.append("aspect_ratio", ad.aspect_ratio || "9:16");
    fd.append("resolution", chosenRes);
    fd.append("duration", String(ad.duration_s || 15));
    // Attach only the featured products' photos, in the <IMAGE_REF_n> order the prompt describes them
    const refFiles = (ad.ref_image_indexes || []).length
      ? ad.ref_image_indexes.map((i) => flow.files[i]).filter(Boolean)
      : flow.files;
    refFiles.slice(0, MAX_VIDEO_REFS).forEach((f) => fd.append("reference_images", f));

    try {
      const res = await fetch("/api/studio/generate-video", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Could not start the video"));
      const { job_id } = await res.json();
      setVideoState(id, "rendering", "Omni Flash is rendering… usually a few minutes");
      const job = await pollJob(job_id, {
        onProgress: (j) => { if (token === flow.token && j.progress_msg) setVideoState(id, "rendering", j.progress_msg); },
      });
      if (token !== flow.token) return;
      flow.videos[id] = job.video_url;
      ad.rendered_resolution = job.resolution || chosenRes;
      $(`video_${id}`).src = job.video_url;
      const dl = $(`vdl_${id}`);
      dl.href = job.video_url;
      dl.hidden = false;
      setVideoState(id, "done");
      notify(`Video ad “${ad.angle_name}” (${ad.rendered_resolution}) is ready.`, "success");
    } catch (err) {
      if (token !== flow.token) return;
      setVideoState(id, "error", err.message);
      notify(`Video render failed: ${err.message}`, "error");
    } finally {
      flow.activeRenders = Math.max(0, flow.activeRenders - 1);
    }
  }

  // Leaving with research or renders in progress loses the page state
  window.addEventListener("beforeunload", (e) => {
    if (flow.pollTimer || flow.activeRenders > 0) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
})();
