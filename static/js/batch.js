// Batch Prompt Studio: Bulk generation from Markdown files with automated rate-limit queueing.
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = escapeHtml;

  let parsedPrompts = [];
  let referenceFiles = [];
  let currentBatchId = null;
  let pollTimer = null;
  let isPaused = false;

  function getMaxRefs() {
    const m = (typeof getModel === "function" ? getModel() : null) || "nano-banana-pro";
    return m === "nano-banana-2.1" ? 14 : 6;
  }

  function updateRefLimitNotice(m) {
    const modelKey = m || (typeof getModel === "function" ? getModel() : null) || "nano-banana-pro";
    const maxRefs = modelKey === "nano-banana-2.1" ? 14 : 6;
    const labelEl = $("batch_ref_limit_label");
    if (labelEl) {
      labelEl.textContent = `· optional, up to ${maxRefs} for ${modelKey === "nano-banana-2.1" ? "Nano Banana 2.1" : "Nano Banana Pro"}`;
    }
  }

  // ---------------------------------------------------------------------------
  // Reference Images Dropzone
  // ---------------------------------------------------------------------------
  function initRefDropzone() {
    const drop = $("batch_ref_drop");
    const input = $("batch_ref_files");
    const thumbs = $("batch_ref_thumbs");

    function renderThumbs() {
      thumbs.innerHTML = "";
      referenceFiles.forEach((file, i) => {
        const wrap = document.createElement("div");
        wrap.className = "thumb";
        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        img.alt = file.name;
        const rm = document.createElement("button");
        rm.type = "button";
        rm.className = "thumb-rm";
        rm.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        rm.title = "Remove reference image";
        rm.onclick = (e) => {
          e.stopPropagation();
          referenceFiles.splice(i, 1);
          renderThumbs();
        };
        wrap.appendChild(img);
        wrap.appendChild(rm);
        thumbs.appendChild(wrap);
      });
      drop.classList.toggle("has-thumbs", referenceFiles.length > 0);
    }

    drop.addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
      const max = getMaxRefs();
      const added = Array.from(input.files || []).slice(0, Math.max(0, max - referenceFiles.length));
      referenceFiles.push(...added);
      input.value = "";
      renderThumbs();
    });

    drop.addEventListener("dragover", (e) => {
      e.preventDefault();
      drop.classList.add("dragover");
    });
    drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      drop.classList.remove("dragover");
      const files = Array.from(e.dataTransfer?.files || []).filter((f) => f.type.startsWith("image/"));
      const max = getMaxRefs();
      const added = files.slice(0, Math.max(0, max - referenceFiles.length));
      referenceFiles.push(...added);
      renderThumbs();
    });
  }

  // ---------------------------------------------------------------------------
  // Markdown Files Upload & Parsing
  // ---------------------------------------------------------------------------
  function initMarkdownDropzone() {
    const drop = $("batch_md_drop");
    const input = $("batch_md_files");

    async function handleFiles(files) {
      const validFiles = Array.from(files).filter((f) => {
        const name = (f.name || "").toLowerCase();
        return name.endsWith(".md") || name.endsWith(".markdown") || name.endsWith(".txt") || f.type.includes("text");
      });

      if (!validFiles.length) {
        notify("Please select or drop Markdown (.md) or text (.txt) files.", "warning");
        return;
      }

      drop.classList.add("busy");
      drop.querySelector(".dropzone-cta span").textContent = `Parsing ${validFiles.length} file(s)...`;

      const fd = new FormData();
      validFiles.forEach((f) => fd.append("files", f));

      try {
        const res = await fetch("/api/batch-prompts/parse", {
          method: "POST",
          headers: apiHeaders(),
          body: fd,
        });

        if (!res.ok) {
          throw new Error(await readErrorDetail(res, "Could not parse prompt files."));
        }

        const data = await res.json();
        const incoming = data.prompts || [];

        if (!incoming.length) {
          notify("No prompts could be detected in the uploaded file(s).", "warning");
          return;
        }

        // Append to existing or replace
        const startId = parsedPrompts.length;
        incoming.forEach((p, idx) => {
          p.id = startId + idx + 1;
          p.selected = true;
        });

        parsedPrompts.push(...incoming);
        if (parsedPrompts.length > 100) {
          notify(`Notice: 100 prompts maximum per batch. Keeping first 100 of ${parsedPrompts.length}.`, "info");
          parsedPrompts = parsedPrompts.slice(0, 100);
        }

        renderPromptList();
        renderFileTags(validFiles);
        notify(`Parsed ${incoming.length} prompt(s) successfully! Total ready: ${parsedPrompts.length}`, "success");

      } catch (err) {
        notify(err.message, "error");
      } finally {
        drop.classList.remove("busy");
        drop.querySelector(".dropzone-cta span").textContent = "Drop .md or .txt files or click to browse";
        input.value = "";
      }
    }

    drop.addEventListener("click", () => input.click());
    input.addEventListener("change", () => handleFiles(input.files));

    drop.addEventListener("dragover", (e) => {
      e.preventDefault();
      drop.classList.add("dragover");
    });
    drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
    drop.addEventListener("drop", (e) => {
      e.preventDefault();
      drop.classList.remove("dragover");
      if (e.dataTransfer?.files?.length) {
        handleFiles(e.dataTransfer.files);
      }
    });
  }

  function renderFileTags(files) {
    const container = $("batch_file_tags");
    files.forEach((f) => {
      const tag = document.createElement("span");
      tag.className = "badge batch-file-pill";
      tag.innerHTML = `<i class="fa-regular fa-file-lines"></i> ${esc(f.name)}`;
      container.appendChild(tag);
    });
  }

  // ---------------------------------------------------------------------------
  // Prompt List Rendering & Editing
  // ---------------------------------------------------------------------------
  function renderPromptList() {
    const list = $("batch_prompt_list");
    const countEl = $("batch_prompt_count");
    const actionsEl = $("batch_list_actions");
    const startBtn = $("batch_start_btn");

    countEl.textContent = parsedPrompts.length;
    actionsEl.hidden = parsedPrompts.length === 0;
    startBtn.disabled = parsedPrompts.length === 0;

    if (!parsedPrompts.length) {
      list.innerHTML = `
        <div class="batch-empty-prompts">
          <i class="fa-solid fa-list-check"></i>
          <span>No prompts loaded yet. Drop one or more .md files above.</span>
        </div>`;
      return;
    }

    list.innerHTML = "";
    parsedPrompts.forEach((item, index) => {
      const card = document.createElement("div");
      card.className = "batch-prompt-card";
      card.dataset.index = index;

      const aspectBadge = item.aspect_ratio ? `<span class="badge badge-accent">${esc(item.aspect_ratio)}</span>` : "";
      const sourceBadge = item.source_file ? `<span class="badge" title="Source file">${esc(item.source_file)}</span>` : "";

      card.innerHTML = `
        <div class="batch-prompt-header">
          <label class="batch-check-label">
            <input type="checkbox" class="batch-prompt-select" ${item.selected ? "checked" : ""} data-idx="${index}">
            <span class="batch-prompt-num">#${item.id}</span>
            <strong class="batch-prompt-title" contenteditable="true" title="Click to edit title">${esc(item.title)}</strong>
          </label>
          <div class="batch-prompt-meta">
            ${aspectBadge}
            ${sourceBadge}
            <button type="button" class="btn-icon batch-prompt-del" title="Remove prompt" data-idx="${index}"><i class="fa-solid fa-xmark"></i></button>
          </div>
        </div>
        <div class="batch-prompt-body">
          <textarea class="textarea batch-prompt-textarea" rows="2" data-idx="${index}">${esc(item.prompt)}</textarea>
        </div>
      `;

      // Event handlers
      const check = card.querySelector(".batch-prompt-select");
      check.addEventListener("change", (e) => {
        item.selected = e.target.checked;
        updateSelectedCount();
      });

      const titleEl = card.querySelector(".batch-prompt-title");
      titleEl.addEventListener("blur", (e) => {
        item.title = e.target.textContent.trim() || `Prompt ${item.id}`;
      });

      const textEl = card.querySelector(".batch-prompt-textarea");
      textEl.addEventListener("input", (e) => {
        item.prompt = e.target.value.trim();
      });

      const delBtn = card.querySelector(".batch-prompt-del");
      delBtn.addEventListener("click", () => {
        parsedPrompts.splice(index, 1);
        // renumber
        parsedPrompts.forEach((p, i) => (p.id = i + 1));
        renderPromptList();
      });

      list.appendChild(card);
    });

    updateSelectedCount();
  }

  function updateSelectedCount() {
    const selCount = parsedPrompts.filter((p) => p.selected).length;
    const btn = $("batch_start_btn");
    btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Start batch generation (${selCount})`;
    btn.disabled = selCount === 0;
  }

  // Clear & Select All
  $("batch_clear_all")?.addEventListener("click", () => {
    parsedPrompts = [];
    $("batch_file_tags").innerHTML = "";
    renderPromptList();
  });

  $("batch_select_all")?.addEventListener("click", () => {
    const allSelected = parsedPrompts.every((p) => p.selected);
    parsedPrompts.forEach((p) => (p.selected = !allSelected));
    renderPromptList();
  });

  // ---------------------------------------------------------------------------
  // Batch Execution & Queue Engine
  // ---------------------------------------------------------------------------
  const getAspect = segmented("batch_aspect", "ratio");
  const getModel = segmented("batch_model", "model", (newModel) => {
    updateRefLimitNotice(newModel);
  });
  const getDelay = segmented("batch_delay", "delay");

  $("batch_start_btn")?.addEventListener("click", async () => {
    if (!requireKey()) return;

    const selected = parsedPrompts.filter((p) => p.selected && p.prompt.trim());
    if (!selected.length) {
      notify("Select at least 1 prompt to run.", "warning");
      return;
    }

    const startBtn = $("batch_start_btn");
    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="spinner"></span> Starting queue…';

    const selectedModel = getModel() || "nano-banana-pro";
    const fd = new FormData();
    fd.append("prompts", JSON.stringify(selected));
    fd.append("model", selectedModel);
    fd.append("aspect_ratio", getAspect() || "1:1");
    fd.append("rate_limit_delay_s", getDelay() || "2.5");

    referenceFiles.forEach((file) => fd.append("reference_images", file));

    try {
      const res = await fetch("/api/batch-prompts/start", {
        method: "POST",
        headers: apiHeaders(),
        body: fd,
      });

      if (!res.ok) {
        throw new Error(await readErrorDetail(res, "Could not start batch run."));
      }

      const data = await res.json();
      currentBatchId = data.batch_id;
      isPaused = false;

      // Switch stage to running
      initStageRunning(selected.length, selectedModel);
      startPolling(currentBatchId);
      notify(`Batch #${currentBatchId} started! Automated queue is processing prompts.`, "info");

    } catch (err) {
      notify(err.message, "error");
      updateSelectedCount();
    }
  });

  function initStageRunning(total, modelKey) {
    $("batch_stage_empty").hidden = true;
    $("batch_stage_active").hidden = false;
    $("batch_meter_fill").style.width = "0%";
    $("batch_meter_val").textContent = `0 / ${total}`;
    const badge = $("batch_model_badge");
    if (badge) {
      const m = modelKey || (typeof getModel === "function" ? getModel() : "") || "nano-banana-pro";
      badge.textContent = m === "nano-banana-2.1" ? "Nano Banana 2.1" : "Nano Banana Pro";
      badge.hidden = false;
    }
    $("batch_results_grid").innerHTML = "";
    $("batch_zip_btn").hidden = true;
    $("batch_pause_btn").hidden = false;
    $("batch_resume_btn").hidden = true;
    $("batch_cancel_btn").hidden = false;
    $("batch_alert").hidden = false;
    $("batch_alert").className = "batch-alert info";
    $("batch_alert").innerHTML = '<span class="spinner"></span> Initializing queue and checking API rate limits...';
  }

  function startPolling(batchId) {
    if (pollTimer) clearInterval(pollTimer);

    async function poll() {
      try {
        const res = await fetch(`/api/batch-prompts/status/${encodeURIComponent(batchId)}`);
        if (!res.ok) return;

        const job = await res.json();
        updateQueueUI(job);

        if (["completed", "cancelled", "failed"].includes(job.status)) {
          clearInterval(pollTimer);
          pollTimer = null;
          updateSelectedCount();
          if (job.status === "completed") {
            notify(`Batch generation complete! Generated ${job.completed_count} images.`, "success");
          } else if (job.status === "cancelled") {
            notify("Batch run cancelled.", "warning");
          } else if (job.status === "failed") {
            notify(`Batch failed: ${job.error || "Unknown error"}`, "error");
          }
        }
      } catch (e) {
        // network blip, continue polling
      }
    }

    poll();
    pollTimer = setInterval(poll, 2200);
  }

  function updateQueueUI(job) {
    const total = job.total_count || 1;
    const completed = job.completed_count || 0;
    const failed = job.failed_count || 0;
    const pct = Math.min(100, Math.round(((completed + failed) / total) * 100));

    $("batch_meter_fill").style.width = `${pct}%`;
    $("batch_meter_val").textContent = `${completed} / ${total} (${pct}%)`;

    const badge = $("batch_model_badge");
    if (badge && job.model) {
      badge.textContent = job.model === "nano-banana-2.1" ? "Nano Banana 2.1" : "Nano Banana Pro";
      badge.hidden = false;
    }

    // Rate limit alert badge
    const alertEl = $("batch_alert");
    if (job.rate_limit_notice) {
      alertEl.hidden = false;
      const isCooling = job.rate_limit_notice.includes("Rate limit reached") || job.rate_limit_notice.includes("Cooling down");
      alertEl.className = isCooling ? "batch-alert warning" : "batch-alert info";
      alertEl.innerHTML = `${isCooling ? '<i class="fa-solid fa-hourglass-half"></i>' : '<span class="spinner"></span>'} <span>${esc(job.rate_limit_notice)}</span>`;
    } else if (job.status === "completed") {
      alertEl.className = "batch-alert success";
      alertEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> Batch completed: ${completed} image(s) generated successfully${failed > 0 ? `, ${failed} failed` : ""}.`;
    } else {
      alertEl.hidden = true;
    }

    // Zip button
    if (job.zip_url) {
      const zipBtn = $("batch_zip_btn");
      zipBtn.hidden = false;
      zipBtn.href = job.zip_url;
    }

    // Controls
    $("batch_pause_btn").hidden = job.status === "paused" || ["completed", "cancelled", "failed"].includes(job.status);
    $("batch_resume_btn").hidden = job.status !== "paused";
    $("batch_cancel_btn").hidden = ["completed", "cancelled", "failed"].includes(job.status);

    // Live Render Grid
    renderResultsGrid(job.prompts || []);
  }

  function renderResultsGrid(items) {
    const grid = $("batch_results_grid");

    items.forEach((item) => {
      let card = grid.querySelector(`[data-result-id="${item.id}"]`);

      if (!card) {
        card = document.createElement("div");
        card.className = "batch-res-card";
        card.dataset.resultId = item.id;
        grid.appendChild(card);
      }

      if (item.status === "success" && item.image_url) {
        card.className = "batch-res-card success";
        card.innerHTML = `
          <div class="batch-res-thumb">
            <img src="${esc(item.image_url)}" alt="${esc(item.title)}" loading="lazy">
            <span class="badge badge-accent batch-res-tag">#${item.id}</span>
          </div>
          <div class="batch-res-info">
            <div class="batch-res-title" title="${esc(item.title)}">${esc(item.title)}</div>
            <div class="batch-res-actions">
              <a href="${esc(item.image_url)}" download="${esc(item.filename || `ad_${item.id}.png`)}" class="btn btn-sm btn-ghost" title="Download image"><i class="fa-solid fa-download"></i> Save</a>
              <button type="button" class="btn btn-sm btn-ghost btn-copy-prompt" data-prompt="${esc(item.prompt)}" title="Copy prompt"><i class="fa-solid fa-copy"></i> Copy</button>
            </div>
          </div>
        `;
      } else if (item.status === "processing") {
        card.className = "batch-res-card processing";
        card.innerHTML = `
          <div class="batch-res-placeholder">
            <span class="spinner"></span>
            <span>Generating #${item.id}…</span>
          </div>
          <div class="batch-res-info">
            <div class="batch-res-title">${esc(item.title)}</div>
            <span class="badge badge-warning">Rendering</span>
          </div>`;
      } else if (item.status === "retrying") {
        card.className = "batch-res-card retrying";
        card.innerHTML = `
          <div class="batch-res-placeholder">
            <i class="fa-solid fa-hourglass-half"></i>
            <span>Rate limit cooling…</span>
          </div>
          <div class="batch-res-info">
            <div class="batch-res-title">${esc(item.title)}</div>
            <span class="badge badge-warning">Attempt ${item.attempts || 1}</span>
          </div>`;
      } else if (item.status === "failed") {
        card.className = "batch-res-card failed";
        card.innerHTML = `
          <div class="batch-res-placeholder error">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>Generation failed</span>
          </div>
          <div class="batch-res-info">
            <div class="batch-res-title">${esc(item.title)}</div>
            <div class="batch-res-err" title="${esc(item.error || '')}">${esc(item.error || 'Failed')}</div>
          </div>`;
      } else {
        card.className = "batch-res-card pending";
        card.innerHTML = `
          <div class="batch-res-placeholder muted">
            <i class="fa-solid fa-clock"></i>
            <span>Queued #${item.id}</span>
          </div>
          <div class="batch-res-info">
            <div class="batch-res-title">${esc(item.title)}</div>
            <span class="badge">In queue</span>
          </div>`;
      }
    });

    // Copy prompt handlers
    grid.querySelectorAll(".btn-copy-prompt").forEach((btn) => {
      btn.onclick = () => {
        navigator.clipboard.writeText(btn.dataset.prompt);
        notify("Prompt copied to clipboard!", "success");
      };
    });
  }

  // ---------------------------------------------------------------------------
  // Control Buttons
  // ---------------------------------------------------------------------------
  $("batch_pause_btn")?.addEventListener("click", async () => {
    if (!currentBatchId) return;
    try {
      await fetch(`/api/batch-prompts/pause/${encodeURIComponent(currentBatchId)}`, {
        method: "POST",
        headers: apiHeaders(),
      });
      isPaused = true;
      $("batch_pause_btn").hidden = true;
      $("batch_resume_btn").hidden = false;
      notify("Queue paused.", "info");
    } catch (e) {
      notify("Could not pause queue.", "error");
    }
  });

  $("batch_resume_btn")?.addEventListener("click", async () => {
    if (!currentBatchId) return;
    try {
      await fetch(`/api/batch-prompts/resume/${encodeURIComponent(currentBatchId)}`, {
        method: "POST",
        headers: apiHeaders(),
      });
      isPaused = false;
      $("batch_resume_btn").hidden = true;
      $("batch_pause_btn").hidden = false;
      notify("Queue resumed.", "info");
    } catch (e) {
      notify("Could not resume queue.", "error");
    }
  });

  $("batch_cancel_btn")?.addEventListener("click", async () => {
    if (!currentBatchId) return;
    const ok = await askConfirm("Cancel Batch Queue?", "Remaining queued prompts will not be generated.");
    if (!ok) return;

    try {
      await fetch(`/api/batch-prompts/cancel/${encodeURIComponent(currentBatchId)}`, {
        method: "POST",
        headers: apiHeaders(),
      });
      notify("Queue cancelled.", "warning");
    } catch (e) {
      notify("Could not cancel queue.", "error");
    }
  });

  // ---------------------------------------------------------------------------
  // History Loading
  // ---------------------------------------------------------------------------
  async function loadBatchHistory() {
    try {
      const res = await fetch("/api/batch-prompts/history");
      if (!res.ok) return;
      const data = await res.json();
      const list = $("batch_history_list");
      if (!list) return;

      const batches = data.batches || [];
      if (!batches.length) {
        list.innerHTML = '<span class="muted" style="font-size:0.82rem;">No recent batch jobs</span>';
        return;
      }

      list.innerHTML = "";
      batches.slice(0, 5).forEach((b) => {
        const item = document.createElement("div");
        item.className = "batch-hist-item";
        const modelLabel = b.model === "nano-banana-2.1" ? "Nano Banana 2.1" : "Nano Banana Pro";
        item.innerHTML = `
          <div class="batch-hist-main">
            <strong class="batch-hist-id">${esc(b.batch_id)}</strong>
            <span class="muted small">${esc(modelLabel)} · <span class="num">${b.completed_count}/${b.total_count}</span> generated</span>
          </div>
          <div class="batch-hist-actions">
            ${b.zip_url ? `<a href="${esc(b.zip_url)}" class="btn-link" title="Download ZIP"><i class="fa-solid fa-download"></i> ZIP</a>` : ""}
            <button type="button" class="btn-link batch-load-job" data-id="${esc(b.batch_id)}">View</button>
          </div>
        `;
        item.querySelector(".batch-load-job")?.addEventListener("click", () => {
          currentBatchId = b.batch_id;
          initStageRunning(b.total_count, b.model);
          startPolling(b.batch_id);
        });
        list.appendChild(item);
      });
    } catch (e) {
      // ignore history load error
    }
  }

  window.addEventListener("viewchange", (e) => {
    if (e.detail === "batch") {
      updateRefLimitNotice();
      loadBatchHistory();
    }
  });

  // ---------------------------------------------------------------------------
  // Initialize
  // ---------------------------------------------------------------------------
  initRefDropzone();
  initMarkdownDropzone();
  updateRefLimitNotice();
})();
