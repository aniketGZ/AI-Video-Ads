// Studio composer: the floating prompt dock over the gallery.
// Pill menus wrap the existing segmented groups (studios.js still reads them), prompts grow with their text,
// and the gallery scrolls up to whatever was just generated or picked.
(function () {
  // ------------------------------------------------------------ pill menus
  function closeAll(except) {
    document.querySelectorAll(".pill-menu.open").forEach((menu) => {
      if (menu !== except) setOpen(menu, false);
    });
  }

  function setOpen(menu, open) {
    const pop = menu.querySelector(".pill-pop");
    const pill = menu.querySelector(".pill");
    menu.classList.toggle("open", open);
    pop.hidden = !open;
    pill.setAttribute("aria-expanded", String(open));
    if (open) {
      // keep the menu on screen: open leftwards when it would run off the right edge
      menu.classList.remove("align-right");
      if (pop.getBoundingClientRect().right > window.innerWidth - 8) menu.classList.add("align-right");
      const active = pop.querySelector("button.active") || pop.querySelector("button");
      if (active) active.focus();
    }
  }

  function syncLabel(menu) {
    const active = menu.querySelector(".pill-pop button.active");
    if (active) menu.querySelector(".pill-value").textContent = active.textContent.trim();
  }

  document.querySelectorAll(".pill-menu").forEach((menu) => {
    syncLabel(menu);
    menu.querySelector(".pill").addEventListener("click", () => {
      const open = !menu.classList.contains("open");
      closeAll(menu);
      setOpen(menu, open);
    });
    // runs after the segmented group's own handler, so the active class is already moved
    menu.querySelector(".pill-pop").addEventListener("click", (e) => {
      if (!e.target.closest("button")) return;
      syncLabel(menu);
      setOpen(menu, false);
      menu.querySelector(".pill").focus();
    });
    menu.addEventListener("keydown", (e) => {
      if (!menu.classList.contains("open")) return;
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(menu, false);
        menu.querySelector(".pill").focus();
        return;
      }
      // Up, down, home and end walk the choices, as in any native menu
      const options = Array.from(menu.querySelectorAll(".pill-pop button"));
      const at = options.indexOf(document.activeElement);
      const next = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: options.length - 1 }[e.key];
      if (next === undefined) return;
      e.preventDefault();
      options[(next + options.length) % options.length].focus();
    });
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".pill-menu")) closeAll();
  });
  window.addEventListener("viewchange", () => {
    closeAll();
    document.querySelectorAll(".composer .prompt-list textarea").forEach(grow);
  });

  // ------------------------------------------------------------ prompts grow with their text
  const MAX_PROMPT_HEIGHT = 168;
  function grow(box) {
    if (!box.offsetParent) return; // hidden view: it measures 0, size it when shown
    box.style.height = "auto";
    box.style.height = `${Math.min(box.scrollHeight, MAX_PROMPT_HEIGHT)}px`;
  }
  document.querySelectorAll(".composer .prompt-list").forEach((list) => {
    list.addEventListener("input", (e) => {
      if (e.target.matches("textarea")) grow(e.target);
    });
    // extra prompts are added by studios.js; size them as they arrive
    new MutationObserver(() => list.querySelectorAll("textarea").forEach(grow)).observe(list, { childList: true, subtree: true });
    list.querySelectorAll("textarea").forEach(grow);
  });

  // Ctrl/Cmd + Enter generates from anywhere in the composer
  document.querySelectorAll(".composer").forEach((form) => {
    form.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        form.requestSubmit();
      }
    });
    // what is generated appears at the top of the canvas, so bring it into view
    form.addEventListener("submit", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  });

  // ------------------------------------------------------------ gallery
  document.querySelectorAll(".gallery").forEach((gallery) => {
    // Tiles fade in as their picture arrives; if a thumbnail fails, fall back to the full file
    gallery.addEventListener("load", (e) => e.target.classList?.add("is-loaded"), true);
    gallery.addEventListener("loadeddata", (e) => e.target.classList?.add("is-loaded"), true);
    gallery.addEventListener("error", (e) => {
      const img = e.target;
      const full = img.closest?.("[data-url]")?.dataset.url;
      if (img.tagName === "IMG" && full && !img.src.endsWith(full)) img.src = full;
    }, true);
    // video tiles preview on hover
    gallery.addEventListener("mouseover", (e) => {
      const video = e.target.closest("button")?.querySelector("video");
      if (video) video.play().catch(() => {});
    });
    gallery.addEventListener("mouseout", (e) => {
      const tile = e.target.closest("button");
      if (!tile || tile.contains(e.relatedTarget)) return;
      const video = tile.querySelector("video");
      if (video) { video.pause(); video.currentTime = 0; }
    });
  });

  // ------------------------------------------------------------ starting points on an empty canvas
  document.querySelectorAll("[data-example]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const box = chip.closest(".page-studio").querySelector(".composer textarea[data-prompt]");
      box.value = chip.dataset.example;
      box.dispatchEvent(new Event("input", { bubbles: true }));
      box.focus();
      box.setSelectionRange(box.value.length, box.value.length);
    });
  });
})();
