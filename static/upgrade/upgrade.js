// Campaign builder upgrade page: entrances, plan prices from the server, and the "your link next" form.
(function () {
  document.documentElement.classList.add("js");

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ------------------------------------------------------------ entrances (once, as each part enters)
  document.querySelectorAll(".stage, .compare-head, .wall").forEach((group) => {
    group.querySelectorAll(":scope > .reveal, :scope > .cell").forEach((el, i) => el.style.setProperty("--d", `${(i % 4) * 80}ms`));
  });
  const targets = document.querySelectorAll(".reveal, .cell");
  if ("IntersectionObserver" in window && !reduced) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      });
    }, { rootMargin: "0px 0px -10% 0px" });
    targets.forEach((el) => io.observe(el));
  } else {
    targets.forEach((el) => el.classList.add("is-in"));
  }

  // ------------------------------------------------------------ videos play only while on screen
  const videos = document.querySelectorAll("video");
  if (reduced) {
    videos.forEach((v) => { v.removeAttribute("autoplay"); v.pause(); });
  } else if ("IntersectionObserver" in window) {
    const vo = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) e.target.play().catch(() => {});
        else e.target.pause();
      });
    }, { threshold: 0.25 });
    videos.forEach((v) => vo.observe(v));
  }

  // ------------------------------------------------------------ plans and what this visitor already has
  const nf = new Intl.NumberFormat("en-US");
  Promise.all([
    fetch("/api/plans").then((r) => (r.ok ? r.json() : null)).catch(() => null),
    fetch("/api/plan").then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]).then(([plans, mine]) => {
    if (plans && plans.plans) {
      document.querySelectorAll(".plan[data-plan]").forEach((card) => {
        const p = plans.plans[card.dataset.plan];
        if (!p) return;
        card.querySelector(".js-price").textContent = `$${nf.format(p.price_usd_month)}`;
        card.querySelector(".js-credits").textContent = nf.format(p.credits);
      });
    }
    // Someone who already has the campaign builder is sent straight to it
    if (mine && (mine.features || []).includes("campaign_manager")) {
      document.querySelectorAll(".js-upgrade").forEach((a) => {
        a.href = "/#campaign";
        if (a.classList.contains("btn") || a.classList.contains("board-action")) a.textContent = "Open Campaign";
      });
      const form = document.getElementById("close_form");
      form.action = "/";
      form.querySelector("button").textContent = "Build it now";
    }
  });

  // ------------------------------------------------------------ your link next
  // The link waits in this browser; the Campaign tab fills it in once the plan includes it.
  const form = document.getElementById("close_form");
  const input = document.getElementById("close_url");
  const note = document.getElementById("close_note");
  form.addEventListener("submit", (ev) => {
    let url = (input.value || "").trim();
    if (url && !/^https?:\/\//i.test(url)) url = `https://${url}`;
    if (url) {
      let ok = false;
      try { ok = /\./.test(new URL(url).hostname); } catch (e) { ok = false; }
      if (!ok) {
        ev.preventDefault();
        note.hidden = false;
        note.textContent = "That doesn't look like a web address. Try something like https://yourbrand.com/product";
        input.focus();
        return;
      }
      try { localStorage.setItem("pending_brand_url", url); } catch (e) { /* private mode: the link just isn't kept */ }
    }
    if (form.action.endsWith("/")) { // already on a plan with the builder
      ev.preventDefault();
      location.href = "/#campaign";
    }
  });
})();
