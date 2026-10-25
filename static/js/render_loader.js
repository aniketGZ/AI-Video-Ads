// Render loader: a retro space shooter in the ad's aspect ratio.
// While a render runs, invaders drift down a starfield and a ship fires at them. People can steer it
// (pointer, touch, or the arrow keys once the frame has focus; tap or Space for an extra shot); left alone,
// an autopilot plays. When the output lands, revealRendered() hides it behind a grid of blocks and the ship
// sweeps underneath, lasering each column away to uncover the real image or video.
(function () {
  const SPRITES = {
    ship: [
      ".....X.....",
      "....XXX....",
      "....XXX....",
      ".XXXXXXXXX.",
      "XXXXXXXXXXX",
      "XXXXXXXXXXX",
    ],
    crab: [
      [
        "..X.....X..",
        "...X...X...",
        "..XXXXXXX..",
        ".XX.XXX.XX.",
        "XXXXXXXXXXX",
        "X.XXXXXXX.X",
        "X.X.....X.X",
        "...XX.XX...",
      ],
      [
        "..X.....X..",
        "X..X...X..X",
        "X.XXXXXXX.X",
        "XXX.XXX.XXX",
        "XXXXXXXXXXX",
        ".XXXXXXXXX.",
        "..X.....X..",
        ".X.......X.",
      ],
    ],
    squid: [
      [
        "...XX...",
        "..XXXX..",
        ".XXXXXX.",
        "XX.XX.XX",
        "XXXXXXXX",
        "..X..X..",
        ".X.XX.X.",
        "X.X..X.X",
      ],
      [
        "...XX...",
        "..XXXX..",
        ".XXXXXX.",
        "XX.XX.XX",
        "XXXXXXXX",
        ".X.XX.X.",
        "X......X",
        ".X....X.",
      ],
    ],
  };
  const KINDS = [
    { sprite: SPRITES.crab, color: "#e6e6e6", points: 10 },
    { sprite: SPRITES.squid, color: "#a8a8a8", points: 20 },
  ];
  const TILE = "#141414";

  const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const accent = () => getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#4cb3f0";
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  function sizeCanvas(canvas, w, h) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(w * dpr));
    canvas.height = Math.max(1, Math.round(h * dpr));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;
    return ctx;
  }

  // Pixel art: x is the sprite's centre, y its top, u the size of one art pixel
  function drawSprite(ctx, rows, x, y, u, color) {
    const left = Math.round(x - (rows[0].length * u) / 2);
    const top = Math.round(y);
    ctx.fillStyle = color;
    rows.forEach((row, r) => {
      for (let c = 0; c < row.length; c++) if (row[c] === "X") ctx.fillRect(left + c * u, top + r * u, u, u);
    });
  }

  function burst(list, x, y, u, colors, count) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const speed = (40 + Math.random() * 110) * (reduceMotion() ? 0 : 1);
      list.push({ x, y, vx: Math.cos(a) * speed, vy: Math.sin(a) * speed, life: 0.5 + Math.random() * 0.3, age: 0, u, color: colors[i % colors.length] });
    }
  }

  function stepParticles(ctx, list, dt) {
    for (let i = list.length - 1; i >= 0; i--) {
      const p = list[i];
      p.age += dt;
      if (p.age >= p.life) { list.splice(i, 1); continue; }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      ctx.globalAlpha = 1 - p.age / p.life;
      ctx.fillStyle = p.color;
      ctx.fillRect(Math.round(p.x), Math.round(p.y), p.u, p.u);
    }
    ctx.globalAlpha = 1;
  }

  // ------------------------------------------------------------ the game (while rendering)
  function startGame(canvas, { fill }) {
    const frame = canvas.parentElement;
    const hue = accent();
    let ctx;
    let W = 0;
    let H = 0;
    let u = 2;
    let shipY = 0;
    const stars = Array.from({ length: 70 }, () => ({ x: Math.random(), y: Math.random(), z: 1 + Math.floor(Math.random() * 3) }));
    const ship = { x: 0, target: 0 };
    const bullets = [];
    const enemies = [];
    const particles = [];
    const floaters = [];
    const keys = { left: false, right: false };
    let score = 0;
    let lastInput = -Infinity;
    let lastShot = 0;
    let spawnIn = 0.4;
    let clock = 0;
    let hint = 1;
    let last = performance.now();

    const fit = () => {
      const first = !W;
      W = frame.clientWidth;
      H = frame.clientHeight;
      u = Math.max(2, Math.round(W / 85));
      shipY = H - SPRITES.ship.length * u - (fill ? 48 : 12);
      ctx = sizeCanvas(canvas, W, H);
      if (first) { ship.x = W / 2; ship.target = W / 2; }
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(frame);

    const fire = () => {
      if (clock - lastShot < 0.08) return;
      lastShot = clock;
      bullets.push({ x: ship.x, y: shipY - u * 3 });
    };

    // ---- input: steer with the pointer or the arrow keys, tap or Space for an extra shot
    const touched = () => { lastInput = clock; hint = Math.min(hint, 0.99); };
    const pointerX = (e) => clamp(e.clientX - frame.getBoundingClientRect().left, 0, W);
    frame.addEventListener("pointermove", (e) => { ship.target = pointerX(e); touched(); });
    frame.addEventListener("pointerdown", (e) => { ship.target = pointerX(e); touched(); fire(); });
    frame.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "a") keys.left = true;
      else if (e.key === "ArrowRight" || e.key === "d") keys.right = true;
      else if (e.key === " " || e.key === "ArrowUp") fire();
      else return;
      e.preventDefault();
      touched();
    });
    frame.addEventListener("keyup", (e) => {
      if (e.key === "ArrowLeft" || e.key === "a") keys.left = false;
      if (e.key === "ArrowRight" || e.key === "d") keys.right = false;
    });
    frame.addEventListener("blur", () => { keys.left = keys.right = false; });

    // A wave is a small formation (one or two rows) that sways and descends together
    function spawnWave() {
      const rowsInWave = Math.random() < 0.5 ? 1 : 2;
      const spacing = 15 * u;
      const sway = 5 * u;
      const fitCols = Math.max(2, Math.floor((W - 2 * sway - 12 * u) / spacing) + 1);
      const colsInWave = Math.min(fitCols, 3 + Math.floor(Math.random() * 3));
      const left = (W - (colsInWave - 1) * spacing) / 2;
      const phase = Math.random() * Math.PI * 2;
      const speed = H * (0.045 + Math.random() * 0.03) * (reduceMotion() ? 0.5 : 1);
      for (let r = 0; r < rowsInWave; r++) {
        const kind = KINDS[r % KINDS.length];
        for (let c = 0; c < colsInWave; c++) {
          enemies.push({ kind, x: left + c * spacing, y: -(r + 1) * 11 * u, phase, sway, speed });
        }
      }
    }

    function update(dt) {
      clock += dt;
      const idle = clock - lastInput > 2.5;
      // autopilot: line up under the invader closest to the bottom, and only shoot once lined up
      let lined = false;
      if (idle) {
        const threat = enemies.filter((e) => e.y > 0).reduce((a, e) => (!a || e.y > a.y ? e : a), null);
        const tx = threat ? threat.x + Math.sin(threat.phase + clock * 1.6) * threat.sway : W / 2 + Math.sin(clock * 0.8) * W * 0.3;
        ship.target = tx;
        lined = !!threat && Math.abs(ship.x - tx) < 3 * u;
      }
      if (keys.left || keys.right) ship.target = clamp(ship.target + (keys.right - keys.left) * W * 1.1 * dt, 0, W);
      const half = (SPRITES.ship[0].length * u) / 2;
      ship.target = clamp(ship.target, half, W - half);
      ship.x += (ship.target - ship.x) * Math.min(1, dt * 12);

      if (idle ? lined && clock - lastShot > 0.45 : clock - lastShot > 0.32) fire();
      if (hint > 0 && (hint < 1 || clock > 5)) hint = Math.max(0, hint - dt * 1.5);

      spawnIn -= dt;
      if (spawnIn <= 0 && enemies.length < 4) {
        spawnWave();
        spawnIn = 1.2 + Math.random() * 1.2;
      }

      for (let i = bullets.length - 1; i >= 0; i--) {
        const b = bullets[i];
        b.y -= H * 1.5 * dt;
        if (b.y < -4 * u) { bullets.splice(i, 1); continue; }
        const hit = enemies.findIndex((e) => {
          const x = e.x + Math.sin(e.phase + clock * 1.6) * e.sway;
          const w = (e.kind.sprite[0][0].length * u) / 2;
          return Math.abs(b.x - x) <= w && b.y <= e.y + e.kind.sprite[0].length * u && b.y >= e.y;
        });
        if (hit >= 0) {
          const e = enemies[hit];
          const x = e.x + Math.sin(e.phase + clock * 1.6) * e.sway;
          burst(particles, x, e.y + 4 * u, u, [e.kind.color, "#ffffff", hue], 14);
          floaters.push({ x, y: e.y, text: `+${e.kind.points}`, age: 0 });
          score += e.kind.points;
          enemies.splice(hit, 1);
          bullets.splice(i, 1);
        }
      }
      for (let i = enemies.length - 1; i >= 0; i--) {
        enemies[i].y += enemies[i].speed * dt;
        if (enemies[i].y > H) enemies.splice(i, 1); // it slipped past; no game over in a loading screen
      }
      for (let i = floaters.length - 1; i >= 0; i--) {
        floaters[i].age += dt;
        floaters[i].y -= 18 * dt;
        if (floaters[i].age > 0.8) floaters.splice(i, 1);
      }
    }

    function draw(dt) {
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, W, H);
      // three layers of stars, the nearer ones brighter and faster
      for (const s of stars) {
        if (!reduceMotion()) s.y = (s.y + (s.z * 0.025 + 0.01) * dt) % 1;
        ctx.globalAlpha = 0.18 + s.z * 0.2;
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(Math.round(s.x * W), Math.round(s.y * H), s.z > 2 ? 2 : 1, s.z > 2 ? 2 : 1);
      }
      ctx.globalAlpha = 1;
      const step = Math.floor(clock * 2) % 2;
      for (const e of enemies) {
        drawSprite(ctx, e.kind.sprite[step], e.x + Math.sin(e.phase + clock * 1.6) * e.sway, e.y, u, e.kind.color);
      }
      ctx.fillStyle = "#ffffff";
      for (const b of bullets) ctx.fillRect(Math.round(b.x - u / 2), Math.round(b.y), u, u * 3);
      drawSprite(ctx, SPRITES.ship, ship.x, shipY, u, hue);
      stepParticles(ctx, particles, dt);

      const size = Math.max(10, Math.round(u * 4.5));
      ctx.font = `500 ${size}px "JetBrains Mono", ui-monospace, monospace`;
      ctx.textBaseline = "top";
      ctx.textAlign = "center";
      for (const f of floaters) {
        ctx.globalAlpha = 1 - f.age / 0.8;
        ctx.fillStyle = hue;
        ctx.fillText(f.text, f.x, f.y);
      }
      ctx.globalAlpha = 1;
      ctx.textAlign = "left";
      const label = `SCORE ${String(score).padStart(4, "0")}`;
      ctx.globalAlpha = 0.8;
      ctx.fillStyle = "#000";
      ctx.fillRect(4, 4, ctx.measureText(label).width + 8, size + 8);
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#949494";
      ctx.fillText(label, 8, 8);
      if (hint > 0) {
        ctx.globalAlpha = hint;
        ctx.textAlign = "center";
        ctx.fillStyle = "#b4b4b4";
        ctx.fillText("Move to steer · tap to fire", W / 2, H * 0.42);
        ctx.globalAlpha = 1;
      }
    }

    function tick(now) {
      if (!canvas.isConnected) {
        observer.disconnect();
        return; // the render finished and the host's content was replaced
      }
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (W && H) {
        update(dt);
        draw(dt);
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // ------------------------------------------------------------ loader markup
  // Calling it again on the same host only swaps the text, so progress updates keep the game and the timer going.
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
    // The frame's height is capped, so its width follows the ratio
    const size = fill ? "" : `width: min(100%, ${Math.round((340 * w) / h)}px);`;
    host.innerHTML = `
      <div class="render-loader${fill ? " is-fill" : ""}" role="status">
        <div class="rl-frame" style="aspect-ratio: ${w} / ${h}; ${size}" tabindex="0"
             aria-label="Mini game while it renders: steer with the arrow keys, Space to fire"><canvas aria-hidden="true"></canvas></div>
        <div class="rl-meta"><span class="rl-label">${escapeHtml(text)}</span><span class="rl-time" data-start="${Date.now()}">0:00</span></div>
      </div>`;
    startGame(host.querySelector(".rl-frame canvas"), { fill });
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
    const u = Math.max(2, Math.round(box.width / 110));
    const gap = Math.max(2, cw * 0.06);
    const hue = accent();
    const shipH = SPRITES.ship.length * u;
    const baseY = vy + vh - shipH - u * 3;

    // The ship glides left to right under the grid; at each column its laser pops the blocks bottom to top
    const LEAD = 140;
    const PER_COLUMN = 80;
    const PER_BLOCK = 22;
    const beamFor = rows * PER_BLOCK + 90;
    const fireAt = (c) => LEAD + c * PER_COLUMN;
    const popAt = (c, r) => fireAt(c) + (rows - 1 - r) * PER_BLOCK;
    const cleared = popAt(cols - 1, 0) + 120;
    const gone = cleared + 380;
    const popped = Array.from({ length: rows }, () => Array(cols).fill(false));
    const particles = [];
    let shipX = vx + cw / 2;
    const start = performance.now();
    let last = start;

    function frame(now) {
      if (!canvas.isConnected || !el.isConnected) {
        canvas.remove();
        el.style.opacity = "";
        return;
      }
      if (live) paintArt();
      const t = now - start;
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      ctx.clearRect(0, 0, box.width, box.height);
      ctx.fillStyle = "#000";
      ctx.fillRect(vx, vy, vw, vh);

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = vx + c * cw;
          const y = vy + r * ch;
          const at = popAt(c, r);
          if (t >= at) {
            // uncovered: this block's slice of the real picture, seamless with its neighbours
            ctx.drawImage(art, x * dpr, y * dpr, cw * dpr, ch * dpr, x, y, cw, ch);
            if (!popped[r][c]) {
              popped[r][c] = true;
              burst(particles, x + cw / 2, y + ch / 2, u, ["#ffffff", hue, "#6b6b6b"], 6);
            }
            const since = t - at;
            if (since < 160) {
              ctx.globalAlpha = 0.7 * (1 - since / 160);
              ctx.fillStyle = "#ffffff";
              ctx.fillRect(x, y, cw, ch);
              ctx.globalAlpha = 1;
            }
          } else {
            ctx.fillStyle = TILE;
            ctx.fillRect(x + gap / 2, y + gap / 2, cw - gap, ch - gap);
          }
        }
      }

      // the laser: a beam from the ship's nose up to the block it is popping
      for (let c = 0; c < cols; c++) {
        const bt = t - fireAt(c);
        if (bt < 0 || bt > beamFor) continue;
        const reached = Math.min(rows, Math.floor(bt / PER_BLOCK) + 1);
        const topY = vy + (rows - reached) * ch;
        ctx.globalAlpha = bt > beamFor - 90 ? (beamFor - bt) / 90 : 1;
        ctx.fillStyle = hue;
        ctx.fillRect(Math.round(vx + c * cw + cw / 2 - u / 2), topY, u, baseY - topY);
        ctx.globalAlpha = 1;
      }

      stepParticles(ctx, particles, dt);

      // the ship: follows the laser across, then leaves upwards once every block is gone
      const column = clamp(Math.floor((t - LEAD) / PER_COLUMN), 0, cols - 1);
      shipX += (vx + column * cw + cw / 2 - shipX) * Math.min(1, dt * 22);
      const away = Math.max(0, t - cleared) / 1000;
      const shipTop = baseY - away * away * vh * 9;
      if (shipTop > -shipH) drawSprite(ctx, SPRITES.ship, shipX, shipTop, u, hue);

      if (t >= gone && !particles.length) {
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
