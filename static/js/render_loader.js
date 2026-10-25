// Render loader: a dot matrix in the ad's aspect ratio with a ripple that loops outwards from the centre.
// The ripple is pure CSS (each dot's delay is its distance from the centre), so it stays smooth while the
// page is busy. When the output lands, revealRendered() grows the same dots into the real image or video,
// centre first, until they merge into the full picture.
(function () {
  const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const easeOut = (k) => 1 - Math.pow(1 - k, 3);

  // Columns per orientation; rows follow the ratio so the dots stay on a square pitch
  function grid(w, h, portraitCols, landscapeCols) {
    const cols = w >= h ? landscapeCols : portraitCols;
    return { cols, rows: Math.max(4, Math.round((cols * h) / w)) };
  }

  // ------------------------------------------------------------ loader markup
  // Calling it again on the same host only swaps the text, so progress updates keep the ripple and the timer going.
  // { ratio: "4:5", fill: true } fills a host that already has the ad's shape (a campaign or batch card).
  window.renderLoader = function (host, text, { ratio = "1:1", fill = false } = {}) {
    if (typeof host === "string") host = document.getElementById(host);
    if (!host) return;
    const existing = host.querySelector(".render-loader");
    if (existing) {
      existing.querySelector(".rl-label").textContent = text;
      return;
    }
    const [w, h] = String(ratio).split(":").map(Number);
    const { cols, rows } = grid(w, h, 16, 22);
    const cx = (cols - 1) / 2;
    const cy = (rows - 1) / 2;
    const far = Math.hypot(cx, cy);
    let dots = "";
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) dots += `<i style="--d:${(Math.hypot(c - cx, r - cy) / far).toFixed(3)}"></i>`;
    }
    // The frame's height is capped, so its width follows the ratio
    const size = fill ? "" : `width: min(100%, ${Math.round((340 * w) / h)}px);`;
    host.innerHTML = `
      <div class="render-loader${fill ? " is-fill" : ""}" role="status">
        <div class="rl-frame" style="aspect-ratio: ${w} / ${h}; ${size}">
          <div class="rl-dots" style="grid-template-columns: repeat(${cols}, 1fr); grid-template-rows: repeat(${rows}, 1fr)" aria-hidden="true">${dots}</div>
        </div>
        <div class="rl-meta"><span class="rl-label">${escapeHtml(text)}</span><span class="rl-time" data-start="${Date.now()}">0:00</span></div>
      </div>`;
    tickRenderTimers();
  };

  let clock = null;
  function tickRenderTimers() {
    const clocks = document.querySelectorAll(".rl-time[data-start]");
    clocks.forEach((el) => {
      const s = Math.floor((Date.now() - Number(el.dataset.start)) / 1000);
      el.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    });
    if (clocks.length && !clock) clock = setInterval(tickRenderTimers, 1000);
    if (!clocks.length && clock) { clearInterval(clock); clock = null; }
  }

  // ------------------------------------------------------------ the reveal (when the output lands)
  function playReveal(el) {
    const box = el.getBoundingClientRect();
    if (!box.width || !box.height || reduceMotion()) {
      el.style.opacity = "";
      return;
    }
    const parent = el.parentElement;
    if (getComputedStyle(parent).position === "static") parent.style.position = "relative";
    const pbox = parent.getBoundingClientRect();
    const canvas = document.createElement("canvas");
    canvas.className = "rl-reveal";
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.left = `${box.left - pbox.left - parent.clientLeft + parent.scrollLeft}px`;
    canvas.style.top = `${box.top - pbox.top - parent.clientTop + parent.scrollTop}px`;
    canvas.style.width = `${box.width}px`;
    canvas.style.height = `${box.height}px`;
    parent.appendChild(canvas);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(box.width * dpr));
    canvas.height = Math.max(1, Math.round(box.height * dpr));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Where the picture really sits inside the element (object-fit contain or cover)
    const nw = el.naturalWidth || el.videoWidth || box.width;
    const nh = el.naturalHeight || el.videoHeight || box.height;
    const fitMode = getComputedStyle(el).objectFit;
    let dw = box.width;
    let dh = box.height;
    if (fitMode === "contain" || fitMode === "cover") {
      const s = (fitMode === "contain" ? Math.min : Math.max)(box.width / nw, box.height / nh);
      dw = nw * s;
      dh = nh * s;
    }
    const dx = (box.width - dw) / 2;
    const dy = (box.height - dh) / 2;
    const vx = Math.max(0, dx);
    const vy = Math.max(0, dy);
    const vw = Math.min(box.width, dw);
    const vh = Math.min(box.height, dh);

    const { cols, rows } = grid(vw, vh, 16, 22);
    const cw = vw / cols;
    const ch = vh / rows;
    const startR = Math.max(1, Math.min(cw, ch) * 0.12); // the size of a resting loader dot
    const fullR = Math.hypot(cw, ch) / 2 + 1; // big enough that neighbours merge with no gaps
    const cx = (cols - 1) / 2;
    const cy = (rows - 1) / 2;
    const far = Math.hypot(cx, cy) || 1;
    const SPREAD = 460; // centre-to-corner delay
    const GROW = 560;
    const cells = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        cells.push({ x: vx + (c + 0.5) * cw, y: vy + (r + 0.5) * ch, delay: (Math.hypot(c - cx, r - cy) / far) * SPREAD });
      }
    }
    const end = SPREAD + GROW;
    const start = performance.now();

    function frame(now) {
      if (!canvas.isConnected || !el.isConnected) {
        canvas.remove();
        el.style.opacity = "";
        return;
      }
      const t = now - start;
      ctx.clearRect(0, 0, box.width, box.height);
      ctx.fillStyle = "#000";
      ctx.fillRect(vx, vy, vw, vh);

      // dots still waiting for the wave stay small and grey, like the loader they replace
      ctx.fillStyle = "rgba(255, 255, 255, 0.28)";
      ctx.beginPath();
      for (const cell of cells) {
        if (t >= cell.delay) continue;
        ctx.moveTo(cell.x + startR, cell.y);
        ctx.arc(cell.x, cell.y, startR, 0, Math.PI * 2);
      }
      ctx.fill();

      // dots the wave has reached grow into windows onto the real picture
      ctx.save();
      ctx.beginPath();
      for (const cell of cells) {
        if (t < cell.delay) continue;
        const k = easeOut(Math.min(1, (t - cell.delay) / GROW));
        const radius = startR + (fullR - startR) * k;
        ctx.moveTo(cell.x + radius, cell.y);
        ctx.arc(cell.x, cell.y, radius, 0, Math.PI * 2);
      }
      ctx.clip();
      ctx.drawImage(el, dx, dy, dw, dh);
      ctx.restore();

      if (t >= end) {
        el.style.opacity = "";
        canvas.remove();
        return;
      }
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  // Hides the finished media at once, then plays the reveal when its first frame is ready.
  window.revealRendered = function (el) {
    if (!el) return;
    el.style.opacity = "0";
    let done = false;
    const go = () => {
      if (done) return;
      done = true;
      requestAnimationFrame(() => playReveal(el));
    };
    const giveUp = () => { done = true; el.style.opacity = ""; };
    if (el.tagName === "VIDEO") {
      if (el.readyState >= 2) go();
      else el.addEventListener("loadeddata", go, { once: true });
    } else if (el.complete && el.naturalWidth) {
      go();
    } else {
      el.addEventListener("load", go, { once: true });
    }
    el.addEventListener("error", giveUp, { once: true });
    setTimeout(() => { if (!done) giveUp(); }, 20000);
  };

  window.tickRenderTimers = tickRenderTimers;
})();
