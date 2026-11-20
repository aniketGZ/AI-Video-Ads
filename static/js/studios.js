// Image studio (Nano Banana Pro) and video studio (Omni Flash): one-off generations outside the campaign flow.
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = escapeHtml;

  function showResult(container, html) {
    $(container).innerHTML = html;
  }

  function busy(container, text, ratio) {
    renderLoader(container, text, { ratio });
  }

  function failed(container, text) {
    showResult(container, `<div class="media-empty error"><i class="fa-solid fa-triangle-exclamation"></i><span>${esc(text)}</span>
      <div class="result-bar"><button type="button" class="btn btn-sm" data-retry>Try again</button><button type="button" class="btn btn-sm btn-ghost" data-dismiss-result>Dismiss</button></div></div>`);
  }

  // The Generate button says what the app is doing; the blur hides the swap between the two labels
  function setBusy(btn, busy, sync) {
    btn.disabled = busy;
    if (busy) btn.innerHTML = '<span class="spinner"></span> Generating…';
    else sync();
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      btn.animate([{ filter: "blur(3px)", opacity: 0.6 }, { filter: "blur(0)", opacity: busy ? 0.85 : 1 }], { duration: 200, easing: "ease-out" });
    }
  }
  const submitKey = `<kbd>${MOD_KEY} ↵</kbd>`;

  const MAX_PROMPTS = 5;

  // ------------------------------------------------------------ prompt drop helper (accepts text, markdown, and reference images)
  function wireMarkdownDrop({ containerId, getBoxes, addBtnId, onUpdate, onImageDrop }) {
    const container = $(containerId);
    if (!container) return;

    function isMdFile(f) {
      const name = (f.name || "").toLowerCase();
      return name.endsWith(".md") || name.endsWith(".markdown") || name.endsWith(".txt") || f.type === "text/markdown";
    }

    function readAsText(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsText(file);
      });
    }

    async function handleDrop(e, targetTextarea) {
      const files = Array.from(e.dataTransfer?.files || []);
      if (!files.length) return; // Allow native text drag/drop
      e.preventDefault();
      e.stopPropagation();
      container.classList.remove("dragover");
      if (targetTextarea) targetTextarea.classList.remove("dragover");

      // Ingest dropped images as reference images
      const imageFiles = files.filter((f) => f.type.startsWith("image/"));
      if (imageFiles.length && onImageDrop) {
        onImageDrop(imageFiles);
        notify(imageFiles.length === 1 ? `Added ${imageFiles[0].name} as reference image` : `Added ${imageFiles.length} reference images`, "success");
      }

      // Ingest markdown or text prompt files
      const mdFiles = files.filter(isMdFile);
      if (!mdFiles.length) {
        if (!imageFiles.length) {
          notify("Please drop an image or a text/markdown file.", "info");
        }
        return;
      }

      const boxes = getBoxes();
      let startIdx = targetTextarea ? boxes.indexOf(targetTextarea) : 0;
      if (startIdx < 0) startIdx = 0;

      for (let i = 0; i < mdFiles.length; i++) {
        const file = mdFiles[i];
        let currentBoxes = getBoxes();
        let targetBox = currentBoxes[startIdx + i];
        if (!targetBox && addBtnId && $(addBtnId) && !$(addBtnId).hidden && currentBoxes.length < MAX_PROMPTS) {
          $(addBtnId).click();
          currentBoxes = getBoxes();
          targetBox = currentBoxes[startIdx + i];
        }
        if (!targetBox) break;

        try {
          const text = await readAsText(file);
          targetBox.value = text.trim();
          targetBox.dispatchEvent(new Event("input", { bubbles: true }));
          targetBox.dispatchEvent(new Event("change", { bubbles: true }));
        } catch (err) {
          notify(`Could not read ${file.name}`, "error");
        }
      }

      if (onUpdate) onUpdate();
      notify(mdFiles.length === 1 ? `Loaded prompt from ${mdFiles[0].name}` : `Loaded ${mdFiles.length} prompt files`, "info");
    }

    container.addEventListener("dragover", (e) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        e.preventDefault();
        const ta = e.target.closest("textarea");
        if (ta) ta.classList.add("dragover");
        else container.classList.add("dragover");
      }
    });

    container.addEventListener("dragleave", (e) => {
      const ta = e.target.closest("textarea");
      if (ta) ta.classList.remove("dragover");
      if (!e.relatedTarget || !container.contains(e.relatedTarget)) {
        container.classList.remove("dragover");
      }
    });

    container.addEventListener("drop", (e) => {
      const ta = e.target.closest("textarea");
      handleDrop(e, ta);
    });
  }

  // ------------------------------------------------------------ image studio
  const imgRefs = imageDropzone({ zone: "img_drop", input: "img_files", thumbs: "img_thumbs", max: 6 });
  const imgAspect = segmented("img_aspect", "ratio");
  const imgResolution = segmented("img_resolution", "res");
  const imgModel = segmented("img_model", "model", (m) => {
    const is21 = m === "nano-banana-2.1";
    const max = is21 ? 14 : 6;
    if (imgRefs && imgRefs.setMax) imgRefs.setMax(max);
    const hint = $("img_refs_hint");
    if (hint) hint.textContent = `· optional, up to ${max} · product photos, styling or packaging`;
  });

  function showImage(url, meta) {
    const dim = meta && meta.width && meta.height ? `${meta.width}×${meta.height}` : "";
    showResult("img_result", `<figure class="result-card">
      <img src="${esc(url)}" alt="Generated image ad">
      <figcaption class="result-bar">
        ${meta && meta.resolution ? `<span class="badge badge-accent">${esc(meta.resolution)}</span>` : ""}
        ${meta && meta.aspect_ratio ? `<span class="badge">${esc(meta.aspect_ratio)}</span>` : ""}
        ${dim ? `<span class="muted small num">${esc(dim)}</span>` : ""}
        <a href="${esc(url)}" download class="btn btn-sm"><i class="fa-solid fa-download"></i> Download</a>
        <button type="button" class="btn btn-sm btn-ghost" data-dismiss-result><i class="fa-solid fa-xmark"></i> Close</button>
      </figcaption>
    </figure>`);
  }

  function imgPromptBoxes() {
    return Array.from($("img_prompts").querySelectorAll("[data-prompt]"));
  }

  function syncImgPromptUi() {
    const boxes = imgPromptBoxes();
    $("img_prompts").querySelectorAll(".prompt-extra .label").forEach((el, i) => { el.textContent = `Prompt ${i + 2}`; });
    $("img_add_prompt").hidden = boxes.length >= MAX_PROMPTS;
    const n = boxes.filter((b) => b.value.trim()).length || 1;
    $("img_submit").innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Generate ${n > 1 ? `${n} images` : "image"} ${submitKey}`;
  }

  $("img_add_prompt").addEventListener("click", () => {
    if (imgPromptBoxes().length >= MAX_PROMPTS) return;
    const wrap = document.createElement("div");
    wrap.className = "prompt-extra";
    wrap.innerHTML = `
      <div class="prompt-extra-head">
        <span class="label"></span>
        <button type="button" class="btn-link" data-remove-prompt>Remove</button>
      </div>
      <textarea class="textarea" data-prompt rows="4" placeholder="Another prompt, rendered as its own image"></textarea>`;
    $("img_prompts").appendChild(wrap);
    syncImgPromptUi();
    wrap.querySelector("textarea").focus();
  });

  $("img_prompts").addEventListener("click", (e) => {
    const rm = e.target.closest("[data-remove-prompt]");
    if (!rm) return;
    rm.closest(".prompt-extra").remove();
    syncImgPromptUi();
  });
  $("img_prompts").addEventListener("input", syncImgPromptUi);

  wireMarkdownDrop({
    containerId: "img_prompts",
    getBoxes: imgPromptBoxes,
    addBtnId: "img_add_prompt",
    onUpdate: syncImgPromptUi,
    onImageDrop: (imgs) => imgRefs.add(imgs),
  });

  async function loadImageHistory() {
    try {
      const res = await fetch("/api/image-studio/history");
      if (!res.ok) return;
      const { images } = await res.json();
      $("img_history").innerHTML = (images || []).map((i) =>
        `<button type="button" data-url="${esc(i.url)}" aria-label="Open this image"><img src="/api/thumb/${encodeURIComponent(i.filename)}" alt="" loading="lazy" decoding="async"></button>`
      ).join("");
    } catch (e) { /* history is optional */ }
    $("img_history").removeAttribute("data-loading");
  }

  $("img_form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompts = imgPromptBoxes().map((b) => b.value.trim()).filter(Boolean);
    if (!prompts.length) return notify("Write a prompt first.", "warning");
    if (!requireKey()) return;

    const selectedModel = imgModel() || "nano-banana-pro";
    const selectedRes = imgResolution() || "1K";
    const modelLabel = selectedModel === "nano-banana-2.1" ? "Nano Banana 2.1" : "Nano Banana Pro";

    if (prompts.length > 1 && !(await askConfirm(
      `Generate ${prompts.length} images?`,
      `Each prompt is a separate ${modelLabel} render (${selectedRes}).`,
      `Generate ${prompts.length}`,
      { skipKey: "multi_image" }
    ))) return;

    const fd = new FormData();
    fd.append("model", selectedModel);
    fd.append("prompts", JSON.stringify(prompts));
    fd.append("prompt", prompts[0]);
    fd.append("aspect_ratio", imgAspect() || "1:1");
    fd.append("resolution", selectedRes);
    if ($("img_style").value) fd.append("style_preset", $("img_style").value);

    const refFiles = imgRefs.files();
    refFiles.forEach((f) => fd.append("reference_images", f));
    if (refFiles[0]) fd.append("product_image", refFiles[0]);

    const imgFolderId = $("img_folder_id") ? $("img_folder_id").value : "";
    if (imgFolderId) fd.append("folder_id", imgFolderId);

    setBusy($("img_submit"), true, syncImgPromptUi);

    if (prompts.length === 1) {
      busy("img_result", `${modelLabel} is generating… (${selectedRes})`, imgAspect() || "1:1");
      try {
        const res = await fetch("/api/image-studio/generate", { method: "POST", headers: apiHeaders(), body: fd });
        if (!res.ok) throw new Error(await readErrorDetail(res, "Image generation failed"));
        const data = await res.json();
        showImage(data.image_url, data);
        revealRendered($("img_result").querySelector("img"));
        loadImageHistory();
        notify(`Image ready (${data.resolution || selectedRes}).`, "success");
      } catch (err) {
        failed("img_result", err.message);
      } finally {
        setBusy($("img_submit"), false, syncImgPromptUi);
      }
      return;
    }

    // Multiple prompts: display result grid
    showResult("img_result", `<div class="result-grid">${prompts.map((p, i) => `
      <div class="result-tile">
        <div class="tile-label" title="${esc(p)}">Prompt ${i + 1} · ${esc(p.slice(0, 60))}</div>
        <div id="img_tile_${i}"></div>
      </div>`).join("")}</div>`);
    prompts.forEach((_, i) => renderLoader(`img_tile_${i}`, `${modelLabel} is generating…`, { ratio: imgAspect() || "1:1" }));

    try {
      const res = await fetch("/api/image-studio/generate", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Image generation failed"));
      const data = await res.json();
      const results = data.images || (data.image_url ? [{ image_url: data.image_url, prompt: prompts[0], status: "success" }] : []);

      let ok = 0;
      prompts.forEach((p, i) => {
        const item = results[i] || results.find((r) => r.prompt === p);
        const tileEl = $(`img_tile_${i}`);
        if (!tileEl) return;
        if (item && item.image_url && item.status !== "failed") {
          ok++;
          tileEl.innerHTML = `
            <img src="${esc(item.image_url)}" alt="${esc(p)}" data-prompt="${esc(p)}" data-aspect="${esc(imgAspect() || "1:1")}">
            <div class="tile-bar">
              <span class="badge badge-accent small">${esc(item.resolution || selectedRes)}</span>
              <div style="display:inline-flex; gap:10px; align-items:center;">
                <button type="button" class="btn-link small btn-save-creative" data-type="image" data-url="${esc(item.image_url)}" data-prompt="${esc(p)}" data-aspect="${esc(imgAspect() || "1:1")}" title="Save prompt and image to library"><i class="fa-regular fa-bookmark"></i> Save Prompt</button>
                <a href="${esc(item.image_url)}" download="${esc(item.filename || `image_${i+1}.png`)}" class="btn-link small" target="_blank"><i class="fa-solid fa-download"></i> Save</a>
              </div>
            </div>`;
          revealRendered(tileEl.querySelector("img"));
        } else {
          const errText = item?.error || "Generation failed";
          tileEl.innerHTML = `<div class="media-empty error"><i class="fa-solid fa-triangle-exclamation"></i><span>${esc(errText)}</span></div>`;
        }
      });
      loadImageHistory();
      notify(`${ok} of ${prompts.length} images ready.`, ok === prompts.length ? "success" : "warning");
    } catch (err) {
      failed("img_result", err.message);
    } finally {
      setBusy($("img_submit"), false, syncImgPromptUi);
    }
  });

  // ------------------------------------------------------------ video studio
  const vidRefs = imageDropzone({ zone: "vid_drop", input: "vid_files", thumbs: "vid_thumbs", max: 7 });
  const vidFirst = imageDropzone({ zone: "vid_first_drop", input: "vid_first_file", thumbs: "vid_first_thumbs", max: 1 });
  const vidLast = imageDropzone({ zone: "vid_last_drop", input: "vid_last_file", thumbs: "vid_last_thumbs", max: 1 });
  const vidAspect = segmented("vid_aspect", "ratio");
  const vidResolution = segmented("vid_resolution", "res");
  const vidDuration = segmented("vid_duration", "dur");
  const PROMPT_LABELS = { prompt_images: "Prompt", first_last_frame: "Motion directions / prompt", edit_video: "Edit instructions" };
  const vidMode = segmented("vid_mode", "mode", (mode) => {
    document.querySelectorAll("[data-for-mode]").forEach((el) => { el.hidden = el.dataset.forMode !== mode; });
    $("vid_prompt_label").textContent = PROMPT_LABELS[mode];
  });
  const sessionVideos = [];

  // Extra prompts share the reference images, frames and format; each one is its own render
  function promptBoxes() {
    return Array.from($("vid_prompts").querySelectorAll("[data-prompt]"));
  }

  function syncPromptUi() {
    const boxes = promptBoxes();
    $("vid_prompts").querySelectorAll(".prompt-extra .label").forEach((el, i) => { el.textContent = `Prompt ${i + 2}`; });
    $("vid_add_prompt").hidden = boxes.length >= MAX_PROMPTS;
    const n = boxes.filter((b) => b.value.trim()).length || 1;
    $("vid_submit").innerHTML = `<i class="fa-solid fa-clapperboard"></i> Generate ${n > 1 ? `${n} videos` : "video"} ${submitKey}`;
  }

  $("vid_add_prompt").addEventListener("click", () => {
    if (promptBoxes().length >= MAX_PROMPTS) return;
    const wrap = document.createElement("div");
    wrap.className = "prompt-extra";
    wrap.innerHTML = `
      <div class="prompt-extra-head">
        <span class="label"></span>
        <button type="button" class="btn-link" data-remove-prompt>Remove</button>
      </div>
      <textarea class="textarea" data-prompt rows="4" placeholder="Another prompt, rendered as its own video"></textarea>`;
    $("vid_prompts").appendChild(wrap);
    syncPromptUi();
    wrap.querySelector("textarea").focus();
  });

  $("vid_prompts").addEventListener("click", (e) => {
    const rm = e.target.closest("[data-remove-prompt]");
    if (!rm) return;
    rm.closest(".prompt-extra").remove();
    syncPromptUi();
  });
  $("vid_prompts").addEventListener("input", syncPromptUi);

  wireMarkdownDrop({
    containerId: "vid_prompts",
    getBoxes: promptBoxes,
    addBtnId: "vid_add_prompt",
    onUpdate: syncPromptUi,
    onImageDrop: (imgs) => vidRefs.add(imgs),
  });

  function rememberVideo(url, job) {
    const res = (job?.resolution || vidResolution() || "1080p").toUpperCase();
    sessionVideos.unshift({ url, resolution: res, width: job?.width, height: job?.height });
    $("vid_history").innerHTML = sessionVideos.map((item) =>
      `<button type="button" data-url="${esc(item.url)}" aria-label="Open this video">
        <video src="${esc(item.url)}" muted preload="metadata"></video>
        ${item.resolution ? `<span class="vid-hist-badge">${esc(item.resolution)}</span>` : ""}
      </button>`
    ).join("");
  }

  function tileState(i, html) {
    const el = $(`vid_tile_${i}`);
    if (el) el.innerHTML = html;
  }

  function showVideo(url, job) {
    const item = sessionVideos.find((v) => v.url === url);
    const res = (job?.resolution || item?.resolution || vidResolution() || "1080p").toUpperCase();
    const w = job?.width || item?.width;
    const h = job?.height || item?.height;
    showResult("vid_result", `<figure class="result-card">
      <video src="${esc(url)}" controls autoplay playsinline></video>
      <figcaption class="result-bar">
        <span class="badge badge-accent">${esc(res)}</span>
        ${w && h ? `<span class="muted small num">${esc(`${w}×${h}`)}</span>` : ""}
        <a href="${esc(url)}" download="omni_video_${esc(res.toLowerCase())}.mp4" class="btn btn-sm"><i class="fa-solid fa-download"></i> Download</a>
        <button type="button" class="btn btn-sm btn-ghost" data-dismiss-result><i class="fa-solid fa-xmark"></i> Close</button>
      </figcaption>
    </figure>`);
  }

  $("vid_form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const mode = vidMode() || "prompt_images";
    const prompts = promptBoxes().map((b) => b.value.trim()).filter(Boolean);
    if (!prompts.length) return notify("Write a prompt first.", "warning");
    if (mode === "first_last_frame" && !vidFirst.files()[0]) {
      return notify("Add at least a start frame.", "warning");
    }
    if (mode === "edit_video" && !$("vid_source").files[0]) return notify("Choose a clip to edit.", "warning");
    if (!requireKey()) return;
    if (prompts.length > 1 && !(await askConfirm(
      `Generate ${prompts.length} videos?`, "Each prompt is a separate Omni Flash render.", `Generate ${prompts.length}`,
      { skipKey: "multi_video" },
    ))) return;

    const fd = new FormData();
    fd.append("mode", mode);
    fd.append("prompts", JSON.stringify(prompts));
    fd.append("aspect_ratio", vidAspect() || "9:16");
    fd.append("duration", vidDuration() || "8");
    fd.append("resolution", vidResolution() || "1080p");
    if (mode === "prompt_images") vidRefs.files().forEach((f) => fd.append("reference_images", f));
    if (mode === "first_last_frame") {
      if (vidFirst.files()[0]) fd.append("first_frame", vidFirst.files()[0]);
      if (vidLast.files()[0]) fd.append("last_frame", vidLast.files()[0]);
    }
    if (mode === "edit_video") fd.append("source_video", $("vid_source").files[0]);

    const vidFolderId = $("vid_folder_id") ? $("vid_folder_id").value : "";
    if (vidFolderId) fd.append("folder_id", vidFolderId);

    setBusy($("vid_submit"), true, syncPromptUi);
    busy("vid_result", prompts.length > 1 ? `Sending ${prompts.length} prompts to Omni Flash…` : "Sending to Omni Flash…", vidAspect() || "9:16");
    try {
      // One request uploads the shared images once and starts every prompt in parallel
      const res = await fetch("/api/studio/generate-video", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Could not start the video"));
      const data = await res.json();
      const jobIds = data.job_ids || [data.job_id];

      if (jobIds.length === 1) {
        busy("vid_result", "Omni Flash is rendering… usually a few minutes", vidAspect() || "9:16");
        const job = await pollJob(jobIds[0], { onProgress: (j) => j.progress_msg && busy("vid_result", j.progress_msg, vidAspect() || "9:16") });
        showVideo(job.video_url, job);
        revealRendered($("vid_result").querySelector("video"));
        rememberVideo(job.video_url, job);
        notify("Video ready.", "success");
        return;
      }

      const ratio = vidAspect() || "9:16";
      const loading = (i, text) => renderLoader(`vid_tile_${i}`, text, { ratio });
      showResult("vid_result", `<div class="result-grid">${jobIds.map((_, i) => `
        <div class="result-tile">
          <div class="tile-label" title="${esc(prompts[i])}">Prompt ${i + 1} · ${esc(prompts[i].slice(0, 60))}</div>
          <div id="vid_tile_${i}"></div>
        </div>`).join("")}</div>`);
      jobIds.forEach((_, i) => loading(i, "Rendering… usually a few minutes"));

      const results = await Promise.allSettled(jobIds.map((id, i) =>
        pollJob(id, { onProgress: (j) => j.progress_msg && loading(i, j.progress_msg) })
          .then((job) => {
            const rBadge = (job.resolution || vidResolution() || "1080p").toUpperCase();
            tileState(i, `<video src="${esc(job.video_url)}" controls playsinline data-prompt="${esc(prompts[i])}" data-aspect="${esc(ratio)}"></video>
              <div class="tile-meta" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                <span class="badge badge-accent">${esc(rBadge)}</span>
                <div style="display:inline-flex; gap:10px; align-items:center;">
                  <button type="button" class="btn-link small btn-save-creative" data-type="video" data-url="${esc(job.video_url)}" data-prompt="${esc(prompts[i])}" data-aspect="${esc(ratio)}" title="Save prompt and video to library"><i class="fa-regular fa-bookmark"></i> Save Prompt</button>
                  <a href="${esc(job.video_url)}" download="video_${i+1}_${rBadge.toLowerCase()}.mp4" class="btn-link small" title="Download video"><i class="fa-solid fa-download"></i> Download</a>
                </div>
              </div>`);
            revealRendered($(`vid_tile_${i}`).querySelector("video"));
            rememberVideo(job.video_url, job);
          })
          .catch((err) => {
            tileState(i, `<div class="media-empty error"><i class="fa-solid fa-triangle-exclamation"></i><span>${esc(err.message)}</span></div>`);
            throw err;
          })
      ));
      const ok = results.filter((r) => r.status === "fulfilled").length;
      notify(`${ok} of ${jobIds.length} videos ready.`, ok === jobIds.length ? "success" : "warning");
    } catch (err) {
      failed("vid_result", err.message);
    } finally {
      setBusy($("vid_submit"), false, syncPromptUi);
    }
  });

  // The style pill keeps its choice in a hidden field, read when the form is sent
  segmented("img_style_group", "style", (style) => { $("img_style").value = style; });

  syncImgPromptUi();
  syncPromptUi();

  // Result actions: close it and return to the gallery, or run the same request again after a failure
  document.querySelectorAll(".stage-current").forEach((stage) => {
    stage.addEventListener("click", (e) => {
      if (e.target.closest("[data-dismiss-result]")) {
        const video = stage.id === "vid_result";
        showResult(stage.id, `<div class="media-empty"><i class="${video ? "fa-solid fa-film" : "fa-regular fa-image"}"></i><span>Your ${video ? "video" : "image"} appears here</span></div>`);
      } else if (e.target.closest("[data-retry]")) {
        $(stage.id === "vid_result" ? "vid_form" : "img_form").requestSubmit();
      }
    });
  });

  // =========================================================================
  // Industry Preset Templates (Pinterest Reference Creative Studio)
  // =========================================================================
  let allIndustryTemplates = [];
  let activeTemplate = null;
  let tplProductFile = null;
  let tplLogoFile = null;

  async function loadIndustryTemplates() {
    try {
      const res = await fetch("/api/campaign/preset-templates");
      if (!res.ok) return;
      const data = await res.json();
      allIndustryTemplates = data.templates || [];
      renderTemplatePillList();
      populateTemplateModalSelect();
      if (allIndustryTemplates.length > 0) {
        setModalTemplate(allIndustryTemplates[0].id);
      }
    } catch (err) {
      console.warn("Could not load preset templates:", err);
    }
  }

  function renderTemplatePillList() {
    const listEl = $("img_preset_template_list");
    if (!listEl) return;
    listEl.innerHTML = `
      <button type="button" class="btn btn-sm btn-primary w-full" id="btn_open_full_template_modal" style="margin-bottom: 6px; justify-content:center;">
        <i class="fa-solid fa-wand-magic-sparkles"></i> Open Template Studio
      </button>
      <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.04em; color:var(--ink-3); padding:4px 8px;">Popular Styles</div>
      ${allIndustryTemplates.map((t) => `
        <button type="button" class="template-item-btn" data-pick-template="${esc(t.id)}">
          <span class="tpl-btn-name">${esc(t.name)}</span>
          <span class="tpl-btn-sub">${esc(t.industry_label)}</span>
        </button>
      `).join("")}
    `;

    $("btn_open_full_template_modal")?.addEventListener("click", () => {
      openIndustryTemplateModal(activeTemplate?.id || "beauty_editorial_rhode");
    });

    listEl.querySelectorAll("[data-pick-template]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tid = btn.dataset.pickTemplate;
        openIndustryTemplateModal(tid);
      });
    });
  }

  function populateTemplateModalSelect() {
    const sel = $("tpl_preset_picker");
    if (!sel) return;
    sel.innerHTML = allIndustryTemplates.map((t) => `
      <option value="${esc(t.id)}">${esc(t.industry_label)} — ${esc(t.name)}</option>
    `).join("");

    sel.addEventListener("change", () => {
      setModalTemplate(sel.value);
    });
  }

  function setModalTemplate(templateId) {
    const t = allIndustryTemplates.find((x) => x.id === templateId) || allIndustryTemplates[0];
    if (!t) return;
    activeTemplate = t;

    // Update Header
    if ($("tpl_modal_preset_name")) $("tpl_modal_preset_name").textContent = t.name;
    if ($("tpl_modal_industry_badge")) $("tpl_modal_industry_badge").textContent = t.industry_label;
    if ($("tpl_modal_movement")) $("tpl_modal_movement").textContent = t.movement;
    if ($("tpl_preset_picker") && $("tpl_preset_picker").value !== t.id) {
      $("tpl_preset_picker").value = t.id;
    }

    // Prefill form defaults
    const defs = t.template_defaults || {};
    if ($("tpl_brand_name")) $("tpl_brand_name").value = defs.brand_name || "";
    if ($("tpl_product_name")) $("tpl_product_name").value = defs.product_name || "";
    if ($("tpl_idea")) $("tpl_idea").value = defs.idea || "";
    if ($("tpl_headline")) $("tpl_headline").value = defs.headline || "";
    if ($("tpl_cta")) $("tpl_cta").value = defs.cta || "Shop Now";
    if ($("tpl_aspect_ratio")) $("tpl_aspect_ratio").value = defs.aspect_ratio || "4:5";

    // Reference Pins
    const pinsEl = $("tpl_pins_strip");
    if (pinsEl) {
      const pins = t.reference_pins || [];
      pinsEl.innerHTML = pins.map((p) => `
        <a class="template-pin-card" href="${esc(p.pin_url || p.image_url)}" target="_blank" rel="noopener" title="${esc(p.title || 'Pinterest Pin')}">
          <img src="${esc(p.image_url)}" alt="${esc(p.title || 'Reference')}" loading="lazy">
          <div class="template-pin-badge"><i class="fa-brands fa-pinterest"></i> Reference</div>
        </a>
      `).join("");
    }

    // Palette Dots
    const dotsEl = $("tpl_palette_dots");
    if (dotsEl) {
      const palette = t.colors?.palette || [t.colors?.background_tone, t.colors?.secondary_accent, t.colors?.primary_accent].filter(Boolean);
      dotsEl.innerHTML = palette.map((c) => `<span class="template-dot" style="background:${esc(c)}" title="${esc(c)}"></span>`).join("");
    }

    // Typography Tags
    const typoEl = $("tpl_typo_tags");
    if (typoEl) {
      const fonts = (t.typography?.recommended_headline_fonts || []).slice(0, 3);
      typoEl.innerHTML = fonts.map((f) => `<span class="badge small"><i class="fa-solid fa-font"></i> ${esc(f)}</span>`).join("");
    }

    updateCompiledPromptPreview();
  }

  function getModalFormData() {
    return {
      preset_id: activeTemplate?.id || "beauty_editorial_rhode",
      brand_name: $("tpl_brand_name")?.value.trim() || "",
      product_name: $("tpl_product_name")?.value.trim() || "",
      idea: $("tpl_idea")?.value.trim() || "",
      headline: $("tpl_headline")?.value.trim() || "",
      cta: $("tpl_cta")?.value.trim() || "Shop Now",
      aspect_ratio: $("tpl_aspect_ratio")?.value || "4:5",
      has_product_ref: !!tplProductFile,
      has_logo: !!tplLogoFile,
    };
  }

  let promptDebounceTimer = null;
  function updateCompiledPromptPreview() {
    clearTimeout(promptDebounceTimer);
    promptDebounceTimer = setTimeout(async () => {
      const fd = getModalFormData();
      try {
        const body = new FormData();
        Object.entries(fd).forEach(([k, v]) => body.append(k, String(v)));
        const res = await fetch("/api/campaign/presets/render-template", {
          method: "POST",
          headers: apiHeaders(),
          body,
        });
        if (res.ok) {
          const data = await res.json();
          if ($("tpl_prompt_preview")) {
            $("tpl_prompt_preview").textContent = data.rendered_prompt;
          }
        }
      } catch (err) {
        console.warn("Could not recompile preview:", err);
      }
    }, 150);
  }

  function openIndustryTemplateModal(presetId) {
    if (typeof showView === "function") {
      showView("image", { push: true });
    }
    const modal = $("industry_template_modal");
    if (!modal) return;
    if (presetId) {
      setModalTemplate(presetId);
    }
    if (typeof modal.showModal === "function") {
      modal.showModal();
    } else {
      modal.setAttribute("open", "");
    }
  }
  window.openIndustryTemplateModal = openIndustryTemplateModal;

  function closeIndustryTemplateModal() {
    const modal = $("industry_template_modal");
    if (!modal) return;
    if (typeof modal.close === "function") {
      modal.close();
    } else {
      modal.removeAttribute("open");
    }
  }

  // Hook input events on modal form fields
  ["tpl_brand_name", "tpl_product_name", "tpl_idea", "tpl_headline", "tpl_cta", "tpl_aspect_ratio"].forEach((id) => {
    $(id)?.addEventListener("input", updateCompiledPromptPreview);
    $(id)?.addEventListener("change", updateCompiledPromptPreview);
  });

  // Modal Buttons
  $("btn_close_industry_template")?.addEventListener("click", closeIndustryTemplateModal);
  $("btn_cancel_template")?.addEventListener("click", closeIndustryTemplateModal);

  // Copy prompt button
  $("btn_copy_tpl_prompt")?.addEventListener("click", async () => {
    const txt = $("tpl_prompt_preview")?.textContent || "";
    if (!txt) return;
    try {
      await navigator.clipboard.writeText(txt);
      notify("Prompt copied to clipboard!", "success");
    } catch {
      notify("Could not copy to clipboard.", "error");
    }
  });

  // Wire product & logo dropzones inside modal
  function wireModalDropzone(zoneId, inputId, previewId, imgId, rmBtnId, onFile) {
    const zone = $(zoneId);
    const input = $(inputId);
    const prev = $(previewId);
    const img = $(imgId);
    const rm = $(rmBtnId);
    if (!zone || !input) return;

    zone.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      input.click();
    });

    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
      const f = Array.from(e.dataTransfer?.files || []).find((x) => x.type.startsWith("image/"));
      if (f) handleFile(f);
    });

    input.addEventListener("change", () => {
      if (input.files && input.files[0]) handleFile(input.files[0]);
    });

    function handleFile(file) {
      onFile(file);
      if (img && prev) {
        img.src = URL.createObjectURL(file);
        prev.hidden = false;
      }
      updateCompiledPromptPreview();
    }

    rm?.addEventListener("click", (e) => {
      e.stopPropagation();
      onFile(null);
      if (input) input.value = "";
      if (prev) prev.hidden = true;
      if (img) img.src = "";
      updateCompiledPromptPreview();
    });
  }

  wireModalDropzone("tpl_product_dropzone", "tpl_product_file", "tpl_product_preview", "tpl_product_preview_img", "btn_remove_tpl_product", (f) => {
    tplProductFile = f;
  });

  wireModalDropzone("tpl_logo_dropzone", "tpl_logo_file", "tpl_logo_preview", "tpl_logo_preview_img", "btn_remove_tpl_logo", (f) => {
    tplLogoFile = f;
  });

  function applyTemplateToStudio() {
    const promptText = $("tpl_prompt_preview")?.textContent.trim();
    if (!promptText) {
      notify("Template prompt is empty.", "warning");
      return false;
    }

    // Set prompt box
    const primaryBox = imgPromptBoxes()[0];
    if (primaryBox) {
      primaryBox.value = promptText;
      primaryBox.dispatchEvent(new Event("input", { bubbles: true }));
      primaryBox.dispatchEvent(new Event("change", { bubbles: true }));
    }

    // Set aspect ratio
    const ratio = $("tpl_aspect_ratio")?.value || "4:5";
    const ratioBtn = $("img_aspect")?.querySelector(`button[data-ratio="${ratio}"]`);
    if (ratioBtn) {
      ratioBtn.click();
    }

    // Set resolution if selected
    const res = $("tpl_resolution")?.value || "1K";
    const resBtn = $("img_resolution")?.querySelector(`button[data-res="${res}"]`);
    if (resBtn) {
      resBtn.click();
    }

    // Transfer uploaded files to studio references
    const toAdd = [tplProductFile, tplLogoFile].filter(Boolean);
    if (toAdd.length && imgRefs) {
      imgRefs.add(toAdd);
    }

    // Update template label in composer bar
    if (activeTemplate && $("img_template_label")) {
      $("img_template_label").textContent = activeTemplate.name.split(" ")[0];
    }

    closeIndustryTemplateModal();
    return true;
  }

  $("btn_load_into_studio")?.addEventListener("click", () => {
    if (applyTemplateToStudio()) {
      notify(`Loaded "${activeTemplate?.name || 'Industry'}" template into Studio!`, "success");
    }
  });

  $("btn_generate_from_template")?.addEventListener("click", () => {
    if (applyTemplateToStudio()) {
      notify(`Generating ad with "${activeTemplate?.name || 'Industry'}" template…`, "info");
      setTimeout(() => {
        $("img_form").requestSubmit();
      }, 50);
    }
  });

  loadIndustryTemplates();

  window.addEventListener("viewchange", (e) => { if (e.detail === "image") loadImageHistory(); });
})();
