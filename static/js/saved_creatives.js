// Saved Creatives & Prompt Library Manager
// Connects to /api/saved/* with Supabase PostgreSQL and local SQLite persistence.
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  let savedItems = [];
  let currentFilter = "all"; // 'all' | 'video' | 'image' | 'favorites'
  let searchQuery = "";

  // ------------------------------------------------------------ Fetch and Render
  async function loadSavedItems() {
    const grid = $("saved_grid");
    const emptyState = $("saved_empty");
    const countBadge = $("saved_count_badge");
    if (!grid) return;

    try {
      let url = "/api/saved/list";
      const params = new URLSearchParams();
      if (currentFilter === "video" || currentFilter === "image") {
        params.set("type", currentFilter);
      } else if (currentFilter === "favorites") {
        params.set("favorites", "true");
      }
      if (params.toString()) url += `?${params.toString()}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load saved items");
      const data = await res.json();
      savedItems = data.creatives || [];

      if (countBadge) {
        countBadge.textContent = `${savedItems.length} item${savedItems.length === 1 ? "" : "s"}`;
      }

      renderGrid();
    } catch (err) {
      if (grid) {
        grid.innerHTML = `<div class="media-empty error"><i class="fa-solid fa-triangle-exclamation"></i><span>Could not load saved creatives: ${esc(err.message)}</span></div>`;
      }
    }
  }

  function filterItems() {
    return savedItems.filter((item) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const p = (item.prompt || "").toLowerCase();
        const t = (item.title || "").toLowerCase();
        if (!p.includes(q) && !t.includes(q)) return false;
      }
      return true;
    });
  }

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

  function renderGrid() {
    const grid = $("saved_grid");
    const emptyState = $("saved_empty");
    if (!grid) return;

    const items = filterItems();

    if (!items.length) {
      grid.innerHTML = "";
      if (emptyState) emptyState.hidden = false;
      return;
    }

    if (emptyState) emptyState.hidden = true;

    grid.innerHTML = items
      .map((item) => {
        const isVid = item.type === "video" || (item.media_url || "").endsWith(".mp4");
        const ratioClass = (item.aspect_ratio || "9:16").replace(":", "-");
        const isFav = Boolean(item.is_favorite);
        const timeStr = formatRelativeTime(item.created_at);

        return `
        <article class="saved-card" data-cid="${esc(item.id)}">
          <div class="saved-card-media r-${ratioClass}" data-url="${esc(item.media_url)}" data-type="${isVid ? "video" : "image"}" data-prompt="${esc(item.prompt)}" data-aspect="${esc(item.aspect_ratio || "9:16")}" role="button" tabindex="0" title="Click to preview in high-resolution">
            ${
              isVid
                ? `<video src="${esc(item.media_url)}" muted loop playsinline preload="metadata"></video>
                   <div class="saved-play-badge"><i class="fa-solid fa-play"></i></div>`
                : `<img src="${esc(item.media_url)}" alt="${esc(item.prompt)}" loading="lazy">`
            }
            <div class="saved-card-overlay-top">
              <span class="saved-badge ${isVid ? "badge-video" : "badge-image"}">${isVid ? "VIDEO" : "IMAGE"} · ${esc(item.aspect_ratio || "9:16")}</span>
              <button type="button" class="saved-fav-btn ${isFav ? "active" : ""}" data-fav-id="${esc(item.id)}" title="${isFav ? "Remove favorite" : "Favorite this creative"}">
                <i class="${isFav ? "fa-solid" : "fa-regular"} fa-star"></i>
              </button>
            </div>
          </div>

          <div class="saved-card-body">
            <div class="saved-card-meta">
              <span class="saved-time">${esc(timeStr)}</span>
            </div>

            <p class="saved-prompt-text" title="${esc(item.prompt)}">${esc(item.prompt || "No prompt text recorded.")}</p>

            <div class="saved-actions">
              <button type="button" class="btn-saved-action btn-copy-prompt" data-copy-prompt="${esc(item.prompt)}" title="Copy prompt to clipboard">
                <i class="fa-regular fa-copy"></i> Copy Prompt
              </button>
              <button type="button" class="btn-saved-action btn-load-studio" data-load-type="${isVid ? "video" : "image"}" data-load-prompt="${esc(item.prompt)}" title="Open and populate in Studio">
                <i class="fa-solid fa-arrow-up-right-from-square"></i> Use in Studio
              </button>
              <div class="saved-actions-right">
                <a href="${esc(item.media_url)}" download="${isVid ? "video_ad.mp4" : "image_ad.png"}" class="saved-icon-btn" title="Download asset" target="_blank">
                  <i class="fa-solid fa-download"></i>
                </a>
                <button type="button" class="saved-icon-btn danger" data-delete-id="${esc(item.id)}" title="Delete saved creative">
                  <i class="fa-regular fa-trash-can"></i>
                </button>
              </div>
            </div>
          </div>
        </article>`;
      })
      .join("");

    // Wire preview on hover for videos
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
  }

  // ------------------------------------------------------------ Card Action Handlers
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
      const targetStudio = loadBtn.dataset.loadType; // 'video' | 'image'
      const prompt = loadBtn.dataset.loadPrompt;

      // Switch view
      const navBtn = document.querySelector(`.nav-btn[data-view="${targetStudio}"]`);
      if (navBtn) navBtn.click();

      // Populate textarea
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
        const target = savedItems.find((x) => x.id === id);
        if (target) target.is_favorite = nextFav;
      } catch (_) {}
      return;
    }

    // 4. Delete Item
    const delBtn = e.target.closest("[data-delete-id]");
    if (delBtn) {
      e.stopPropagation();
      const id = delBtn.dataset.deleteId;
      if (!confirm("Remove this saved creative from your library?")) return;

      try {
        const res = await fetch(`/api/saved/${id}`, { method: "DELETE" });
        if (res.ok) {
          savedItems = savedItems.filter((x) => x.id !== id);
          renderGrid();
          if (typeof notify === "function") notify("Creative removed from library", "info");
        }
      } catch (_) {}
      return;
    }

    // 5. Global Save Creative button (.btn-save-creative) on tiles in studios/campaigns
    const saveCreativeBtn = e.target.closest(".btn-save-creative");
    if (saveCreativeBtn) {
      e.stopPropagation();
      const type = saveCreativeBtn.dataset.type || "image";
      const url = saveCreativeBtn.dataset.url;
      const prompt = saveCreativeBtn.dataset.prompt || "";
      const aspect = saveCreativeBtn.dataset.aspect || (type === "video" ? "9:16" : "1:1");
      const title = saveCreativeBtn.dataset.title || (type === "video" ? "Saved Video Creative" : "Saved Image Ad");

      if (!url) return;

      saveCreativeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving';
      saveCreativeBtn.disabled = true;

      try {
        const res = await fetch("/api/saved/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type,
            title,
            prompt,
            media_url: url,
            aspect_ratio: aspect,
          }),
        });
        if (!res.ok) throw new Error("Save request failed");
        saveCreativeBtn.innerHTML = '<i class="fa-solid fa-bookmark" style="color:var(--accent);"></i> Saved';
        if (typeof notify === "function") notify("Creative and prompt saved to library!", "success");
        window.dispatchEvent(new CustomEvent("saved-creatives-updated"));
      } catch (err) {
        saveCreativeBtn.innerHTML = '<i class="fa-regular fa-bookmark"></i> Save Prompt';
        saveCreativeBtn.disabled = false;
        if (typeof notify === "function") notify("Could not save creative", "error");
      }
    }
  });

  // ------------------------------------------------------------ Filters & Search
  function wireFilters() {
    const filterPills = document.querySelectorAll(".saved-filter-pill");
    filterPills.forEach((pill) => {
      pill.addEventListener("click", () => {
        filterPills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        currentFilter = pill.dataset.filter || "all";
        loadSavedItems();
      });
    });

    const searchInput = $("saved_search_input");
    if (searchInput) {
      let debounceTimer = null;
      searchInput.addEventListener("input", (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          searchQuery = e.target.value.trim();
          renderGrid();
        }, 200);
      });
    }
  }

  // ------------------------------------------------------------ View Change Listener
  window.addEventListener("viewchange", (e) => {
    if (e.detail?.view === "saved" || document.querySelector('.nav-btn[data-view="saved"]')?.classList.contains("active")) {
      loadSavedItems();
    }
  });

  window.addEventListener("saved-creatives-updated", () => {
    loadSavedItems();
  });

  // Initial setup
  document.addEventListener("DOMContentLoaded", () => {
    wireFilters();
    if (document.querySelector('.nav-btn[data-view="saved"]')?.classList.contains("active")) {
      loadSavedItems();
    }
  });

  // Export for immediate invocation if already loaded
  window.loadSavedCreatives = loadSavedItems;
})();
