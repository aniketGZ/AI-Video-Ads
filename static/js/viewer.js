// Viewer: images open from where they sit and go back there.
// One spring drives the flight between the tile and the full view, so a close can be caught mid-air and reversed.
// Drag down to dismiss, drag sideways to change item; a flick counts by where it would land, not where it let go.
(function () {
  const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clamp01 = (n) => Math.min(1, Math.max(0, n));

  // ------------------------------------------------------------ spring
  // Apple's two parameters: response (seconds to reach the target) and damping (1 = no overshoot).
  // A new target keeps the current value and velocity, so motion never jumps when it is interrupted.
  function createSpring(value, onUpdate, restDelta) {
    let x = value;
    let v = 0;
    let target = value;
    let stiffness = 0;
    let friction = 0;
    let raf = 0;
    let last = 0;
    let done = null;

    function tick(now) {
      const dt = Math.min((now - last) / 1000, 1 / 30);
      last = now;
      const h = dt / 4;
      for (let i = 0; i < 4; i++) {
        v += (-stiffness * (x - target) - friction * v) * h;
        x += v * h;
      }
      if (Math.abs(x - target) < restDelta && Math.abs(v) < restDelta * 10) {
        x = target;
        v = 0;
        raf = 0;
        onUpdate(x);
        const finish = done;
        done = null;
        if (finish) finish();
        return;
      }
      onUpdate(x);
      raf = requestAnimationFrame(tick);
    }

    return {
      to(next, { response = 0.34, damping = 1, velocity, onRest = null } = {}) {
        target = next;
        stiffness = (2 * Math.PI / response) ** 2;
        friction = (4 * Math.PI * damping) / response;
        if (velocity !== undefined) v = velocity;
        done = onRest;
        if (!raf) {
          last = performance.now();
          raf = requestAnimationFrame(tick);
        }
      },
      stop() {
        cancelAnimationFrame(raf);
        raf = 0;
        done = null;
        v = 0;
      },
      set(next) {
        cancelAnimationFrame(raf);
        raf = 0;
        done = null;
        x = next;
        target = next;
        v = 0;
        onUpdate(x);
      },
    };
  }

  // Where a flick would come to rest if nothing stopped it (px/s to px, the same curve as scroll deceleration)
  const project = (velocity, rate = 0.998) => ((velocity / 1000) * rate) / (1 - rate);
  // The further past an edge, the less the content follows: it slows before it stops
  const rubberband = (over, size, c = 0.55) => (over * size * c) / (size + c * Math.abs(over));

  // ------------------------------------------------------------ dialog
  const dialog = document.createElement("dialog");
  dialog.className = "viewer";
  dialog.setAttribute("aria-label", "Preview");
  dialog.innerHTML = `
    <div class="viewer-scrim"></div>
    <div class="viewer-stage"></div>
    <div class="viewer-bar">
      <button type="button" class="viewer-btn" data-go="-1" aria-label="Previous" title="Previous (←)"><i class="fa-solid fa-arrow-left"></i></button>
      <span class="viewer-count num" aria-live="polite"></span>
      <button type="button" class="viewer-btn" data-go="1" aria-label="Next" title="Next (→)"><i class="fa-solid fa-arrow-right"></i></button>
      <span class="viewer-sep" aria-hidden="true"></span>
      <a class="viewer-btn" data-download download aria-label="Download" title="Download"><i class="fa-solid fa-download"></i><span>Download</span></a>
      <button type="button" class="viewer-btn" data-close aria-label="Close" title="Close (Esc)"><i class="fa-solid fa-xmark"></i></button>
    </div>`;
  document.body.appendChild(dialog);
  const scrim = dialog.querySelector(".viewer-scrim");
  const stage = dialog.querySelector(".viewer-stage");
  const bar = dialog.querySelector(".viewer-bar");
  const count = dialog.querySelector(".viewer-count");
  const download = dialog.querySelector("[data-download]");
  const prev = dialog.querySelector('[data-go="-1"]');
  const next = dialog.querySelector('[data-go="1"]');
  const sep = dialog.querySelector(".viewer-sep");

  let items = [];
  let index = 0;
  let media = null;
  let full = null;    // the on-screen box at rest: { w, h, cx, cy }
  let origin = null;  // the tile it flies from and to: { w, h, cx, cy, r }, or null to fade instead
  let hiddenTile = null;
  let closing = false;

  const pos = { open: 0, x: 0, y: 0 };
  const openSpring = createSpring(0, (v) => { pos.open = v; paint(); }, 0.001);
  const xSpring = createSpring(0, (v) => { pos.x = v; paint(); }, 0.4);
  const ySpring = createSpring(0, (v) => { pos.y = v; paint(); }, 0.4);

  // The tile's own crop and corner radius are part of the flight, so the picture lands exactly on it
  function tileBox(el) {
    if (!el || !el.isConnected || reduceMotion()) return null;
    const r = el.getBoundingClientRect();
    if (!r.width || r.bottom < 0 || r.top > window.innerHeight) return null;
    return { w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2, r: parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0 };
  }

  function paint() {
    if (!media || !full) return;
    const p = pos.open;
    const c = clamp01(p);
    const drop = Math.min(Math.abs(pos.y) / (window.innerHeight * 0.6), 1);
    let scale = 1;
    let x = 0;
    let y = 0;
    let opacity = 1 - (Math.abs(pos.x) / window.innerWidth) * 0.7;
    if (origin) {
      const from = Math.max(origin.w / full.w, origin.h / full.h);
      scale = from + (1 - from) * p;
      x = (origin.cx - full.cx) * (1 - p);
      y = (origin.cy - full.cy) * (1 - p);
      const insetX = ((full.w - origin.w / from) / 2) * (1 - c);
      const insetY = ((full.h - origin.h / from) / 2) * (1 - c);
      const radius = (origin.r / from) * (1 - c) + 14 * c;
      media.style.clipPath = `inset(${insetY.toFixed(2)}px ${insetX.toFixed(2)}px round ${radius.toFixed(2)}px)`;
    } else {
      if (!reduceMotion()) scale = 0.96 + 0.04 * p;
      opacity *= c;
      media.style.clipPath = "inset(0 round 14px)";
    }
    x += pos.x * c;
    y += pos.y * c;
    scale *= 1 - drop * 0.2;
    media.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) scale(${scale.toFixed(4)})`;
    media.style.opacity = opacity;
    const chrome = c * (1 - drop * 0.85);
    scrim.style.opacity = chrome;
    bar.style.opacity = chrome;
  }

  function layout() {
    if (!media) return;
    const nw = media.naturalWidth || media.videoWidth || 1;
    const nh = media.naturalHeight || media.videoHeight || 1;
    const pad = window.innerWidth < 640 ? 8 : 24;
    const room = { w: window.innerWidth - pad * 2, h: window.innerHeight - pad - 76 };
    const k = Math.min(room.w / nw, room.h / nh);
    full = { w: nw * k, h: nh * k, cx: window.innerWidth / 2, cy: pad + room.h / 2 };
    media.style.width = `${full.w}px`;
    media.style.height = `${full.h}px`;
    media.style.left = `${full.cx - full.w / 2}px`;
    media.style.top = `${full.cy - full.h / 2}px`;
    paint();
  }

  function restoreTile() {
    if (hiddenTile) hiddenTile.style.visibility = "";
    hiddenTile = null;
  }

  function show(i) {
    index = i;
    const item = items[i];
    restoreTile();
    if (media) media.remove();
    media = document.createElement(item.type === "video" ? "video" : "img");
    media.className = "viewer-media";
    media.draggable = false;
    if (item.type === "video") {
      Object.assign(media, { controls: true, autoplay: true, loop: true, playsInline: true, src: item.url });
      media.addEventListener("loadedmetadata", layout);
    } else {
      media.alt = item.alt || "";
      media.addEventListener("load", layout);
      // Show what is already on screen at once, then swap in the full file once it has decoded
      media.src = item.thumb || item.url;
      if (item.thumb && item.thumb !== item.url) {
        const shown = media;
        const hires = new Image();
        hires.src = item.url;
        hires.decode().then(() => { if (shown === media) shown.src = item.url; }).catch(() => {});
      }
    }
    stage.appendChild(media);
    if (item.el) {
      item.el.scrollIntoView({ block: "nearest" });
      item.el.style.visibility = "hidden";
      hiddenTile = item.el;
    }
    download.href = item.url;
    download.setAttribute("download", item.download || item.url.split("/").pop() || "");
    const many = items.length > 1;
    prev.hidden = next.hidden = count.hidden = sep.hidden = !many;
    prev.disabled = i === 0;
    next.disabled = i === items.length - 1;
    count.textContent = `${i + 1} of ${items.length}`;
    layout();
  }

  function finishClose() {
    restoreTile();
    if (media) media.remove();
    media = null;
    full = null;
    closing = false;
    if (dialog.open) dialog.close();
  }

  // flick: the release velocity of a drag, handed to the spring so there is no seam between hand and motion
  function close(flick) {
    if (!media || closing) return;
    closing = true;
    origin = tileBox(items[index].el);
    xSpring.stop();
    let velocity = 0;
    if (flick && origin) {
      const reach = pos.y - (origin.cy - full.cy);
      if (Math.abs(reach) > 1) velocity = Math.max(-8, Math.min(0, flick / reach));
    }
    openSpring.to(0, { response: flick ? 0.36 : 0.3, damping: flick ? 0.9 : 1, velocity, onRest: finishClose });
  }

  window.openViewer = function ({ items: list, index: start = 0 }) {
    if (!list.length) return;
    items = list;
    closing = false;
    if (!dialog.open) dialog.showModal();
    xSpring.set(0);
    ySpring.set(0);
    openSpring.stop();
    pos.open = 0;
    origin = tileBox(list[start].el); // measured before the tile hides
    show(start);
    openSpring.to(1, { response: reduceMotion() ? 0.2 : 0.38, damping: 1 });
    dialog.querySelector("[data-close]").focus({ preventScroll: true });
  };

  function go(step) {
    const to = index + step;
    if (to < 0 || to >= items.length) return;
    show(to); // keyboard and buttons: immediate, nothing to wait for
  }

  // ------------------------------------------------------------ bar, keys, backdrop
  bar.addEventListener("click", (e) => {
    const goBtn = e.target.closest("[data-go]");
    if (goBtn) go(Number(goBtn.dataset.go));
    if (e.target.closest("[data-close]")) close();
  });
  stage.addEventListener("click", (e) => { if (e.target === stage) close(); });
  dialog.addEventListener("cancel", (e) => { e.preventDefault(); close(); }); // Esc still flies home
  dialog.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") go(-1);
    if (e.key === "ArrowRight") go(1);
  });
  // The page behind stays where it is, so a close lands on the same tile
  dialog.addEventListener("wheel", (e) => e.preventDefault(), { passive: false });
  window.addEventListener("resize", () => { if (dialog.open) layout(); });

  // ------------------------------------------------------------ drag
  let drag = null;

  stage.addEventListener("pointerdown", (e) => {
    if (!media || e.target !== media || e.button !== 0 || drag) return; // later fingers are ignored
    if (media.tagName === "VIDEO" && e.clientY > media.getBoundingClientRect().bottom - 56) return; // leave its controls alone
    if (media.tagName === "IMG") e.preventDefault();
    // Catches it wherever it is, including mid-flight on the way home
    openSpring.stop();
    xSpring.stop();
    ySpring.stop();
    closing = false;
    media.setPointerCapture(e.pointerId);
    drag = { id: e.pointerId, sx: e.clientX, sy: e.clientY, ox: pos.x, oy: pos.y, axis: null, trail: [{ x: e.clientX, y: e.clientY, t: e.timeStamp }] };
  });

  stage.addEventListener("pointermove", (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    drag.trail.push({ x: e.clientX, y: e.clientY, t: e.timeStamp });
    while (drag.trail.length > 2 && e.timeStamp - drag.trail[0].t > 100) drag.trail.shift();
    const dx = e.clientX - drag.sx;
    const dy = e.clientY - drag.sy;
    if (!drag.axis) {
      if (Math.hypot(dx, dy) < 10) return;
      // Intent is clear: commit to one axis and track from here, with no jump for the distance it took to tell
      drag.axis = Math.abs(dx) > Math.abs(dy) ? "x" : "y";
      drag.sx = e.clientX;
      drag.sy = e.clientY;
      media.classList.add("is-dragging");
      return;
    }
    if (drag.axis === "y") {
      const y = drag.oy + dy;
      pos.y = y < 0 ? rubberband(y, window.innerHeight) : y;
    } else {
      const x = drag.ox + dx;
      const atEdge = (x > 0 && index === 0) || (x < 0 && index === items.length - 1);
      pos.x = atEdge ? rubberband(x, window.innerWidth) : x;
    }
    paint();
  });

  function endDrag(e) {
    if (!drag || e.pointerId !== drag.id) return;
    const { axis, trail } = drag;
    drag = null;
    if (media) media.classList.remove("is-dragging");
    // Only the last moments count: a hand that stopped and then let go has no velocity, however fast it got there
    const recent = trail.filter((s) => e.timeStamp - s.t <= 100);
    const a = recent[0];
    const b = recent[recent.length - 1];
    const dt = recent.length > 1 ? Math.max(b.t - a.t, 1) / 1000 : 0;
    const vx = dt ? (b.x - a.x) / dt : 0;
    const vy = dt ? (b.y - a.y) / dt : 0;
    const rest = () => openSpring.to(1, { response: 0.38, damping: 1 });

    if (axis === "y") {
      if (pos.y + project(vy) > Math.min(180, window.innerHeight * 0.22)) return close(vy);
      rest();
      ySpring.to(0, { response: 0.35, damping: Math.abs(vy) > 200 ? 0.82 : 1, velocity: vy });
    } else if (axis === "x") {
      rest();
      const landing = pos.x + project(vx);
      const step = landing < 0 ? 1 : -1;
      const hasNext = index + step >= 0 && index + step < items.length;
      if (Math.abs(landing) > window.innerWidth * 0.25 && hasNext) {
        xSpring.to(-step * window.innerWidth, {
          response: 0.26,
          velocity: vx,
          onRest: () => {
            show(index + step);
            xSpring.set(step * window.innerWidth * 0.5);
            xSpring.to(0, { response: 0.34, damping: 1 });
          },
        });
      } else {
        xSpring.to(0, { response: 0.35, damping: 0.85, velocity: vx });
      }
    } else {
      rest(); // a tap, or a catch that went nowhere: finish opening
    }
  }
  stage.addEventListener("pointerup", endDrag);
  stage.addEventListener("pointercancel", endDrag);

  // ------------------------------------------------------------ everywhere finished work appears
  const fileName = (el) => el.closest(".ad-card")?.querySelector("a[download]")?.getAttribute("download") || undefined;

  document.querySelectorAll(".gallery").forEach((gallery) => {
    gallery.addEventListener("click", (e) => {
      const tile = e.target.closest("[data-url]");
      if (!tile) return;
      const tiles = Array.from(gallery.querySelectorAll("[data-url]"));
      window.openViewer({
        index: tiles.indexOf(tile),
        items: tiles.map((t) => {
          const img = t.querySelector("img");
          return { url: t.dataset.url, type: img ? "image" : "video", thumb: img && img.complete && img.naturalWidth ? img.currentSrc : undefined, el: t };
        }),
      });
    });
  });

  [["img_result", "img"], ["image_grid", ".media img"], ["batch_results_grid", ".batch-res-thumb img"]].forEach(([id, selector]) => {
    const host = document.getElementById(id);
    if (!host) return;
    host.addEventListener("click", (e) => {
      const shot = e.target.closest(selector);
      if (!shot || shot.hidden) return;
      const shots = Array.from(host.querySelectorAll(selector)).filter((img) => !img.hidden && img.src);
      window.openViewer({
        index: shots.indexOf(shot),
        items: shots.map((img) => ({ url: img.currentSrc || img.src, type: "image", alt: img.alt, download: fileName(img), el: img })),
      });
    });
  });
})();
