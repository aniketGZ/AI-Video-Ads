// Saved Creatives, Project Folders, Creator Profile & Pinterest Ad Templates
// Connects to /api/projects, /api/saved/*, /api/user/profile, and /api/templates/*.
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = (s) =>
    (s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  // State
  let projects = [];
  let savedCreatives = [];
  let exploreTemplates = [];
  let currentFolder = ""; // '' (all) | 'favorites' | 'unassigned' | <uuid>
  let currentMediaType = ""; // '' | 'image' | 'video'
  let searchQuery = "";
  let selectedColor = "#8d3624";
  let userProfile = null;

  // Templates State
  let currentViewMode = "templates"; // 'templates' | 'generations'
  let activeCategory = "all";
  let templateSearchQuery = "";
  let templateMediaType = "all";
  let recreateAspect = "4:5";
  let uploadedProductFile = null;

  // -------------------------------------------------------------------------
  // Helper: Relative Time Format
  // -------------------------------------------------------------------------
  function formatRelativeTime(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      const diff = Math.floor((Date.now() - d.getTime()) / 1000);
      if (diff < 60) return "Just now";
      if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
      if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch (_) {
      return "";
    }
  }

  // -------------------------------------------------------------------------
  // Primary View Mode Switching: Explore Templates vs My Generations
  // -------------------------------------------------------------------------
  function setViewMode(mode) {
    currentViewMode = mode;
    const secTemplates = $("lib_section_templates");
    const secGenerations = $("lib_section_generations");
    const navTemplates = $("lib_nav_templates");
    const navGenerations = $("lib_nav_generations");
    const subnavGenerations = $("lib_generations_subnav");

    if (mode === "templates") {
      if (secTemplates) secTemplates.hidden = false;
      if (secGenerations) secGenerations.hidden = true;
      if (navTemplates) navTemplates.classList.add("active");
      if (navGenerations) navGenerations.classList.remove("active");
      if (subnavGenerations) subnavGenerations.hidden = true;
      loadExploreTemplates();
    } else {
      if (secTemplates) secTemplates.hidden = true;
      if (secGenerations) secGenerations.hidden = false;
      if (navTemplates) navTemplates.classList.remove("active");
      if (navGenerations) navGenerations.classList.add("active");
      if (subnavGenerations) subnavGenerations.hidden = false;
      loadSavedCreatives();
    }
  }

  // -------------------------------------------------------------------------
  // Explore Templates API & Showcase
  // -------------------------------------------------------------------------
  async function loadExploreTemplates() {
    const grid = $("explore_templates_grid");
    if (!grid) return;

    try {
      const params = new URLSearchParams();
      if (activeCategory && activeCategory !== "all") params.set("category", activeCategory);
      if (templateMediaType && templateMediaType !== "all") params.set("media_type", templateMediaType);
      if (templateSearchQuery) params.set("q", templateSearchQuery);

      const res = await fetch(`/api/templates/explore?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to load templates");
      const data = await res.json();
      exploreTemplates = data.templates || [];
      renderTemplatesGrid();
    } catch (err) {
      if (grid) {
        grid.innerHTML = `<div class="media-empty error" style="grid-column: 1 / -1;"><i class="fa-solid fa-triangle-exclamation"></i><span>Could not load templates: ${esc(err.message)}</span></div>`;
      }
    }
  }

  function renderTemplatesGrid() {
    const grid = $("explore_templates_grid");
    if (!grid) return;

    if (!exploreTemplates.length) {
      grid.innerHTML = `
        <div class="media-empty" style="grid-column: 1 / -1; padding: 48px 20px; text-align: center;">
          <i class="fa-solid fa-compass" style="font-size: 32px; color: var(--ink-3); margin-bottom: 12px;"></i>
          <h3>No templates matched your filter</h3>
          <p class="muted">Try selecting "All" or search for another keyword like "perfume", "watch", or "can".</p>
          <button type="button" class="btn btn-sm btn-outline" style="margin-top: 14px;" id="btn_reset_tpl_filters">Reset Filters</button>
        </div>
      `;
      const resetBtn = $("btn_reset_tpl_filters");
      if (resetBtn) {
        resetBtn.addEventListener("click", () => {
          activeCategory = "all";
          templateSearchQuery = "";
          const catBtns = document.querySelectorAll(".tpl-cat-btn");
          catBtns.forEach((b) => b.classList.toggle("active", b.dataset.cat === "all"));
          if ($("tpl_search_input")) $("tpl_search_input").value = "";
          loadExploreTemplates();
        });
      }
      return;
    }

    grid.innerHTML = exploreTemplates
      .map((tpl) => {
        const cat = tpl.category || "Ads";
        const ind = tpl.industry_label || "";
        const title = tpl.title || "Advertising Visual Reference";
        const movement = tpl.movement || "";

        return `
        <article class="tpl-card" data-template-id="${esc(tpl.id)}">
          <div class="tpl-card-media" role="button" tabindex="0" title="Click to recreate visual with your product">
            <img src="${esc(tpl.image_url)}" alt="${esc(title)}" loading="lazy">
            <div class="tpl-card-top-badges">
              <span class="tpl-pill-badge">${esc(cat)}</span>
              ${ind ? `<span class="tpl-pill-badge" style="font-size:10px;">${esc(ind)}</span>` : ""}
            </div>
            <div class="tpl-card-hover-overlay">
              <h4 class="tpl-hover-title">${esc(title)}</h4>
              ${movement ? `<p class="tpl-hover-sub">${esc(movement)}</p>` : ""}
              <button type="button" class="btn-tpl-recreate-hover" data-open-recreate="${esc(tpl.id)}">
                <i class="fa-solid fa-wand-magic-sparkles"></i> Recreate ✨
              </button>
            </div>
          </div>
        </article>
      `;
      })
      .join("");

    // Wire template card click
    grid.querySelectorAll(".tpl-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        const tplId = card.dataset.templateId;
        if (tplId) openRecreateModal(tplId);
      });
    });
  }

  // -------------------------------------------------------------------------
  // Recreate Template Modal (Exact User Provided Design)
  // -------------------------------------------------------------------------
  async function openRecreateModal(templateId) {
    const dlg = $("recreate_template_modal");
    if (!dlg) return;

    let tpl = exploreTemplates.find((t) => String(t.id) === String(templateId));
    if (!tpl) {
      try {
        const res = await fetch(`/api/templates/detail/${templateId}`);
        if (res.ok) {
          const d = await res.json();
          tpl = d.template;
        }
      } catch (_) {}
    }

    if (!tpl) return;

    // Populate Left Column
    if ($("rec_template_id")) $("rec_template_id").value = tpl.id;
    if ($("rec_preview_img")) {
      $("rec_preview_img").src = tpl.image_url;
      $("rec_preview_img").alt = tpl.title;
    }
    if ($("rec_tpl_category")) $("rec_tpl_category").textContent = tpl.category || "Product shot";
    if ($("rec_tpl_industry")) $("rec_tpl_industry").textContent = tpl.industry_label || "Ad Creative";
    if ($("rec_tpl_name")) $("rec_tpl_name").textContent = tpl.title || "Advertising Reference";
    if ($("rec_tpl_movement")) $("rec_tpl_movement").textContent = tpl.movement || tpl.lighting || "Commercial visual aesthetic";

    // Palette dots
    const paletteRow = $("rec_tpl_palette");
    if (paletteRow && Array.isArray(tpl.colors)) {
      paletteRow.innerHTML = tpl.colors
        .slice(0, 6)
        .map((c) => `<span class="rec-color-dot" style="background-color: ${esc(c)};" title="${esc(c)}"></span>`)
        .join("");
    }

    // Reset Form Fields
    uploadedProductFile = null;
    if ($("rec_product_preview")) $("rec_product_preview").hidden = true;
    if ($("rec_product_cta")) $("rec_product_cta").hidden = false;
    if ($("rec_product_file")) $("rec_product_file").value = "";
    if ($("rec_brand_name")) $("rec_brand_name").value = "";
    if ($("rec_product_name")) $("rec_product_name").value = "";
    if ($("rec_user_edit")) $("rec_user_edit").value = "";

    // Reset Aspect Ratio
    recreateAspect = "4:5";
    document.querySelectorAll("#rec_aspect_seg button").forEach((b) => {
      b.classList.toggle("active", b.dataset.ratio === "4:5");
    });

    // Reset Status & Result
    if ($("rec_status_alert")) $("rec_status_alert").hidden = true;
    if ($("rec_result_box")) $("rec_result_box").hidden = true;

    const btnSubmit = $("btn_submit_recreate");
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = `<span>Recreate ✨ 1.5</span>`;
    }

    if (!dlg.open) dlg.showModal();
  }

  function closeRecreateModal() {
    const dlg = $("recreate_template_modal");
    if (dlg && dlg.open) dlg.close();
  }

  // Handle Product Upload Dropzone
  function setupRecreateUpload() {
    const drop = $("rec_product_drop");
    const fileInput = $("rec_product_file");
    const changeBtn = $("btn_change_product");

    if (drop && fileInput) {
      drop.addEventListener("click", (e) => {
        if (e.target !== changeBtn) {
          fileInput.click();
        }
      });

      if (changeBtn) {
        changeBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          fileInput.click();
        });
      }

      fileInput.addEventListener("change", () => {
        if (fileInput.files && fileInput.files[0]) {
          handleProductFile(fileInput.files[0]);
        }
      });

      // Drag and drop
      drop.addEventListener("dragover", (e) => {
        e.preventDefault();
        drop.style.borderColor = "var(--accent)";
      });
      drop.addEventListener("dragleave", () => {
        drop.style.borderColor = "";
      });
      drop.addEventListener("drop", (e) => {
        e.preventDefault();
        drop.style.borderColor = "";
        if (e.dataTransfer?.files?.[0]) {
          handleProductFile(e.dataTransfer.files[0]);
        }
      });
    }

    // Aspect ratio selector
    const aspectSeg = $("rec_aspect_seg");
    if (aspectSeg) {
      aspectSeg.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          aspectSeg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          recreateAspect = btn.dataset.ratio || "4:5";
        });
      });
    }

    // Form submission
    const form = $("recreate_form");
    if (form) {
      form.addEventListener("submit", handleRecreateSubmit);
    }

    // Modal Close
    const closeBtn = $("btn_close_recreate");
    if (closeBtn) closeBtn.addEventListener("click", closeRecreateModal);

    // Again button in result
    const againBtn = $("rec_btn_again");
    if (againBtn) {
      againBtn.addEventListener("click", () => {
        if ($("rec_result_box")) $("rec_result_box").hidden = true;
        const btnSubmit = $("btn_submit_recreate");
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = `<span>Recreate ✨ 1.5</span>`;
        }
      });
    }

    // Studio button in result
    const studioBtn = $("rec_btn_studio");
    if (studioBtn) {
      studioBtn.addEventListener("click", () => {
        closeRecreateModal();
        if (typeof window.showView === "function") window.showView("image", { push: true });
      });
    }
  }

  function handleProductFile(file) {
    if (!file || !file.type.startsWith("image/")) {
      if (typeof notify === "function") notify("Please select a valid image file (PNG/JPG)", "warning");
      return;
    }
    uploadedProductFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
      const thumb = $("rec_product_thumb");
      const nameEl = $("rec_product_filename");
      const previewBox = $("rec_product_preview");
      const ctaBox = $("rec_product_cta");

      if (thumb) thumb.src = e.target.result;
      if (nameEl) nameEl.textContent = file.name;
      if (previewBox) previewBox.hidden = false;
      if (ctaBox) ctaBox.hidden = true;
    };
    reader.readAsDataURL(file);
  }

  async function handleRecreateSubmit(e) {
    e.preventDefault();

    if (!uploadedProductFile) {
      if (typeof notify === "function") notify("Please upload your product image to recreate this template.", "warning");
      const drop = $("rec_product_drop");
      if (drop) {
        drop.style.borderColor = "var(--danger)";
        setTimeout(() => (drop.style.borderColor = ""), 1500);
      }
      return;
    }

    const tplId = $("rec_template_id")?.value;
    if (!tplId) return;

    const brandName = $("rec_brand_name")?.value.trim() || "";
    const productName = $("rec_product_name")?.value.trim() || "";
    const userEdit = $("rec_user_edit")?.value.trim() || "";

    const btnSubmit = $("btn_submit_recreate");
    const statusAlert = $("rec_status_alert");
    const statusText = $("rec_status_text");
    const resultBox = $("rec_result_box");

    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Rendering with AI...</span>`;
    }
    if (statusAlert) {
      statusAlert.hidden = false;
      if (statusText) statusText.textContent = "Nano Banana Pro is matching composition & lighting with your product...";
    }
    if (resultBox) resultBox.hidden = true;

    try {
      const fd = new FormData();
      fd.append("template_id", tplId);
      fd.append("product_image", uploadedProductFile);
      if (brandName) fd.append("brand_name", brandName);
      if (productName) fd.append("product_name", productName);
      if (userEdit) fd.append("user_edit", userEdit);
      fd.append("aspect_ratio", recreateAspect);
      fd.append("resolution", "2K");

      const res = await fetch("/api/templates/recreate", {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Recreation failed");
      }

      const data = await res.json();

      if (statusAlert) statusAlert.hidden = true;
      if (resultBox) {
        resultBox.hidden = false;
        const resImg = $("rec_result_img");
        if (resImg) resImg.src = data.image_url;
        const resRatio = $("rec_result_ratio");
        if (resRatio) resRatio.textContent = data.aspect_ratio || "4:5";
        const dlBtn = $("rec_download_btn");
        if (dlBtn) dlBtn.href = data.image_url;
      }

      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<i class="fa-solid fa-check"></i> <span>Recreated Successfully</span>`;
      }

      if (typeof notify === "function") notify("Commercial ad created and stored in your library!", "success");

      // Notify updates
      window.dispatchEvent(new CustomEvent("saved-creatives-updated"));
      updateCategoryCounts();
    } catch (err) {
      if (statusAlert) statusAlert.hidden = true;
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<span>Recreate ✨ 1.5</span>`;
      }
      if (typeof notify === "function") notify(err.message || "Could not recreate template", "error");
    }
  }

  // -------------------------------------------------------------------------
  // Project Management API
  // -------------------------------------------------------------------------
  async function loadProjects() {
    try {
      const res = await fetch("/api/projects");
      if (!res.ok) throw new Error("Failed to load projects");
      const data = await res.json();
      projects = data.projects || [];
      renderProjectsSidebar();
      renderStudioProjectMenus();
      renderProfileProjectList();
    } catch (err) {
      console.warn("Could not load projects:", err);
    }
  }

  function renderProjectsSidebar() {
    const list = $("library_folder_list");
    if (!list) return;

    if (!projects.length) {
      list.innerHTML = `<div style="padding: 8px 12px; font-size: 12px; color: var(--ink-3);">No folders created yet.</div>`;
      return;
    }

    list.innerHTML = projects
      .map((proj) => {
        const isActive = currentFolder === proj.id;
        const color = proj.color || "#8d3624";
        const count = proj.creative_count || 0;
        return `
          <button type="button" class="lib-folder-item ${isActive ? "active" : ""}" data-folder-id="${esc(proj.id)}">
            <span class="lib-folder-dot" style="background-color: ${esc(color)};"></span>
            <span class="lib-folder-name" title="${esc(proj.name)}">${esc(proj.name)}</span>
            <span class="lib-folder-count">${count}</span>
          </button>
        `;
      })
      .join("");
  }

  function renderStudioProjectMenus() {
    const imgList = $("img_project_list");
    const vidList = $("vid_project_list");

    const buildOptionsHtml = (selectedId) => {
      let html = `
        <button type="button" class="project-pop-item ${!selectedId ? "active" : ""}" data-val="">
          <span class="project-pop-dot" style="background: var(--ink-3);"></span>
          <span>No Folder (Unassigned)</span>
        </button>
      `;
      projects.forEach((p) => {
        const isSel = selectedId === p.id;
        html += `
          <button type="button" class="project-pop-item ${isSel ? "active" : ""}" data-val="${esc(p.id)}">
            <span class="project-pop-dot" style="background: ${esc(p.color || "#8d3624")};"></span>
            <span>${esc(p.name)}</span>
          </button>
        `;
      });
      return html;
    };

    if (imgList) {
      const cur = $("img_folder_id")?.value || "";
      imgList.innerHTML = buildOptionsHtml(cur);
    }
    if (vidList) {
      const cur = $("vid_folder_id")?.value || "";
      vidList.innerHTML = buildOptionsHtml(cur);
    }
  }

  function renderProfileProjectList() {
    const list = $("prof_project_list");
    if (!list) return;

    if (!projects.length) {
      list.innerHTML = `<div style="padding: 10px; font-size: 13px; color: var(--ink-3); text-align: center;">No project folders created yet. Click "New Folder" above.</div>`;
      return;
    }

    list.innerHTML = projects
      .map((proj) => {
        const color = proj.color || "#8d3624";
        const count = proj.creative_count || 0;
        return `
          <div class="prof-project-item">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="lib-folder-dot" style="background-color: ${esc(color)};"></span>
              <span style="font-weight: 500;">${esc(proj.name)}</span>
              <span class="muted small">(${count} items)</span>
            </div>
            <button type="button" class="btn btn-xs btn-ghost btn-open-proj-from-prof" data-proj-id="${esc(proj.id)}">
              View Folder
            </button>
          </div>
        `;
      })
      .join("");
  }

  // -------------------------------------------------------------------------
  // Saved Creatives API & Filtering
  // -------------------------------------------------------------------------
  async function loadSavedCreatives() {
    const grid = $("library_grid");
    const emptyState = $("library_empty");
    if (!grid) return;

    try {
      const params = new URLSearchParams();
      if (currentMediaType) params.set("type", currentMediaType);
      if (currentFolder === "favorites") {
        params.set("favorites", "true");
      } else if (currentFolder === "unassigned") {
        params.set("folder_id", "unassigned");
      } else if (currentFolder) {
        params.set("folder_id", currentFolder);
      }
      if (searchQuery) params.set("q", searchQuery);

      const url = `/api/saved/list?${params.toString()}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load creatives");

      const data = await res.json();
      savedCreatives = data.creatives || [];

      // Update badge counts
      updateCategoryCounts();
      updateHeaderAndActionBar();
      renderGrid();
    } catch (err) {
      if (grid) {
        grid.innerHTML = `<div class="media-empty error" style="grid-column: 1 / -1;"><i class="fa-solid fa-triangle-exclamation"></i><span>Could not load creatives: ${esc(err.message)}</span></div>`;
      }
    }
  }

  function updateCategoryCounts() {
    fetch("/api/user/profile")
      .then((r) => r.json())
      .then((d) => {
        if (d.stats) {
          if ($("lib_count_all")) $("lib_count_all").textContent = d.stats.total_creatives || 0;
          if ($("lib_count_all_sub")) $("lib_count_all_sub").textContent = d.stats.total_creatives || 0;
          if ($("lib_count_favorites")) $("lib_count_favorites").textContent = d.stats.favorites_count || 0;
          if ($("lib_count_unassigned")) $("lib_count_unassigned").textContent = d.stats.unassigned_count || 0;
          if ($("prof_stat_total")) $("prof_stat_total").textContent = d.stats.total_creatives || 0;
          if ($("prof_stat_breakdown"))
            $("prof_stat_breakdown").textContent = `${d.stats.total_images || 0} images · ${d.stats.total_videos || 0} videos`;
          if ($("prof_stat_projects")) $("prof_stat_projects").textContent = d.stats.total_projects || 0;
        }
      })
      .catch(() => {});
  }

  function updateHeaderAndActionBar() {
    const titleEl = $("lib_active_folder_title");
    const descEl = $("lib_active_folder_desc");
    const bar = $("project_action_bar");

    if (!currentFolder) {
      if (titleEl) titleEl.textContent = "All Generations";
      if (descEl) descEl.textContent = "Every image and video ad you create collects here with its exact prompt and uploaded references.";
      if (bar) bar.hidden = true;
    } else if (currentFolder === "favorites") {
      if (titleEl) titleEl.textContent = "Starred Favorites";
      if (descEl) descEl.textContent = "Your highest performing and favorite generated ads across all campaigns.";
      if (bar) bar.hidden = true;
    } else if (currentFolder === "unassigned") {
      if (titleEl) titleEl.textContent = "Unassigned Generations";
      if (descEl) descEl.textContent = "Generations that haven't been assigned to a project folder yet.";
      if (bar) bar.hidden = true;
    } else {
      const proj = projects.find((p) => p.id === currentFolder);
      if (proj) {
        if (titleEl) titleEl.textContent = proj.name;
        if (descEl) descEl.textContent = proj.description || "Organized project folder";
        if (bar) {
          bar.hidden = false;
          if ($("proj_active_color")) $("proj_active_color").style.backgroundColor = proj.color || "#8d3624";
          if ($("proj_active_name")) $("proj_active_name").textContent = proj.name;
          if ($("proj_active_count"))
            $("proj_active_count").textContent = `· ${savedCreatives.length} item${savedCreatives.length === 1 ? "" : "s"}`;
        }
      }
    }
  }

  function renderGrid() {
    const grid = $("library_grid");
    const emptyState = $("library_empty");
    if (!grid) return;

    if (!savedCreatives.length) {
      grid.innerHTML = "";
      if (emptyState) emptyState.hidden = false;
      return;
    }

    if (emptyState) emptyState.hidden = true;

    grid.innerHTML = savedCreatives
      .map((item) => {
        const isVid = item.type === "video" || (item.media_url || "").endsWith(".mp4");
        const ratioClass = (item.aspect_ratio || "9:16").replace(":", "-");
        const isFav = Boolean(item.is_favorite);
        const timeStr = formatRelativeTime(item.created_at);

        // Find associated project
        const projectObj = item.folder_id ? projects.find((p) => p.id === item.folder_id) : null;

        // Parse reference images
        let refImages = [];
        if (Array.isArray(item.reference_images)) {
          refImages = item.reference_images;
        } else if (typeof item.reference_images === "string") {
          try {
            refImages = JSON.parse(item.reference_images);
          } catch (_) {}
        }

        const refStripHtml =
          refImages && refImages.length
            ? `
            <div class="lib-ref-strip" title="Uploaded reference photos used in this render">
              <span class="lib-ref-label"><i class="fa-solid fa-paperclip"></i> Refs (${refImages.length})</span>
              ${refImages
                .map(
                  (url) => `
                <img src="${esc(url)}" class="lib-ref-thumb" alt="Reference image" title="Click to view reference image" data-ref-url="${esc(url)}" loading="lazy">
              `
                )
                .join("")}
            </div>`
            : "";

        return `
        <article class="saved-card" data-cid="${esc(item.id)}">
          <div class="saved-card-media r-${ratioClass}" data-url="${esc(item.media_url)}" data-type="${isVid ? "video" : "image"}" data-prompt="${esc(item.prompt)}" data-aspect="${esc(item.aspect_ratio || "9:16")}" role="button" tabindex="0" title="Click to inspect in high-resolution viewer">
            ${
              isVid
                ? `<video src="${esc(item.media_url)}" muted loop playsinline preload="metadata"></video>
                   <div class="saved-play-badge"><i class="fa-solid fa-play"></i></div>`
                : `<img src="${esc(item.media_url)}" alt="${esc(item.prompt)}" loading="lazy">`
            }
            <div class="saved-card-overlay-top">
              <span class="saved-badge ${isVid ? "badge-video" : "badge-image"}">${isVid ? "VIDEO" : "IMAGE"} · ${esc(item.aspect_ratio || "9:16")}</span>
              <button type="button" class="saved-fav-btn ${isFav ? "active" : ""}" data-fav-id="${esc(item.id)}" title="${isFav ? "Remove favorite" : "Star favorite"}">
                <i class="${isFav ? "fa-solid" : "fa-regular"} fa-star"></i>
              </button>
            </div>
          </div>

          <div class="saved-card-body">
            <div class="saved-card-meta">
              <span class="saved-time">${esc(timeStr)}</span>
              ${
                projectObj
                  ? `<span class="lib-project-tag" title="Project: ${esc(projectObj.name)}">
                      <span class="lib-folder-dot" style="background-color: ${esc(projectObj.color || "#8d3624")}; width: 6px; height: 6px;"></span>
                      <span>${esc(projectObj.name)}</span>
                    </span>`
                  : `<span class="muted small" style="font-size: 11px;">Unassigned</span>`
              }
            </div>

            ${refStripHtml}

            <p class="saved-prompt-text" title="${esc(item.prompt)}">${esc(item.prompt || "No prompt text recorded.")}</p>

            <div class="saved-actions">
              <button type="button" class="btn-saved-action btn-copy-prompt" data-copy-prompt="${esc(item.prompt)}" title="Copy exact prompt">
                <i class="fa-regular fa-copy"></i> Copy
              </button>
              <button type="button" class="btn-saved-action btn-load-studio" data-load-type="${isVid ? "video" : "image"}" data-load-prompt="${esc(item.prompt)}" title="Populate into Studio">
                <i class="fa-solid fa-arrow-up-right-from-square"></i> Use in Studio
              </button>
              
              <div class="saved-actions-right">
                <!-- Move to Folder Menu -->
                <div class="lib-move-dropdown">
                  <button type="button" class="saved-icon-btn btn-trigger-move" data-cid="${esc(item.id)}" title="Move to Project Folder">
                    <i class="fa-regular fa-folder-open"></i>
                  </button>
                  <div class="lib-move-pop" hidden data-pop-cid="${esc(item.id)}">
                    <div style="font-size: 11px; font-weight:600; color:var(--ink-3); padding:4px 8px; text-transform:uppercase;">Move to Folder</div>
                    <button type="button" class="lib-move-item" data-move-folder="">
                      <span class="lib-folder-dot" style="background: var(--ink-3);"></span>
                      <span>Unassign</span>
                    </button>
                    ${projects
                      .map(
                        (p) => `
                      <button type="button" class="lib-move-item" data-move-folder="${esc(p.id)}">
                        <span class="lib-folder-dot" style="background: ${esc(p.color || "#8d3624")};"></span>
                        <span>${esc(p.name)}</span>
                      </button>
                    `
                      )
                      .join("")}
                  </div>
                </div>

                <a href="${esc(item.media_url)}" download="${isVid ? "video_ad.mp4" : "image_ad.png"}" class="saved-icon-btn" title="Download file" target="_blank">
                  <i class="fa-solid fa-download"></i>
                </a>
                <button type="button" class="saved-icon-btn danger" data-delete-id="${esc(item.id)}" title="Delete generation">
                  <i class="fa-regular fa-trash-can"></i>
                </button>
              </div>
            </div>
          </div>
        </article>
        `;
      })
      .join("");

    // Wire hover video autoplay & click viewer
    grid.querySelectorAll(".saved-card-media").forEach((slot) => {
      const vid = slot.querySelector("video");
      if (vid) {
        slot.addEventListener("mouseenter", () => vid.play().catch(() => {}));
        slot.addEventListener("mouseleave", () => {
          vid.pause();
          vid.currentTime = 0;
        });
      }
      slot.addEventListener("click", () => {
        const url = slot.dataset.url;
        const type = slot.dataset.type;
        const prompt = slot.dataset.prompt;
        const aspect = slot.dataset.aspect;
        if (typeof window.openViewer === "function") {
          window.openViewer({
            items: [{ url, type, prompt, aspect, el: slot }],
            index: 0,
          });
        }
      });
    });

    // Wire reference image click preview
    grid.querySelectorAll(".lib-ref-thumb").forEach((thumb) => {
      thumb.addEventListener("click", (e) => {
        e.stopPropagation();
        const url = thumb.dataset.refUrl;
        if (url && typeof window.openViewer === "function") {
          window.openViewer({
            items: [{ url, type: "image", prompt: "Uploaded Reference Photo", aspect: "1:1", el: thumb }],
            index: 0,
          });
        }
      });
    });
  }

  // -------------------------------------------------------------------------
  // Project Editor Modal Handling
  // -------------------------------------------------------------------------
  function openProjectModal(editProjectId = null) {
    const dlg = $("project_editor_modal");
    if (!dlg) return;

    const titleEl = $("proj_modal_title");
    const idInput = $("proj_input_id");
    const nameInput = $("proj_input_name");
    const descInput = $("proj_input_desc");

    if (editProjectId) {
      const proj = projects.find((p) => p.id === editProjectId);
      if (proj) {
        if (titleEl) titleEl.textContent = "Edit Project Folder";
        if (idInput) idInput.value = proj.id;
        if (nameInput) nameInput.value = proj.name;
        if (descInput) descInput.value = proj.description || "";
        selectedColor = proj.color || "#8d3624";
      }
    } else {
      if (titleEl) titleEl.textContent = "New Project Folder";
      if (idInput) idInput.value = "";
      if (nameInput) nameInput.value = "";
      if (descInput) descInput.value = "";
      selectedColor = "#8d3624";
    }

    // Update color dots
    document.querySelectorAll(".color-dot-pick").forEach((dot) => {
      dot.classList.toggle("active", dot.dataset.color === selectedColor);
    });

    if (!dlg.open) dlg.showModal();
    if (nameInput) nameInput.focus();
  }

  function closeProjectModal() {
    const dlg = $("project_editor_modal");
    if (dlg && dlg.open) dlg.close();
  }

  async function handleProjectSubmit(e) {
    e.preventDefault();
    const id = $("proj_input_id")?.value;
    const name = $("proj_input_name")?.value.trim();
    const description = $("proj_input_desc")?.value.trim();

    if (!name) {
      if (typeof notify === "function") notify("Please enter a project name", "warning");
      return;
    }

    const payload = {
      name,
      description,
      color: selectedColor,
      icon: "folder",
    };

    try {
      if (id) {
        const res = await fetch(`/api/projects/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Could not update project");
        if (typeof notify === "function") notify("Project updated!", "success");
      } else {
        const res = await fetch("/api/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Could not create project");
        const data = await res.json();
        if (typeof notify === "function") notify("Project folder created!", "success");
        if (data.project?.id) currentFolder = data.project.id;
      }

      closeProjectModal();
      await loadProjects();
      await loadSavedCreatives();
    } catch (err) {
      if (typeof notify === "function") notify(err.message || "Failed to save project", "error");
    }
  }

  // -------------------------------------------------------------------------
  // User Profile Modal Handling
  // -------------------------------------------------------------------------
  async function openProfileModal() {
    const dlg = $("profile_modal");
    if (!dlg) return;

    try {
      const res = await fetch("/api/user/profile");
      if (res.ok) {
        userProfile = await res.json();
        populateProfileUI(userProfile);
      }
    } catch (_) {}

    if (!dlg.open) dlg.showModal();
  }

  function populateProfileUI(data) {
    if (!data) return;
    const user = data.user || {};
    const credits = data.credits || { total: 500, used: 0, remaining: 500 };
    const stats = data.stats || {};

    const email = user.email || "creator@example.com";
    const name = user.name || email.split("@")[0] || "Creator";
    const initials = (name.slice(0, 2) || "AC").toUpperCase();
    const planLabel = user.plan_label ? user.plan_label.toUpperCase() : `${(user.plan || "Free").toUpperCase()} PLAN`;

    // Avatar & Hero
    if ($("prof_avatar_initials")) $("prof_avatar_initials").textContent = initials;
    if ($("prof_display_name")) $("prof_display_name").textContent = name;
    if ($("prof_email")) $("prof_email").textContent = email;
    if ($("prof_plan_badge")) $("prof_plan_badge").textContent = planLabel;

    // Top Dropdown elements as well
    if ($("dropdown_user_avatar")) $("dropdown_user_avatar").textContent = initials;
    if ($("dropdown_user_email")) $("dropdown_user_email").textContent = email;
    if ($("dropdown_user_plan")) $("dropdown_user_plan").textContent = planLabel;

    // Credits
    const pct = Math.max(0, Math.min(100, Math.round((credits.remaining / credits.total) * 100)));
    if ($("prof_credits_pct")) $("prof_credits_pct").textContent = `${pct}% left`;
    if ($("prof_credits_remaining"))
      $("prof_credits_remaining").innerHTML = `${credits.remaining} <span class="metric-sub">/ ${credits.total}</span>`;
    if ($("prof_credits_bar")) $("prof_credits_bar").style.width = `${pct}%`;

    if ($("dropdown_credits_num")) $("dropdown_credits_num").textContent = `${credits.remaining} / ${credits.total}`;
    if ($("dropdown_credits_bar")) $("dropdown_credits_bar").style.width = `${pct}%`;

    // Metrics
    if ($("prof_stat_total")) $("prof_stat_total").textContent = stats.total_creatives || 0;
    if ($("prof_stat_breakdown"))
      $("prof_stat_breakdown").textContent = `${stats.total_images || 0} images · ${stats.total_videos || 0} videos`;
    if ($("prof_stat_projects")) $("prof_stat_projects").textContent = stats.total_projects || 0;

    // Settings form inputs
    if ($("prof_input_name")) $("prof_input_name").value = user.name || "";
    if ($("prof_input_email")) $("prof_input_email").value = email;

    renderProfileProjectList();
  }

  function closeProfileModal() {
    const dlg = $("profile_modal");
    if (dlg && dlg.open) dlg.close();
  }

  // -------------------------------------------------------------------------
  // Event Delegation for All Actions
  // -------------------------------------------------------------------------
  document.addEventListener("click", async (e) => {
    // 1. Copy Prompt
    const copyBtn = e.target.closest(".btn-copy-prompt");
    if (copyBtn) {
      e.stopPropagation();
      const prompt = copyBtn.dataset.copyPrompt;
      if (prompt) {
        try {
          await navigator.clipboard.writeText(prompt);
          const orig = copyBtn.innerHTML;
          copyBtn.innerHTML = '<i class="fa-solid fa-check" style="color:var(--accent);"></i> Copied';
          setTimeout(() => {
            copyBtn.innerHTML = orig;
          }, 1800);
          if (typeof notify === "function") notify("Prompt copied to clipboard!", "info");
        } catch (_) {}
      }
      return;
    }

    // 2. Use in Studio
    const loadBtn = e.target.closest(".btn-load-studio");
    if (loadBtn) {
      e.stopPropagation();
      const targetStudio = loadBtn.dataset.loadType;
      const prompt = loadBtn.dataset.loadPrompt;

      if (typeof window.showView === "function") {
        window.showView(targetStudio, { push: true });
      } else {
        const navBtn = document.querySelector(`.nav-btn[data-view="${targetStudio}"]`);
        if (navBtn) navBtn.click();
      }

      const ta = $(targetStudio === "video" ? "vid_prompt" : "img_prompt");
      if (ta && prompt) {
        ta.value = prompt;
        ta.dispatchEvent(new Event("input", { bubbles: true }));
        ta.dispatchEvent(new Event("change", { bubbles: true }));
        ta.focus();
        ta.setSelectionRange(ta.value.length, ta.value.length);
        if (typeof notify === "function") notify(`Loaded prompt into ${targetStudio} studio!`, "success");
      }
      return;
    }

    // 3. Toggle Favorite
    const favBtn = e.target.closest(".saved-fav-btn");
    if (favBtn) {
      e.stopPropagation();
      const id = favBtn.dataset.favId;
      const isFav = favBtn.classList.contains("active");
      const nextFav = !isFav;

      favBtn.classList.toggle("active", nextFav);
      favBtn.querySelector("i").className = nextFav ? "fa-solid fa-star" : "fa-regular fa-star";

      try {
        await fetch("/api/saved/favorite", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, is_favorite: nextFav }),
        });
        const target = savedCreatives.find((x) => x.id === id);
        if (target) target.is_favorite = nextFav;
        updateCategoryCounts();
      } catch (_) {}
      return;
    }

    // 4. Delete Creative
    const delBtn = e.target.closest("[data-delete-id]");
    if (delBtn) {
      e.stopPropagation();
      const id = delBtn.dataset.deleteId;
      if (!confirm("Permanently delete this creative from your library?")) return;

      try {
        const res = await fetch(`/api/saved/${id}`, { method: "DELETE" });
        if (res.ok) {
          savedCreatives = savedCreatives.filter((x) => x.id !== id);
          renderGrid();
          updateCategoryCounts();
          loadProjects();
          if (typeof notify === "function") notify("Creative removed from library", "info");
        }
      } catch (_) {}
      return;
    }

    // 5. Trigger Move Popover
    const triggerMoveBtn = e.target.closest(".btn-trigger-move");
    if (triggerMoveBtn) {
      e.stopPropagation();
      const cid = triggerMoveBtn.dataset.cid;
      const pop = document.querySelector(`.lib-move-pop[data-pop-cid="${cid}"]`);
      document.querySelectorAll(".lib-move-pop").forEach((p) => {
        if (p !== pop) p.hidden = true;
      });
      if (pop) pop.hidden = !pop.hidden;
      return;
    }

    if (!e.target.closest(".lib-move-dropdown")) {
      document.querySelectorAll(".lib-move-pop").forEach((p) => (p.hidden = true));
    }

    // 6. Move Creative Item to Folder
    const moveItemBtn = e.target.closest(".lib-move-item");
    if (moveItemBtn) {
      e.stopPropagation();
      const pop = moveItemBtn.closest(".lib-move-pop");
      const cid = pop?.dataset.popCid;
      const folderId = moveItemBtn.dataset.moveFolder || null;

      if (cid) {
        try {
          const res = await fetch(`/api/saved/${cid}/move`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_id: folderId }),
          });
          if (res.ok) {
            if (pop) pop.hidden = true;
            if (typeof notify === "function") notify("Moved creative!", "success");
            await loadProjects();
            await loadSavedCreatives();
          }
        } catch (_) {}
      }
      return;
    }

    // 7. Sidebar View Mode: Explore Templates
    if (e.target.closest("#lib_nav_templates")) {
      setViewMode("templates");
      return;
    }

    // 8. Sidebar View Mode: My Generations
    if (e.target.closest("#lib_nav_generations")) {
      setViewMode("generations");
      return;
    }

    // 9. Sidebar Sub-filter buttons (All Assets, Favorites, Unassigned)
    const filterBtn = e.target.closest("#lib_generations_subnav .lib-filter-btn");
    if (filterBtn) {
      document.querySelectorAll("#lib_generations_subnav .lib-filter-btn, #lib_generations_subnav .lib-folder-item").forEach((b) => b.classList.remove("active"));
      filterBtn.classList.add("active");
      currentFolder = filterBtn.dataset.folder || "";
      loadSavedCreatives();
      return;
    }

    // 10. Sidebar Project Folder Item
    const folderItem = e.target.closest("#lib_generations_subnav .lib-folder-item");
    if (folderItem) {
      document.querySelectorAll("#lib_generations_subnav .lib-filter-btn, #lib_generations_subnav .lib-folder-item").forEach((b) => b.classList.remove("active"));
      folderItem.classList.add("active");
      currentFolder = folderItem.dataset.folderId;
      loadSavedCreatives();
      return;
    }

    // 11. Explore Templates: Category filter pills matching Screenshot 1
    const catBtn = e.target.closest(".tpl-cat-btn");
    if (catBtn) {
      document.querySelectorAll(".tpl-cat-btn").forEach((b) => b.classList.remove("active"));
      catBtn.classList.add("active");
      activeCategory = catBtn.dataset.cat || "all";
      loadExploreTemplates();
      return;
    }

    // 12. Explore Templates: Hover Recreate Button
    const recHoverBtn = e.target.closest(".btn-tpl-recreate-hover");
    if (recHoverBtn) {
      e.stopPropagation();
      const tplId = recHoverBtn.dataset.openRecreate;
      if (tplId) openRecreateModal(tplId);
      return;
    }

    // 13. Explore Templates: Quick bottom bar generate
    const quickGenBtn = e.target.closest("#btn_tpl_quick_generate");
    if (quickGenBtn) {
      const qInput = $("tpl_quick_prompt");
      const promptVal = qInput?.value.trim();
      if (!promptVal) {
        if (typeof notify === "function") notify("Write an ad idea first.", "warning");
        if (qInput) qInput.focus();
        return;
      }
      // Populate prompt into Image Studio
      if (typeof window.showView === "function") {
        window.showView("image", { push: true });
        setTimeout(() => {
          const ta = $("img_prompt");
          if (ta) {
            ta.value = promptVal;
            ta.dispatchEvent(new Event("input", { bubbles: true }));
            ta.focus();
          }
        }, 80);
      }
      return;
    }

    // 14. Profile modal: "View Folder" button
    const viewFolderFromProf = e.target.closest(".btn-open-proj-from-prof");
    if (viewFolderFromProf) {
      const projId = viewFolderFromProf.dataset.projId;
      closeProfileModal();
      setViewMode("generations");
      if (typeof window.showView === "function") {
        window.showView("library", { push: true });
      }
      setTimeout(() => {
        const item = document.querySelector(`.lib-folder-item[data-folder-id="${projId}"]`);
        if (item) item.click();
      }, 60);
      return;
    }

    // 15. Color dot picker in Project modal
    const colorDot = e.target.closest(".color-dot-pick");
    if (colorDot) {
      document.querySelectorAll(".color-dot-pick").forEach((d) => d.classList.remove("active"));
      colorDot.classList.add("active");
      selectedColor = colorDot.dataset.color || "#8d3624";
      return;
    }

    // 16. Project Action Bar Actions
    if (e.target.closest("#btn_create_image_in_project")) {
      const proj = projects.find((p) => p.id === currentFolder);
      if (proj) {
        if ($("img_folder_id")) $("img_folder_id").value = proj.id;
        if ($("img_project_label")) $("img_project_label").textContent = proj.name;
      }
      if (typeof window.showView === "function") window.showView("image", { push: true });
      return;
    }

    if (e.target.closest("#btn_create_video_in_project")) {
      const proj = projects.find((p) => p.id === currentFolder);
      if (proj) {
        if ($("vid_folder_id")) $("vid_folder_id").value = proj.id;
        if ($("vid_project_label")) $("vid_project_label").textContent = proj.name;
      }
      if (typeof window.showView === "function") window.showView("video", { push: true });
      return;
    }

    if (e.target.closest("#btn_edit_project")) {
      if (currentFolder) openProjectModal(currentFolder);
      return;
    }

    if (e.target.closest("#btn_delete_project")) {
      if (!currentFolder) return;
      const proj = projects.find((p) => p.id === currentFolder);
      if (!confirm(`Delete project "${proj?.name || "folder"}"? Creatives inside will become unassigned.`)) return;

      try {
        const res = await fetch(`/api/projects/${currentFolder}`, { method: "DELETE" });
        if (res.ok) {
          if (typeof notify === "function") notify("Project folder removed", "info");
          currentFolder = "";
          const allBtn = document.querySelector('#lib_generations_subnav .lib-filter-btn[data-folder=""]');
          if (allBtn) allBtn.click();
          await loadProjects();
        }
      } catch (_) {}
      return;
    }

    // 17. Studio Project Popover item select
    const projPopItem = e.target.closest(".project-pop-item");
    if (projPopItem) {
      const val = projPopItem.dataset.val || "";
      const isImg = projPopItem.closest("#img_project_pop");
      const isVid = projPopItem.closest("#vid_project_pop");

      if (isImg) {
        if ($("img_folder_id")) $("img_folder_id").value = val;
        const proj = projects.find((p) => p.id === val);
        if ($("img_project_label")) $("img_project_label").textContent = proj ? proj.name : "Project";
        if ($("img_project_pop")) $("img_project_pop").hidden = true;
      } else if (isVid) {
        if ($("vid_folder_id")) $("vid_folder_id").value = val;
        const proj = projects.find((p) => p.id === val);
        if ($("vid_project_label")) $("vid_project_label").textContent = proj ? proj.name : "Project";
        if ($("vid_project_pop")) $("vid_project_pop").hidden = true;
      }
      return;
    }

    // 18. Studio project pill open/close toggle
    if (e.target.closest("#btn_img_project")) {
      e.stopPropagation();
      const pop = $("img_project_pop");
      if (pop) pop.hidden = !pop.hidden;
      return;
    }

    if (e.target.closest("#btn_vid_project")) {
      e.stopPropagation();
      const pop = $("vid_project_pop");
      if (pop) pop.hidden = !pop.hidden;
      return;
    }

    if (!e.target.closest("#img_project_menu") && $("img_project_pop")) {
      $("img_project_pop").hidden = true;
    }
    if (!e.target.closest("#vid_project_menu") && $("vid_project_pop")) {
      $("vid_project_pop").hidden = true;
    }
  });

  // -------------------------------------------------------------------------
  // Setup Dialogs & Event Listeners
  // -------------------------------------------------------------------------
  function setupLibraryEvents() {
    setupRecreateUpload();

    // Project Editor Modal Triggers
    if ($("btn_new_project_modal")) $("btn_new_project_modal").addEventListener("click", () => openProjectModal(null));
    if ($("prof_btn_new_project")) $("prof_btn_new_project").addEventListener("click", () => openProjectModal(null));
    if ($("btn_close_proj_modal")) $("btn_close_proj_modal").addEventListener("click", closeProjectModal);
    if ($("btn_cancel_proj_modal")) $("btn_cancel_proj_modal").addEventListener("click", closeProjectModal);
    if ($("project_form")) $("project_form").addEventListener("submit", handleProjectSubmit);

    // Profile Modal Triggers
    if ($("btn_open_profile_dropdown"))
      $("btn_open_profile_dropdown").addEventListener("click", () => {
        const dd = $("user_dropdown");
        if (dd) dd.hidden = true;
        openProfileModal();
      });
    if ($("btn_close_profile")) $("btn_close_profile").addEventListener("click", closeProfileModal);
    if ($("btn_close_profile_foot")) $("btn_close_profile_foot").addEventListener("click", closeProfileModal);
    if ($("btn_go_to_library"))
      $("btn_go_to_library").addEventListener("click", () => {
        closeProfileModal();
        if (typeof window.showView === "function") window.showView("library", { push: true });
      });

    // Profile Settings Form Save Name
    if ($("prof_settings_form")) {
      $("prof_settings_form").addEventListener("submit", (e) => {
        e.preventDefault();
        const newName = $("prof_input_name")?.value.trim();
        if (newName) {
          if ($("prof_display_name")) $("prof_display_name").textContent = newName;
          if ($("dropdown_user_email")) $("dropdown_user_email").textContent = newName;
          if (typeof notify === "function") notify("Display name updated!", "success");
        }
      });
    }

    // User Dropdown "Projects & Library" item
    if ($("btn_open_library_dropdown")) {
      $("btn_open_library_dropdown").addEventListener("click", () => {
        const dd = $("user_dropdown");
        if (dd) dd.hidden = true;
        if (typeof window.showView === "function") window.showView("library", { push: true });
      });
    }

    // Media type filter buttons in My Generations
    const typeSeg = $("lib_media_type_filter");
    if (typeSeg) {
      typeSeg.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          typeSeg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          currentMediaType = btn.dataset.type || "";
          loadSavedCreatives();
        });
      });
    }

    // Media filter in Explore Templates (All, Images, Videos)
    const tplMediaSeg = $("tpl_media_type_filter");
    if (tplMediaSeg) {
      tplMediaSeg.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          tplMediaSeg.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          templateMediaType = btn.dataset.media || "all";
          loadExploreTemplates();
        });
      });
    }

    // Refresh Library button
    if ($("btn_refresh_library")) {
      $("btn_refresh_library").addEventListener("click", () => {
        loadProjects();
        loadSavedCreatives();
        if (typeof notify === "function") notify("Library refreshed", "info");
      });
    }

    // Search Input in My Generations
    const searchInput = $("lib_search_input");
    if (searchInput) {
      let timer = null;
      searchInput.addEventListener("input", (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          searchQuery = e.target.value.trim();
          loadSavedCreatives();
        }, 220);
      });
    }

    // Search Input in Explore Templates
    const tplSearchInput = $("tpl_search_input");
    if (tplSearchInput) {
      let timer = null;
      tplSearchInput.addEventListener("input", (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          templateSearchQuery = e.target.value.trim();
          loadExploreTemplates();
        }, 220);
      });
    }
  }

  // -------------------------------------------------------------------------
  // View Change & Global Listeners
  // -------------------------------------------------------------------------
  window.addEventListener("viewchange", (e) => {
    const v = e.detail?.view;
    if (v === "library" || v === "saved") {
      loadProjects();
      if (currentViewMode === "templates") {
        loadExploreTemplates();
      } else {
        loadSavedCreatives();
      }
    }
  });

  window.addEventListener("saved-creatives-updated", () => {
    loadProjects();
    loadSavedCreatives();
  });

  document.addEventListener("DOMContentLoaded", () => {
    setupLibraryEvents();
    loadProjects();
    // Default to explore templates
    loadExploreTemplates();
  });

  // Global exports
  window.openProfileModal = openProfileModal;
  window.openProjectModal = openProjectModal;
  window.openRecreateModal = openRecreateModal;
  window.loadSavedCreatives = loadSavedCreatives;
  window.loadProjects = loadProjects;
  window.loadExploreTemplates = loadExploreTemplates;
  window.setLibraryViewMode = setViewMode;
})();
