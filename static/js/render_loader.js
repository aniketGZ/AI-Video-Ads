// Render loader: a Tetris well in the ad's aspect ratio.
// While a render runs, pieces fall, lock in and clear full rows. When the output lands, revealRendered()
// drops pieces that each carry their slice of the real image or video until the frame is full, then hands
// over to the media element itself.
(function () {
  const SHAPES = [
    [[0, 0], [1, 0], [2, 0], [3, 0]], // I
    [[0, 0], [1, 0], [0, 1], [1, 1]], // O
    [[0, 0], [1, 0], [2, 0], [1, 1]], // T
    [[1, 0], [2, 0], [0, 1], [1, 1]], // S
    [[0, 0], [1, 0], [1, 1], [2, 1]], // Z
    [[0, 0], [0, 1], [0, 2], [1, 2]], // L
    [[1, 0], [1, 1], [1, 2], [0, 2]], // J
  ];
  const SMALL = [[[0, 0], [1, 0]], [[0, 0], [0, 1]], [[0, 0]]]; // fillers for the reveal's last gaps

  // Every distinct rotation of a shape, normalised to start at 0,0 (y grows downwards)
  function rotations(cells) {
    const out = [];
    const seen = new Set();
    let cur = cells;
    for (let r = 0; r < 4; r++) {
      const minX = Math.min(...cur.map((c) => c[0]));
      const minY = Math.min(...cur.map((c) => c[1]));
      const norm = cur.map(([x, y]) => [x - minX, y - minY]).sort((a, b) => a[1] - b[1] || a[0] - b[0]);
      const key = norm.join(";");
      if (!seen.has(key)) { seen.add(key); out.push(norm); }
      cur = cur.map(([x, y]) => [-y, x]);
    }
    return out;
  }
  const PIECES = SHAPES.map(rotations);
  const ALL_ROTATIONS = PIECES.flat();

  const SHADES = ["#383838", "#404040", "#474747", "#3c3c3c"];
  const EMPTY = "#161616";
  const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const accent = () => getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#4cb3f0";
  const height = (cells) => Math.max(...cells.map((c) => c[1])) + 1;
  const shuffle = (list) => list.map((v) => [Math.random(), v]).sort((a, b) => a[0] - b[0]).map((p) => p[1]);

  function sizeCanvas(canvas, w, h) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(w * dpr));
    canvas.height = Math.max(1, Math.round(h * dpr));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  }

  function block(ctx, x, y, w, h, r) {
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x, y, w, h, r);
    else ctx.rect(x, y, w, h);
    ctx.fill();
  }

  // ------------------------------------------------------------ the well (while rendering)
  function startWell(canvas, cols, rows) {
    const frame = canvas.parentElement;
    const board = Array.from({ length: rows }, () => Array(cols).fill(null));
    const hue = accent();
    let ctx;
    let W = 0;
    let H = 0;
    let piece = null;
    let clearing = null;
    let wait = 0;
    let last = performance.now();

    const fit = () => {
      W = frame.clientWidth;
      H = frame.clientHeight;
      ctx = sizeCanvas(canvas, W, H);
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(frame);

    const fits = (cells, x, y) => cells.every(([cx, cy]) => {
      const gx = x + cx;
      const gy = y + cy;
      return gx >= 0 && gx < cols && gy < rows && (gy < 0 || !board[gy][gx]);
    });

    const restY = (cells, x) => {
      let y = -height(cells);
      while (fits(cells, x, y + 1)) y++;
      return y;
    };

    // A small placement brain: sit low, avoid holes, finish rows; a little noise keeps it from looking scripted
    function score(cells, x, y) {
      const own = new Set(cells.map(([cx, cy]) => `${x + cx},${y + cy}`));
      let s = 0;
      for (const [cx, cy] of cells) {
        const gx = x + cx;
        const gy = y + cy;
        s += gy * 2;
        if (gy + 1 < rows && !board[gy + 1][gx] && !own.has(`${gx},${gy + 1}`)) s -= 7;
      }
      for (const r of new Set(cells.map(([, cy]) => y + cy))) {
        if (board[r].every((v, c) => v || own.has(`${c},${r}`))) s += 12;
      }
      return s + Math.random() * 2;
    }

    function spawn() {
      const rots = PIECES[Math.floor(Math.random() * PIECES.length)];
      let best = null;
      for (const cells of rots) {
        const w = Math.max(...cells.map((c) => c[0])) + 1;
        for (let x = 0; x <= cols - w; x++) {
          const y = restY(cells, x);
          if (cells.some(([, cy]) => y + cy < 0)) continue; // would stick out of the top
          const s = score(cells, x, y);
          if (!best || s > best.s) best = { cells, x, y, s };
        }
      }
      if (!best) {
        // The well topped out: wash every row away and start again
        clearing = { rows: board.map((_, r) => r), t: 0 };
        return;
      }
      piece = { ...best, fy: -height(best.cells), v: 7, shade: SHADES[Math.floor(Math.random() * SHADES.length)] };
    }

    function lock() {
      const now = performance.now();
      for (const [cx, cy] of piece.cells) board[piece.y + cy][piece.x + cx] = { shade: piece.shade, t: now };
      piece = null;
      wait = reduceMotion() ? 0.5 : 0.06;
      const full = board.map((row, r) => (row.every(Boolean) ? r : -1)).filter((r) => r >= 0);
      if (full.length) clearing = { rows: full, t: 0 };
    }

    function draw(now) {
      const cw = W / cols;
      const ch = H / rows;
      const gap = Math.max(2, cw * 0.08);
      const radius = Math.min(cw, ch) * 0.16;
      ctx.clearRect(0, 0, W, H);
      for (let r = 0; r < rows; r++) {
        const clearingRow = clearing && clearing.rows.includes(r);
        for (let c = 0; c < cols; c++) {
          const cell = board[r][c];
          let x = c * cw + gap / 2;
          let w = cw - gap;
          if (clearingRow && cell) {
            // The cleared row flashes white and pinches towards its centre
            const k = Math.min(1, clearing.t / 0.3);
            const shrink = w * k * 0.9;
            x += shrink / 2;
            w -= shrink;
            ctx.fillStyle = "#ffffff";
            ctx.globalAlpha = 1 - k;
            block(ctx, x, r * ch + gap / 2, w, ch - gap, radius);
            ctx.globalAlpha = 1;
            continue;
          }
          ctx.fillStyle = cell ? cell.shade : EMPTY;
          block(ctx, x, r * ch + gap / 2, w, ch - gap, radius);
          if (cell) {
            // A freshly locked block cools from the accent to its grey
            const age = (now - cell.t) / 450;
            if (age < 1) {
              ctx.globalAlpha = 1 - age;
              ctx.fillStyle = hue;
              block(ctx, x, r * ch + gap / 2, w, ch - gap, radius);
              ctx.globalAlpha = 1;
            }
          }
        }
      }
      if (piece) {
        ctx.fillStyle = hue;
        for (const [cx, cy] of piece.cells) {
          block(ctx, (piece.x + cx) * cw + gap / 2, (piece.fy + cy) * ch + gap / 2, cw - gap, ch - gap, radius);
        }
      }
    }

    function tick(now) {
      if (!canvas.isConnected) {
        observer.disconnect();
        return; // the host's content was replaced
      }
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (clearing) {
        clearing.t += dt;
        if (clearing.t >= 0.3) {
          for (const r of clearing.rows.sort((a, b) => a - b)) {
            board.splice(r, 1);
            board.unshift(Array(cols).fill(null));
          }
          clearing = null;
        }
      } else if (!piece) {
        wait -= dt;
        if (wait <= 0) spawn();
      } else if (reduceMotion()) {
        piece.fy = piece.y;
        lock();
      } else {
        piece.v += 38 * dt; // gravity, in rows per second squared
        piece.fy += piece.v * dt;
        if (piece.fy >= piece.y) {
          piece.fy = piece.y;
          lock();
        }
      }
      if (W && H) draw(now);
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // ------------------------------------------------------------ loader markup
  // Calling it again on the same host only swaps the text, so progress updates keep the well and the timer going.
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
    const cols = w >= h ? 10 : 8;
    const rows = Math.max(4, Math.round((cols * h) / w));
    // The frame's height is capped, so its width follows the ratio
    const size = fill ? "" : `width: min(100%, ${Math.round((340 * w) / h)}px);`;
    host.innerHTML = `
      <div class="render-loader${fill ? " is-fill" : ""}" role="status">
        <div class="rl-frame" style="aspect-ratio: ${w} / ${h}; ${size}"><canvas aria-hidden="true"></canvas></div>
        <div class="rl-meta"><span class="rl-label">${escapeHtml(text)}</span><span class="rl-time" data-start="${Date.now()}">0:00</span></div>
      </div>`;
    startWell(host.querySelector(".rl-frame canvas"), cols, rows);
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
  // Cover the visible area with pieces, bottom row first, each resting on what is already placed.
  function tile(cols, rows) {
    const filled = Array.from({ length: rows }, () => Array(cols).fill(false));
    const pieces = [];
    const canPlace = (cells, x, y) => cells.every(([cx, cy]) => {
      const gx = x + cx;
      const gy = y + cy;
      if (gx < 0 || gx >= cols || gy < 0 || gy >= rows || filled[gy][gx]) return false;
      // supported: the cell below is the floor, already filled, or part of this piece
      const below = gy + 1;
      return below >= rows || filled[below][gx] || cells.some(([ox, oy]) => x + ox === gx && y + oy === below);
    });
    for (let r = rows - 1; r >= 0; r--) {
      for (let c = 0; c < cols; c++) {
        if (filled[r][c]) continue;
        let placed = null;
        for (const set of [shuffle(ALL_ROTATIONS), SMALL]) {
          for (const cells of set) {
            // anchor the shape's bottom-left cell on (c, r)
            const bottom = height(cells) - 1;
            const anchor = cells.filter(([, cy]) => cy === bottom).sort((a, b) => a[0] - b[0])[0];
            const x = c - anchor[0];
            const y = r - anchor[1];
            if (canPlace(cells, x, y)) { placed = { cells, x, y }; break; }
          }
          if (placed) break;
        }
        for (const [cx, cy] of placed.cells) filled[placed.y + cy][placed.x + cx] = true;
        pieces.push(placed);
      }
    }
    return pieces;
  }

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
    const ctx = sizeCanvas(canvas, box.width, box.height);

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

    // One scaled copy of the picture to slice from (redrawn every frame for a playing video)
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const art = document.createElement("canvas");
    art.width = Math.max(1, Math.round(box.width * dpr));
    art.height = Math.max(1, Math.round(box.height * dpr));
    const actx = art.getContext("2d");
    const paintArt = () => {
      actx.clearRect(0, 0, art.width, art.height);
      actx.drawImage(el, dx * dpr, dy * dpr, dw * dpr, dh * dpr);
    };
    paintArt();
    const live = el.tagName === "VIDEO";

    const cols = vw >= vh ? 12 : 9;
    const rows = Math.max(4, Math.round((cols * vh) / vw));
    const cw = vw / cols;
    const ch = vh / rows;
    const pieces = tile(cols, rows);
    const stagger = Math.max(14, Math.min(45, 900 / pieces.length));
    const fall = 340;
    const settle = 220;
    const lastLand = (pieces.length - 1) * stagger + fall;
    const gap0 = Math.max(2, cw * 0.07);
    const hue = accent();
    const start = performance.now();

    function slice(c, r, offsetY, gap) {
      const x = vx + c * cw + gap / 2;
      const y = vy + r * ch + gap / 2;
      const w = cw - gap;
      const h = ch - gap;
      ctx.drawImage(art, x * dpr, y * dpr, w * dpr, h * dpr, x, y + offsetY, w, h);
    }

    function frame(now) {
      if (!canvas.isConnected || !el.isConnected) {
        canvas.remove();
        el.style.opacity = "";
        return;
      }
      if (live) paintArt();
      const t = now - start;
      const merge = Math.min(1, Math.max(0, (t - lastLand) / settle));
      const gap = gap0 * (1 - merge);
      ctx.clearRect(0, 0, box.width, box.height);
      // the empty well the pieces fall into
      if (merge < 1) {
        ctx.globalAlpha = 1 - merge;
        ctx.fillStyle = EMPTY;
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) ctx.fillRect(vx + c * cw + gap / 2, vy + r * ch + gap / 2, cw - gap, ch - gap);
        }
        ctx.globalAlpha = 1;
      }
      pieces.forEach((p, i) => {
        const pt = t - i * stagger;
        if (pt <= 0) return;
        const k = Math.min(1, pt / fall);
        // fall under gravity from just above the frame
        const drop = (p.y + height(p.cells)) * ch + vy;
        const offsetY = -drop * (1 - k * k);
        for (const [cx, cy] of p.cells) slice(p.x + cx, p.y + cy, offsetY, gap);
        // landing flash in the accent, fading over 260ms
        const since = pt - fall;
        if (since >= 0 && since < 260) {
          ctx.globalAlpha = 0.55 * (1 - since / 260);
          ctx.fillStyle = hue;
          for (const [cx, cy] of p.cells) {
            ctx.fillRect(vx + (p.x + cx) * cw + gap / 2, vy + (p.y + cy) * ch + gap / 2, cw - gap, ch - gap);
          }
          ctx.globalAlpha = 1;
        }
      });
      if (t >= lastLand + settle + 260) {
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
