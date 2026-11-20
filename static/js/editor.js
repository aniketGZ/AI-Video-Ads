// Creative Studio Editor: Interactive Inpainting (Brush Mask + Prompt) & 1-Click Background Removal
(function () {
  "use strict";

  const modal = document.getElementById("creative_editor_modal");
  if (!modal) return;

  const stageImg = document.getElementById("editor_stage_img");
  const canvas = document.getElementById("editor_mask_canvas");
  const ctx = canvas ? canvas.getContext("2d") : null;
  const cursorRing = document.getElementById("editor_brush_cursor");
  const loader = document.getElementById("editor_loader");
  const loaderText = document.getElementById("editor_loader_text");

  // Header & Status
  const dimBadge = document.getElementById("editor_dim_badge");
  const btnClose = document.getElementById("btn_close_editor");
  const btnCompare = document.getElementById("btn_editor_compare");

  // HUD
  const brushSlider = document.getElementById("editor_brush_slider");
  const brushVal = document.getElementById("editor_brush_size_val");
  const btnUndo = document.getElementById("btn_editor_undo");
  const btnClearMask = document.getElementById("btn_editor_clear_mask");
  const modeIndicator = document.getElementById("editor_mode_indicator");
  const hudBrushControls = document.getElementById("hud_brush_controls");

  // Tabs
  const tabInpaint = document.getElementById("tab_tool_inpaint");
  const tabRemoveBg = document.getElementById("tab_tool_remove_bg");
  const panelInpaint = document.getElementById("panel_tool_inpaint");
  const panelRemoveBg = document.getElementById("panel_tool_remove_bg");

  // Inpaint Inputs
  const inpaintPrompt = document.getElementById("editor_inpaint_prompt");
  const inpaintModel = document.getElementById("editor_inpaint_model");
  const btnApplyInpaint = document.getElementById("btn_apply_inpaint");

  // Remove BG Inputs
  const removeBgModel = document.getElementById("editor_removebg_model");
  const btnApplyRemoveBg = document.getElementById("btn_apply_remove_bg");

  // Footer Actions
  const btnUseAsBase = document.getElementById("btn_editor_use_as_base");
  const btnSaveLib = document.getElementById("btn_editor_save_lib");
  const btnDownload = document.getElementById("btn_editor_download");

  // State
  let originalUrl = "";
  let currentUrl = "";
  let currentFilename = "edited_creative.png";
  let activeTab = "inpaint"; // 'inpaint' | 'remove_bg'
  let brushRadius = 28;
  let isDrawing = false;
  let strokes = []; // Array of { radius, points: [{x, y}] }
  let currentStroke = null;
  let historyStack = []; // URLs of sequential edits

  // -------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------
  function setBusy(busy, message = "Gemini AI is processing your creative...") {
    if (!loader) return;
    if (busy) {
      if (loaderText) loaderText.textContent = message;
      loader.hidden = false;
      if (btnApplyInpaint) btnApplyInpaint.disabled = true;
      if (btnApplyRemoveBg) btnApplyRemoveBg.disabled = true;
    } else {
      loader.hidden = true;
      if (btnApplyInpaint) btnApplyInpaint.disabled = false;
      if (btnApplyRemoveBg) btnApplyRemoveBg.disabled = false;
    }
  }

  function redrawAllStrokes() {
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (const stroke of strokes) {
      if (!stroke.points || stroke.points.length === 0) continue;
      ctx.lineWidth = stroke.radius * 2;
      ctx.strokeStyle = "rgba(239, 68, 68, 0.55)";
      ctx.fillStyle = "rgba(239, 68, 68, 0.55)";

      if (stroke.points.length === 1) {
        ctx.beginPath();
        ctx.arc(stroke.points[0].x, stroke.points[0].y, stroke.radius, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
        for (let i = 1; i < stroke.points.length; i++) {
          ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
        }
        ctx.stroke();
      }
    }
  }

  function getCanvasCoords(e) {
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }

  function updateBrushCursor(e) {
    if (!cursorRing || !canvas) return;
    const rect = canvas.getBoundingClientRect();
    const inBounds =
      e.clientX >= rect.left &&
      e.clientX <= rect.right &&
      e.clientY >= rect.top &&
      e.clientY <= rect.bottom;

    if (!inBounds || activeTab !== "inpaint") {
      cursorRing.hidden = true;
      return;
    }

    cursorRing.hidden = false;
    const screenRadius = brushRadius * (rect.width / canvas.width);
    const size = Math.max(8, screenRadius * 2);
    cursorRing.style.width = `${size}px`;
    cursorRing.style.height = `${size}px`;
    cursorRing.style.left = `${e.clientX}px`;
    cursorRing.style.top = `${e.clientY}px`;
  }

  // Generate binary black-and-white mask base64 string
  function getBinaryMaskData() {
    if (!canvas || strokes.length === 0) return "";
    const offscreen = document.createElement("canvas");
    offscreen.width = canvas.width;
    offscreen.height = canvas.height;
    const octx = offscreen.getContext("2d");
    if (!octx) return "";

    // Fill black
    octx.fillStyle = "#000000";
    octx.fillRect(0, 0, offscreen.width, offscreen.height);

    // Draw white strokes
    octx.lineCap = "round";
    octx.lineJoin = "round";
    octx.strokeStyle = "#FFFFFF";
    octx.fillStyle = "#FFFFFF";

    for (const stroke of strokes) {
      if (!stroke.points || stroke.points.length === 0) continue;
      octx.lineWidth = stroke.radius * 2;
      if (stroke.points.length === 1) {
        octx.beginPath();
        octx.arc(stroke.points[0].x, stroke.points[0].y, stroke.radius, 0, Math.PI * 2);
        octx.fill();
      } else {
        octx.beginPath();
        octx.moveTo(stroke.points[0].x, stroke.points[0].y);
        for (let i = 1; i < stroke.points.length; i++) {
          octx.lineTo(stroke.points[i].x, stroke.points[i].y);
        }
        octx.stroke();
      }
    }

    return offscreen.toDataURL("image/png");
  }

  // -------------------------------------------------------------
  // Pointer Event Listeners for Mask Drawing
  // -------------------------------------------------------------
  if (canvas) {
    canvas.addEventListener("pointerdown", (e) => {
      if (activeTab !== "inpaint") return;
      canvas.setPointerCapture(e.pointerId);
      isDrawing = true;
      const coords = getCanvasCoords(e);
      currentStroke = {
        radius: brushRadius,
        points: [coords],
      };
      strokes.push(currentStroke);
      redrawAllStrokes();
      updateBrushCursor(e);
    });

    canvas.addEventListener("pointermove", (e) => {
      updateBrushCursor(e);
      if (!isDrawing || !currentStroke || activeTab !== "inpaint") return;
      const coords = getCanvasCoords(e);
      currentStroke.points.push(coords);
      redrawAllStrokes();
    });

    const stopDrawing = (e) => {
      if (!isDrawing) return;
      isDrawing = false;
      currentStroke = null;
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch (_) {}
    };

    canvas.addEventListener("pointerup", stopDrawing);
    canvas.addEventListener("pointercancel", stopDrawing);
    canvas.addEventListener("pointerleave", () => {
      if (cursorRing) cursorRing.hidden = true;
    });
  }

  // Slider Brush Size
  if (brushSlider) {
    brushSlider.addEventListener("input", () => {
      brushRadius = parseInt(brushSlider.value, 10) || 28;
      if (brushVal) brushVal.textContent = `${brushRadius}px`;
    });
  }

  // Undo & Clear
  if (btnUndo) {
    btnUndo.addEventListener("click", () => {
      if (strokes.length > 0) {
        strokes.pop();
        redrawAllStrokes();
      }
    });
  }

  if (btnClearMask) {
    btnClearMask.addEventListener("click", () => {
      strokes = [];
      redrawAllStrokes();
      notify("Mask cleared.", "info");
    });
  }

  // -------------------------------------------------------------
  // Mode Tab Switcher
  // -------------------------------------------------------------
  function switchTab(mode) {
    activeTab = mode;
    if (mode === "inpaint") {
      tabInpaint?.classList.add("active");
      tabInpaint?.setAttribute("aria-selected", "true");
      tabRemoveBg?.classList.remove("active");
      tabRemoveBg?.setAttribute("aria-selected", "false");
      if (panelInpaint) panelInpaint.hidden = false;
      if (panelRemoveBg) panelRemoveBg.hidden = true;
      if (hudBrushControls) hudBrushControls.style.display = "flex";
      if (canvas) canvas.style.pointerEvents = "auto";
      if (modeIndicator) modeIndicator.textContent = "Inpaint Mode";
    } else {
      tabRemoveBg?.classList.add("active");
      tabRemoveBg?.setAttribute("aria-selected", "true");
      tabInpaint?.classList.remove("active");
      tabInpaint?.setAttribute("aria-selected", "false");
      if (panelRemoveBg) panelRemoveBg.hidden = false;
      if (panelInpaint) panelInpaint.hidden = true;
      if (hudBrushControls) hudBrushControls.style.display = "none";
      if (canvas) canvas.style.pointerEvents = "none";
      if (cursorRing) cursorRing.hidden = true;
      if (modeIndicator) modeIndicator.textContent = "Subject Isolation";
    }
  }

  tabInpaint?.addEventListener("click", () => switchTab("inpaint"));
  tabRemoveBg?.addEventListener("click", () => switchTab("remove_bg"));

  // Background Style Card Selection
  document.querySelectorAll(".bg-style-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".bg-style-card").forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
      const radio = card.querySelector('input[type="radio"]');
      if (radio) radio.checked = true;
    });
  });

  // Quick Suggestion Chips
  document.querySelectorAll("[data-inpaint-suggest]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const text = chip.dataset.inpaintSuggest || "";
      if (inpaintPrompt) {
        inpaintPrompt.value = text;
        inpaintPrompt.focus();
      }
    });
  });

  // -------------------------------------------------------------
  // Hold to Compare Feature
  // -------------------------------------------------------------
  if (btnCompare) {
    const showOriginal = () => {
      if (originalUrl && stageImg) {
        stageImg.src = originalUrl;
        if (canvas) canvas.style.opacity = "0.2";
      }
    };
    const showCurrent = () => {
      if (currentUrl && stageImg) {
        stageImg.src = currentUrl;
        if (canvas) canvas.style.opacity = "1";
      }
    };

    btnCompare.addEventListener("pointerdown", showOriginal);
    btnCompare.addEventListener("pointerup", showCurrent);
    btnCompare.addEventListener("pointerleave", showCurrent);
  }

  // -------------------------------------------------------------
  // API Execution: Inpaint
  // -------------------------------------------------------------
  if (btnApplyInpaint) {
    btnApplyInpaint.addEventListener("click", async () => {
      const prompt = inpaintPrompt ? inpaintPrompt.value.trim() : "";
      if (!prompt) {
        notify("Please write instructions describing what to add or modify.", "error");
        if (inpaintPrompt) inpaintPrompt.focus();
        return;
      }

      const maskData = getBinaryMaskData();
      if (!maskData && strokes.length === 0) {
        notify("Please paint over the area you want to modify using the brush.", "warning");
        return;
      }

      setBusy(true, "Gemini Nano Banana is inpainting your marked region...");

      try {
        const formData = new FormData();
        formData.append("image_url", currentUrl);
        formData.append("mask_data", maskData);
        formData.append("prompt", prompt);
        formData.append("model", inpaintModel ? inpaintModel.value : "nano-banana-pro");

        const headers = typeof apiHeaders === "function" ? apiHeaders() : {};
        const res = await fetch("/api/edit/inpaint", {
          method: "POST",
          headers: headers,
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Inpaint failed (HTTP ${res.status})`);
        }

        const data = await res.json();
        if (data.status === "success" && data.image_url) {
          historyStack.push(currentUrl);
          currentUrl = data.image_url;
          currentFilename = data.filename || `edited_${Date.now()}.png`;
          if (stageImg) stageImg.src = currentUrl;

          // Clear mask after successful edit
          strokes = [];
          redrawAllStrokes();

          notify("Inpainting applied successfully!", "success");
          if (btnCompare) btnCompare.hidden = false;

          const studioStageImg = document.querySelector("#img_result img");
          if (studioStageImg) studioStageImg.src = currentUrl;
          window.dispatchEvent(new CustomEvent("studio-image-updated", { detail: { url: currentUrl } }));
        } else {
          throw new Error("No image was returned by the editing engine.");
        }
      } catch (err) {
        notify(err.message, "error");
      } finally {
        setBusy(false);
      }
    });
  }

  // -------------------------------------------------------------
  // API Execution: Remove Background
  // -------------------------------------------------------------
  if (btnApplyRemoveBg) {
    btnApplyRemoveBg.addEventListener("click", async () => {
      const selectedStyleEl = document.querySelector('input[name="bg_style_choice"]:checked');
      const style = selectedStyleEl ? selectedStyleEl.value : "transparent";

      setBusy(true, "Gemini AI is isolating the primary subject...");

      try {
        const formData = new FormData();
        formData.append("image_url", currentUrl);
        formData.append("background_style", style);
        formData.append("model", removeBgModel ? removeBgModel.value : "nano-banana-pro");

        const headers = typeof apiHeaders === "function" ? apiHeaders() : {};
        const res = await fetch("/api/edit/remove-bg", {
          method: "POST",
          headers: headers,
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Background removal failed (HTTP ${res.status})`);
        }

        const data = await res.json();
        if (data.status === "success" && data.image_url) {
          historyStack.push(currentUrl);
          currentUrl = data.image_url;
          currentFilename = data.filename || `bg_removed_${Date.now()}.png`;
          if (stageImg) stageImg.src = currentUrl;

          strokes = [];
          redrawAllStrokes();

          notify("Subject isolated and background updated!", "success");
          if (btnCompare) btnCompare.hidden = false;

          const studioStageImg = document.querySelector("#img_result img");
          if (studioStageImg) studioStageImg.src = currentUrl;
          window.dispatchEvent(new CustomEvent("studio-image-updated", { detail: { url: currentUrl } }));
        } else {
          throw new Error("No image was returned by the editing engine.");
        }
      } catch (err) {
        notify(err.message, "error");
      } finally {
        setBusy(false);
      }
    });
  }

  // -------------------------------------------------------------
  // Footer Action: Chain Edits / Use as Base
  // -------------------------------------------------------------
  if (btnUseAsBase) {
    btnUseAsBase.addEventListener("click", () => {
      strokes = [];
      redrawAllStrokes();
      if (inpaintPrompt) inpaintPrompt.value = "";
      notify("Current visual locked as base. You can now paint and chain further edits.", "success");
    });
  }

  // -------------------------------------------------------------
  // Footer Action: Download
  // -------------------------------------------------------------
  if (btnDownload) {
    btnDownload.addEventListener("click", (e) => {
      e.preventDefault();
      if (!currentUrl) return;
      if (typeof window.downloadMediaFile === "function") {
        window.downloadMediaFile(currentUrl, currentFilename);
      } else {
        const a = document.createElement("a");
        a.href = currentUrl;
        a.download = currentFilename;
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    });
  }

  // -------------------------------------------------------------
  // Footer Action: Save to Library
  // -------------------------------------------------------------
  if (btnSaveLib) {
    btnSaveLib.addEventListener("click", async () => {
      if (!currentUrl) return;
      try {
        const promptUsed = inpaintPrompt ? inpaintPrompt.value.trim() : "Creative Edit";
        const res = await fetch("/api/saved/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: `Edited Creative · ${currentFilename}`,
            media_url: currentUrl,
            prompt: promptUsed || "Edited Creative",
            aspect_ratio: "1:1",
            media_type: "image",
          }),
        });
        if (res.ok) {
          notify("Saved to your Creative Library!", "success");
        } else {
          notify("Failed to save creative to library.", "error");
        }
      } catch (err) {
        notify("Could not save creative to library.", "error");
      }
    });
  }

  // -------------------------------------------------------------
  // Close Editor
  // -------------------------------------------------------------
  function closeEditor() {
    if (modal && modal.open) {
      modal.close();
      strokes = [];
      redrawAllStrokes();
      if (cursorRing) cursorRing.hidden = true;
    }
  }

  btnClose?.addEventListener("click", closeEditor);

  // -------------------------------------------------------------
  // Global Entrypoint: window.openCreativeEditor
  // -------------------------------------------------------------
  window.openCreativeEditor = function (options = {}) {
    const url = typeof options === "string" ? options : options.url;
    if (!url) {
      notify("No image URL provided to edit.", "error");
      return;
    }

    originalUrl = url;
    currentUrl = url;
    currentFilename = options.filename || `edit_${Date.now()}.png`;
    historyStack = [];
    strokes = [];

    if (inpaintPrompt) inpaintPrompt.value = options.prompt || "";
    if (btnCompare) btnCompare.hidden = true;

    // Load Image into stage
    if (stageImg) {
      stageImg.onload = () => {
        if (canvas) {
          canvas.width = stageImg.naturalWidth || 1024;
          canvas.height = stageImg.naturalHeight || 1024;
          redrawAllStrokes();
        }
        if (dimBadge) {
          dimBadge.textContent = `${stageImg.naturalWidth}×${stageImg.naturalHeight}`;
        }
      };
      stageImg.src = url;
    }

    const targetTab = options.tab === "remove_bg" ? "remove_bg" : "inpaint";
    switchTab(targetTab);

    if (modal && !modal.open) {
      modal.showModal();
    }
  };

  // Wire delegated clicks across the page for [data-edit-creative]
  document.addEventListener("click", (e) => {
    const editBtn = e.target.closest("[data-edit-creative], .btn-edit-creative, .btn-studio-inpaint, .btn-studio-removebg");
    if (editBtn) {
      e.preventDefault();
      e.stopPropagation();
      const url = editBtn.dataset.editCreative || editBtn.dataset.url;
      const tab = editBtn.dataset.tab || (editBtn.classList.contains("btn-studio-removebg") ? "remove_bg" : "inpaint");
      if (url) {
        window.openCreativeEditor({ url, tab });
      }
    }
  });
})();
