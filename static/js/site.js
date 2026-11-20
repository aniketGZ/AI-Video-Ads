// Shared by the public pages (landing, pricing, campaign): the bar's rule once content scrolls
// under it, one entrance per part of each section, and videos that only play while on screen.
(function () {
  document.documentElement.classList.add("js");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ------------------------------------------------------------ the bar
  const bar = document.getElementById("bar");
  if (bar) {
    const onScroll = () => bar.classList.toggle("is-scrolled", window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  // ------------------------------------------------------------ entrances: heading, then text, then picture
  const parts = Array.from(document.querySelectorAll(".rv"));
  parts.forEach((el) => {
    const sibs = Array.from(el.parentElement.children).filter((c) => c.classList.contains("rv"));
    el.style.setProperty("--d", `${Math.min(sibs.indexOf(el), 6) * 75}ms`);
  });
  if (!reduced && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add("is-in");
      io.unobserve(e.target);
    }), { rootMargin: "0px 0px -8% 0px" });
    parts.forEach((el) => io.observe(el));
  } else {
    parts.forEach((el) => el.classList.add("is-in"));
  }

  // ------------------------------------------------------------ videos play only while they are seen
  const videos = Array.from(document.querySelectorAll("video[autoplay]"));
  if (reduced) {
    videos.forEach((v) => { v.removeAttribute("autoplay"); v.pause(); });
  } else if ("IntersectionObserver" in window) {
    const vo = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) e.target.play().catch(() => {});
      else e.target.pause();
    }), { threshold: 0.2 });
    videos.forEach((v) => vo.observe(v));
  }

  // ------------------------------------------------------------ a brand link waits for the studio
  // The Campaign tab picks it up from localStorage (core.js), so a visitor never pastes it twice.
  window.keepBrandLink = function (raw) {
    let url = (raw || "").trim();
    if (!url) return { ok: true, url: "" };
    if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
    let ok = false;
    try { ok = /\./.test(new URL(url).hostname); } catch (e) { ok = false; }
    if (ok) { try { localStorage.setItem("pending_brand_url", url); } catch (e) { /* private mode */ } }
    return { ok, url };
  };
})();
