// Render loader: a pixel matrix in the ad's aspect ratio, coloured by the spectrum, with a ripple that loops
// outwards from the centre. The ripple is pure CSS (each pixel's delay is its distance from the centre), so it
// stays smooth while the page is busy. When the output lands, revealRendered() turns the same pixels into a
// mosaic of the real image or video, centre first, and then sharpens each tile into the full picture.
(function () {
  const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const easeOut = (k) => 1 - Math.pow(1 - k, 3);

  // The spectrum left to right, a touch of the next hue further down, so the matrix reads as one gradient
  const STOPS = [[0, [20, 83, 250]], [0.3, [27, 174, 254]], [0.52, [190, 198, 250]], [0.78, [245, 84, 74]], [1, [253, 176, 134]]];
  function spectrumAt(k) {
    const x = Math.min(1, Math.max(0, k));
    let i = 1;
    while (i < STOPS.length - 1 && x > STOPS[i][0]) i++;
    const [p0, c0] = STOPS[i - 1];
    const [p1, c1] = STOPS[i];
    const f = (x - p0) / (p1 - p0);
    return `rgb(${c0.map((v, n) => Math.round(v + (c1[n] - v) * f)).join(",")})`;
  }
  const hueOf = (c, r, cols, rows) => spectrumAt((c / Math.max(1, cols - 1)) * 0.8 + (r / Math.max(1, rows - 1)) * 0.2);

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
      for (let c = 0; c < cols; c++) dots += `<i style="--d:${(Math.hypot(c - cx, r - cy) / far).toFixed(3)};--c:${hueOf(c, r, cols, rows)}"></i>`;
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
    const startR = Math.max(1, Math.min(cw, ch) * 0.1); // half the side of a resting loader pixel
    const cx = (cols - 1) / 2;
    const cy = (rows - 1) / 2;
    const far = Math.hypot(cx, cy) || 1;
    const SPREAD = 460; // centre-to-corner delay
    const TILE = 240;   // a pixel closes into a solid mosaic tile
    const HOLD = 160;   // the mosaic stands
    const GROW = 420;   // the tile opens into the real picture
    const cells = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        cells.push({ x: vx + (c + 0.5) * cw, y: vy + (r + 0.5) * ch, delay: (Math.hypot(c - cx, r - cy) / far) * SPREAD, hue: hueOf(c, r, cols, rows) });
      }
    }
    const end = SPREAD + TILE + HOLD + GROW;
    // the picture at one pixel per cell, stretched back up without smoothing: the mosaic
    const tiny = document.createElement("canvas");
    tiny.width = cols;
    tiny.height = rows;
    const tctx = tiny.getContext("2d");
    tctx.imageSmoothingQuality = "high";
    tctx.drawImage(el, (vx - dx) * (nw / dw), (vy - dy) * (nh / dh), vw * (nw / dw), vh * (nh / dh), 0, 0, cols, rows);
    const square = (cell, kx, ky) => ctx.rect(cell.x - kx, cell.y - ky, kx * 2, ky * 2);
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

      // pixels still waiting for the wave keep the loader's colours
      for (const cell of cells) {
        if (t >= cell.delay + TILE) continue;
        ctx.fillStyle = cell.hue;
        ctx.globalAlpha = t < cell.delay ? 0.4 : 1;
        ctx.fillRect(cell.x - startR, cell.y - startR, startR * 2, startR * 2);
      }
      ctx.globalAlpha = 1;

      // pixels the wave has reached close into flat tiles of the picture
      const open = (from, dur) => {
        ctx.save();
        ctx.beginPath();
        for (const cell of cells) {
          const at = t - cell.delay - from;
          if (at < 0) continue;
          const k = easeOut(Math.min(1, at / dur));
          square(cell, (startR + (cw / 2 + 0.5 - startR) * k), (startR + (ch / 2 + 0.5 - startR) * k));
        }
        ctx.clip();
      };
      open(0, TILE);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(tiny, vx, vy, vw, vh);
      ctx.restore();

      // then each tile opens into the real picture
      open(TILE + HOLD, GROW);
      ctx.imageSmoothingEnabled = true;
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
