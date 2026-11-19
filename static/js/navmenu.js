// Hover menus under the top bar. Hovering a tab shows what that studio can do; each item
// opens the studio already set up for it (a model, a style, a mode). Clicking the tab itself
// still just switches to it. Keyboard: ArrowDown on a tab opens its menu, Escape closes it.
(function () {
  const canHover = window.matchMedia("(hover: hover) and (min-width: 961px)");
  const tabs = Array.from(document.querySelectorAll(".nav-btn[data-menu]"));
  if (!tabs.length) return;

  let openTab = null;
  let openTimer = 0;
  let closeTimer = 0;

  const menuOf = (tab) => document.getElementById(tab.dataset.menu);

  tabs.forEach((tab) => {
    tab.setAttribute("aria-controls", tab.dataset.menu);
    tab.setAttribute("aria-expanded", "false");
  });

  function open(tab, { focusFirst = false } = {}) {
    clearTimeout(closeTimer);
    if (openTab && openTab !== tab) close({ now: true });
    const menu = menuOf(tab);
    if (!menu) return;
    menu.hidden = false;
    tab.setAttribute("aria-expanded", "true");
    openTab = tab;
    if (focusFirst) menu.querySelector("button, a")?.focus();
  }

  function close({ now = false, refocus = false } = {}) {
    clearTimeout(openTimer);
    const run = () => {
      if (!openTab) return;
      const tab = openTab;
      menuOf(tab).hidden = true;
      tab.setAttribute("aria-expanded", "false");
      openTab = null;
      if (refocus) tab.focus();
    };
    clearTimeout(closeTimer);
    if (now) run(); else closeTimer = setTimeout(run, 160);
  }

  // ---------------------------------------------------------------- pointer
  tabs.forEach((tab) => {
    const menu = menuOf(tab);
    tab.addEventListener("mouseenter", () => {
      if (!canHover.matches) return;
      clearTimeout(closeTimer);
      clearTimeout(openTimer);
      // a short pause so sweeping across the bar doesn't flash every menu
      openTimer = setTimeout(() => open(tab), openTab ? 0 : 90);
    });
    tab.addEventListener("mouseleave", () => { clearTimeout(openTimer); close(); });
    tab.addEventListener("click", () => close({ now: true }));
    menu.addEventListener("mouseenter", () => clearTimeout(closeTimer));
    menu.addEventListener("mouseleave", () => close());

    // ---------------------------------------------------------------- keyboard
    tab.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" && canHover.matches) {
        e.preventDefault();
        open(tab, { focusFirst: true });
      } else if (e.key === "Escape") {
        close({ now: true });
      }
    });
    menu.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { e.preventDefault(); close({ now: true, refocus: true }); }
    });
    menu.addEventListener("focusout", (e) => {
      const to = e.relatedTarget;
      if (to && (menu.contains(to) || to === tab)) return;
      close({ now: true });
    });
  });

  canHover.addEventListener?.("change", () => close({ now: true }));

  // ---------------------------------------------------------------- what each item does
  document.addEventListener("click", (e) => {
    const upgrade = e.target.closest("[data-upgrade]");
    if (upgrade) {
      close({ now: true });
      openUpgradeDialog();
      return;
    }
    const item = e.target.closest(".mega [data-go]");
    if (!item) return;
    close({ now: true });
    showView(item.dataset.go, { push: true });
    const pick = item.dataset.pick && document.querySelector(item.dataset.pick);
    if (pick && !pick.classList.contains("active")) pick.click();
    const clickTarget = item.dataset.click && document.querySelector(item.dataset.click);
    if (clickTarget) clickTarget.click();
    const focus = item.dataset.focus && document.querySelector(item.dataset.focus);
    if (focus) {
      focus.focus({ preventScroll: true });
      focus.scrollIntoView({ block: "center", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    } else if (pick) {
      // Show what changed: the composer that holds the picked option
      pick.closest(".composer, form")?.scrollIntoView({ block: "nearest" });
    }
  });
})();
