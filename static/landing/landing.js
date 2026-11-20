// Landing page: open a row of the run, the four stages, the question index and the link form.
// Everything is readable without this script: the open row, the first stage and every answer are in the HTML.
(function () {
  // ------------------------------------------------------------ the run: pick an ad, see it in the frame
  const list = document.getElementById("run_list");
  const stage = document.getElementById("run_stage");
  if (list && stage) {
    const frame = stage.querySelector(".run-frame");
    const meta = document.getElementById("run_meta");
    const cta = document.getElementById("run_cta");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    list.querySelectorAll(".run-item").forEach((btn) => btn.addEventListener("click", () => {
      list.querySelectorAll(".run-item").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      const d = btn.dataset;
      const title = btn.querySelector("b").textContent;
      frame.classList.toggle("is-tall", d.kind === "video");
      frame.innerHTML = d.kind === "video"
        ? `<video src="${d.src}" poster="${d.poster}" muted loop playsinline ${reduced ? "" : "autoplay"} preload="metadata" aria-label="Woodland video ad: ${title}"></video>`
        : `<img src="${d.src}" width="928" height="1152" alt="Woodland image ad: ${title}">`;
      meta.textContent = d.meta;
      cta.textContent = d.cta;
    }));
  }

  // ------------------------------------------------------------ how a run works: one stage open
  const stages = Array.from(document.querySelectorAll("#stages_row .stage-panel"));
  stages.forEach((panel) => {
    panel.querySelector(".stage-toggle").addEventListener("click", () => {
      stages.forEach((p) => {
        const on = p === panel;
        p.classList.toggle("is-open", on);
        p.querySelector(".stage-toggle").setAttribute("aria-expanded", String(on));
      });
    });
  });

  // ------------------------------------------------------------ questions: hover, click or focus picks one
  const pane = document.getElementById("faq_pane");
  const qs = Array.from(document.querySelectorAll(".faq-q"));
  const pick = (q) => {
    qs.forEach((x) => x.setAttribute("aria-expanded", String(x === q)));
    const answer = q.nextElementSibling ? q.nextElementSibling.textContent : "";
    if (pane && pane.textContent.trim() !== answer.trim()) pane.innerHTML = `<p>${answer}</p>`;
  };
  qs.forEach((q) => {
    q.addEventListener("click", () => pick(q));
    q.addEventListener("focus", () => pick(q));
    q.addEventListener("mouseenter", () => { if (window.matchMedia("(hover: hover)").matches) pick(q); });
  });

  // ------------------------------------------------------------ paste your link (hero and close)
  document.querySelectorAll(".js-link-form").forEach((form) => {
    const input = form.querySelector("input");
    const note = form.parentElement.querySelector(".link-note");
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const kept = window.keepBrandLink ? window.keepBrandLink(input.value) : { ok: true };
      if (!kept.ok) {
        if (note) note.textContent = "That doesn't look like a web address. Try yourbrand.com/product";
        input.focus();
        return;
      }
      location.href = "/app#campaign";
    });
  });
})();
