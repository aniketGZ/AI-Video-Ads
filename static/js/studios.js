// Image studio (Nano Banana Pro) and video studio (Omni Flash): one-off generations outside the campaign flow.
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = escapeHtml;

  function showResult(container, html) {
    $(container).innerHTML = html;
  }

  function busy(container, text) {
    showResult(container, `<div class="media-empty"><span class="spinner"></span><span>${esc(text)}</span></div>`);
  }

  function failed(container, text) {
    showResult(container, `<div class="media-empty error"><i class="fa-solid fa-triangle-exclamation"></i><span>${esc(text)}</span></div>`);
  }

  const MAX_PROMPTS = 5;

  // ------------------------------------------------------------ markdown file drop helper
  function wireMarkdownDrop({ containerId, getBoxes, addBtnId, onUpdate }) {
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

      const mdFiles = files.filter(isMdFile);
      if (!mdFiles.length) {
        if (files.some((f) => f.type.startsWith("image/"))) {
          notify("Drop reference images into the Reference Images box below.", "info");
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
    let metaHtml = "";
    if (meta && (meta.resolution || meta.aspect_ratio || meta.width)) {
      const dim = meta.width && meta.height ? `${meta.width}×${meta.height}` : "";
      metaHtml = `<div class="image-meta-bar" style="margin-top: 10px; display: flex; gap: 8px; align-items: center; justify-content: center; font-size: 0.82rem; color: var(--text-2);">
        ${meta.resolution ? `<span class="badge badge-accent">${esc(meta.resolution)}</span>` : ""}
        ${meta.aspect_ratio ? `<span class="badge">${esc(meta.aspect_ratio)}</span>` : ""}
        ${dim ? `<span class="muted small">${esc(dim)}</span>` : ""}
      </div>`;
    }
    showResult("img_result", `<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%;"><img src="${esc(url)}" alt="Generated image ad">${metaHtml}</div>`);
  }

  function imgPromptBoxes() {
    return Array.from($("img_prompts").querySelectorAll("[data-prompt]"));
  }

  function syncImgPromptUi() {
    const boxes = imgPromptBoxes();
    $("img_prompts").querySelectorAll(".prompt-extra .label").forEach((el, i) => { el.textContent = `Prompt ${i + 2}`; });
    $("img_add_prompt").hidden = boxes.length >= MAX_PROMPTS;
    const n = boxes.filter((b) => b.value.trim()).length || 1;
    $("img_submit").innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Generate ${n > 1 ? `${n} images` : "image"}`;
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
  });

  async function loadImageHistory() {
    try {
      const res = await fetch("/api/image-studio/history");
      if (!res.ok) return;
      const { images } = await res.json();
      $("img_history").innerHTML = (images || []).map((i) =>
        `<button type="button" data-url="${esc(i.url)}" aria-label="Show this image"><img src="${esc(i.url)}" alt="" loading="lazy"></button>`
      ).join("") || '<span class="muted small">Nothing yet</span>';
    } catch (e) { /* history is optional */ }
  }

  $("img_history").addEventListener("click", (e) => {
    const b = e.target.closest("[data-url]");
    if (b) showImage(b.dataset.url);
  });

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
      `Generate ${prompts.length}`
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

    $("img_submit").disabled = true;

    if (prompts.length === 1) {
      busy("img_result", `${modelLabel} is generating… (${selectedRes})`);
      try {
        const res = await fetch("/api/image-studio/generate", { method: "POST", headers: apiHeaders(), body: fd });
        if (!res.ok) throw new Error(await readErrorDetail(res, "Image generation failed"));
        const data = await res.json();
        showImage(data.image_url, data);
        loadImageHistory();
        notify(`Image ready (${data.resolution || selectedRes}).`, "success");
      } catch (err) {
        failed("img_result", err.message);
      } finally {
        $("img_submit").disabled = false;
      }
      return;
    }

    // Multiple prompts: display result grid
    const spinner = (text) => `<div class="media-empty"><span class="spinner"></span><span>${esc(text)}</span></div>`;
    showResult("img_result", `<div class="result-grid">${prompts.map((p, i) => `
      <div class="result-tile">
        <div class="tile-label" title="${esc(p)}">Prompt ${i + 1} · ${esc(p.slice(0, 60))}</div>
        <div id="img_tile_${i}">${spinner(`${modelLabel} is generating…`)}</div>
      </div>`).join("")}</div>`);

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
            <img src="${esc(item.image_url)}" alt="${esc(p)}" style="cursor:pointer;" title="Click to view full size">
            <div class="tile-bar">
              <span class="badge badge-accent small">${esc(item.resolution || selectedRes)}</span>
              <button type="button" class="btn-link small" data-view-img><i class="fa-solid fa-expand"></i> View</button>
              <a href="${esc(item.image_url)}" download="${esc(item.filename || `image_${i+1}.png`)}" class="btn-link small" target="_blank"><i class="fa-solid fa-download"></i> Save</a>
            </div>`;
          tileEl.querySelector("img").addEventListener("click", () => showImage(item.image_url, item));
          const viewBtn = tileEl.querySelector("[data-view-img]");
          if (viewBtn) viewBtn.addEventListener("click", () => showImage(item.image_url, item));
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
      $("img_submit").disabled = false;
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
    $("vid_submit").innerHTML = `<i class="fa-solid fa-clapperboard"></i> Generate ${n > 1 ? `${n} videos` : "video"}`;
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
  });

  function rememberVideo(url, job) {
    const res = (job?.resolution || vidResolution() || "1080p").toUpperCase();
    sessionVideos.unshift({ url, resolution: res, width: job?.width, height: job?.height });
    $("vid_history").innerHTML = sessionVideos.map((item) =>
      `<button type="button" data-url="${esc(item.url)}" aria-label="Show this video">
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
    const dim = (job?.width && job?.height) ? `${job.width}×${job.height} · ` : (item?.width && item?.height ? `${item.width}×${item.height} · ` : "");
    const dlFilename = `omni_video_${res.toLowerCase()}.mp4`;
    const toolbar = `
      <div class="vid-meta-pill" style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
        <span class="badge badge-accent">${esc(res)}</span>
        ${dim ? `<span class="muted small">${esc(dim)}</span>` : ""}
        <a href="${esc(url)}" download="${esc(dlFilename)}" class="btn btn-sm btn-ghost" style="padding: 3px 10px; font-size: 0.76rem; border: 1px solid var(--border);" title="Download full resolution video">
          <i class="fa-solid fa-download"></i> Download ${esc(res)}
        </a>
      </div>`;
    showResult("vid_result", `<div class="vid-preview-box">${toolbar}<video src="${esc(url)}" controls autoplay playsinline></video></div>`);
  }

  $("vid_history").addEventListener("click", (e) => {
    const b = e.target.closest("[data-url]");
    if (b) showVideo(b.dataset.url);
  });

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

    $("vid_submit").disabled = true;
    busy("vid_result", prompts.length > 1 ? `Sending ${prompts.length} prompts to Omni Flash…` : "Sending to Omni Flash…");
    try {
      // One request uploads the shared images once and starts every prompt in parallel
      const res = await fetch("/api/studio/generate-video", { method: "POST", headers: apiHeaders(), body: fd });
      if (!res.ok) throw new Error(await readErrorDetail(res, "Could not start the video"));
      const data = await res.json();
      const jobIds = data.job_ids || [data.job_id];

      if (jobIds.length === 1) {
        busy("vid_result", "Omni Flash is rendering… usually a few minutes");
        const job = await pollJob(jobIds[0], { onProgress: (j) => j.progress_msg && busy("vid_result", j.progress_msg) });
        showVideo(job.video_url, job);
        rememberVideo(job.video_url, job);
        notify("Video ready.", "success");
        return;
      }

      const spinner = (text) => `<div class="media-empty"><span class="spinner"></span><span>${esc(text)}</span></div>`;
      showResult("vid_result", `<div class="result-grid">${jobIds.map((_, i) => `
        <div class="result-tile">
          <div class="tile-label" title="${esc(prompts[i])}">Prompt ${i + 1} · ${esc(prompts[i].slice(0, 60))}</div>
          <div id="vid_tile_${i}">${spinner("Rendering… usually a few minutes")}</div>
        </div>`).join("")}</div>`);

      const results = await Promise.allSettled(jobIds.map((id, i) =>
        pollJob(id, { onProgress: (j) => j.progress_msg && tileState(i, spinner(j.progress_msg)) })
          .then((job) => {
            const rBadge = (job.resolution || vidResolution() || "1080p").toUpperCase();
            tileState(i, `<video src="${esc(job.video_url)}" controls playsinline></video>
              <div class="tile-meta" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                <span class="badge badge-accent">${esc(rBadge)}</span>
                <a href="${esc(job.video_url)}" download="video_${i+1}_${rBadge.toLowerCase()}.mp4" class="btn-link small" title="Download video"><i class="fa-solid fa-download"></i> Save</a>
              </div>`);
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
      $("vid_submit").disabled = false;
    }
  });

  window.addEventListener("viewchange", (e) => { if (e.detail === "image") loadImageHistory(); });
})();
