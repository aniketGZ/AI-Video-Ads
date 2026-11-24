// The spectrum: Ad Studio's one moving surface. A ribbon of electric blue, cyan, lavender and coral
// flows on near-black, and part of it breaks into square pixels, the way a frame does while it renders.
//
//   <div class="spectrum" data-spectrum="valley" aria-hidden="true"></div>
//
// Shapes: valley (ribbons rise at both sides, dark in the middle for words), corner (light from one
// corner; data-flip="x", "y" or "xy" moves it), band (left to right), horizon (a glow along the bottom,
// transparent above). One WebGL context draws every surface on the page and copies each into its own
// canvas, so any number of them costs one context. Surfaces off screen, hidden tabs and reduced motion
// stop the clock; without WebGL the CSS background on .spectrum stays.
(function () {
  const SHAPES = { valley: 0, corner: 1, band: 2, horizon: 3 };
  const FRAME_MS = 1000 / 32;
  const ENTRANCE_MS = 1500;
  const reducedQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

  const VERT = "attribute vec2 p; void main() { gl_Position = vec4(p, 0.0, 1.0); }";
  const FRAG = `
    precision highp float;
    uniform vec2 uRes;      // drawn size in pixels
    uniform float uTime;
    uniform float uCell;    // mosaic cell in drawn pixels
    uniform float uIn;      // entrance, 0 to 1
    uniform int uShape;
    uniform vec2 uFlip;
    uniform vec3 uPointer;  // x, y in drawn pixels, strength

    const vec3 GROUND = vec3(0.016, 0.004, 0.031);
    const vec3 INDIGO = vec3(0.020, 0.075, 0.400);
    const vec3 BLUE   = vec3(0.078, 0.325, 0.980);
    const vec3 AZURE  = vec3(0.106, 0.600, 0.996);
    const vec3 CYAN   = vec3(0.240, 0.860, 1.000);
    const vec3 ICE    = vec3(0.815, 0.820, 0.925);
    const vec3 VIOLET = vec3(0.510, 0.294, 0.800);
    const vec3 CORAL  = vec3(0.960, 0.330, 0.270);
    const vec3 AMBER  = vec3(0.992, 0.690, 0.525);

    float hash(vec2 p) {
      p = fract(p * vec2(123.34, 456.21));
      p += dot(p, p + 45.32);
      return fract(p.x * p.y);
    }
    float noise(vec2 p) {
      vec2 i = floor(p), f = fract(p);
      f = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
    }
    // a bell with a different width above and below its centre
    float bell(float d, float up, float down) {
      float w = d > 0.0 ? up : down;
      return exp(-(d * d) / (w * w));
    }

    vec3 valley(vec2 uv) {
      float x = uv.x * 2.0 - 1.0;
      x += 0.045 * sin(uv.y * 2.6 + uTime * 0.23);
      float s = abs(x);
      float h = uv.y;
      float w = 0.030 * sin(x * 3.1 + uTime * 0.37) + 0.022 * sin(x * 5.7 - uTime * 0.29);
      float a = 0.10 + 0.62 * pow(s, 2.3) + w;
      float b = 0.02 + 0.40 * pow(s, 2.5) + w * 0.8;
      float c = -0.02 + 0.19 * s * s + w * 0.5;
      vec3 col = GROUND;
      col += INDIGO * bell(h - a, 0.20, 0.24) * 0.75;
      col = mix(col, BLUE, bell(h - a, 0.075, mix(0.20, 0.085, s)) * 0.96);
      col = mix(col, VIOLET, bell(h - b - 0.09, 0.05, 0.08) * smoothstep(0.30, 0.60, s) * (1.0 - smoothstep(0.7, 0.95, s)) * 0.75);
      col = mix(col, CORAL, bell(h - b - 0.062, 0.040, 0.045) * smoothstep(0.44, 0.72, s) * (1.0 - 0.55 * smoothstep(0.84, 1.0, s)));
      col = mix(col, ICE, bell(h - b, 0.052, 0.070) * smoothstep(0.34, 0.76, s) * 0.96);
      float shore = smoothstep(c + 0.11, c - 0.09, h);
      col = mix(col, mix(BLUE, AZURE, smoothstep(0.05, 0.55, s)), shore);
      col = mix(col, CYAN, smoothstep(c + 0.02, c - 0.16, h) * mix(0.25, 0.95, s));
      return col;
    }

    vec3 corner(vec2 uv) {
      vec2 q = uv;
      float wave = 0.055 * sin(q.x * 4.2 + uTime * 0.40) + 0.045 * sin(q.y * 3.6 - uTime * 0.33);
      float d = length(vec2(q.x * 1.02, q.y * 0.94)) + wave;
      vec3 col = CYAN;
      col = mix(col, vec3(0.44, 0.74, 1.0), smoothstep(0.04, 0.26, d));
      col = mix(col, vec3(0.69, 0.69, 0.96), smoothstep(0.22, 0.48, d));
      col = mix(col, VIOLET, smoothstep(0.42, 0.60, d));
      col = mix(col, CORAL, smoothstep(0.40, 0.58, d) * smoothstep(0.30, 0.72, q.x) * 0.9);
      col = mix(col, BLUE, smoothstep(0.50, 0.64, d) * (1.0 - smoothstep(0.28, 0.62, q.x)));
      col = mix(col, INDIGO, smoothstep(0.58, 0.76, d));
      return mix(col, GROUND, smoothstep(0.66, 1.0, d));
    }

    vec3 band(vec2 uv) {
      float x = uv.x + 0.06 * sin(uv.y * 3.2 + uTime * 0.36) + 0.03 * sin(uv.y * 7.0 - uTime * 0.5);
      vec3 col = mix(GROUND, INDIGO, smoothstep(-0.05, 0.16, x));
      col = mix(col, BLUE, smoothstep(0.12, 0.36, x));
      col = mix(col, AZURE, smoothstep(0.36, 0.52, x));
      col = mix(col, vec3(0.45, 0.83, 1.0), smoothstep(0.50, 0.64, x));
      col = mix(col, ICE, smoothstep(0.62, 0.78, x));
      col = mix(col, AMBER, smoothstep(0.76, 0.90, x));
      return mix(col, CORAL, smoothstep(0.86, 1.04, x));
    }

    vec3 wheel(float x) {
      vec3 c = mix(vec3(0.05, 0.10, 0.75), vec3(0.13, 0.75, 0.79), smoothstep(0.08, 0.26, x));
      c = mix(c, BLUE, smoothstep(0.28, 0.42, x));
      c = mix(c, vec3(0.50, 0.04, 0.45), smoothstep(0.42, 0.54, x));
      c = mix(c, vec3(0.85, 0.07, 0.36), smoothstep(0.52, 0.64, x));
      c = mix(c, vec3(0.93, 0.48, 0.35), smoothstep(0.66, 0.78, x));
      return mix(c, vec3(0.94, 0.76, 0.45), smoothstep(0.76, 0.90, x));
    }
    vec3 horizon(vec2 uv) {
      float m = 0.05 * sin(uTime * 0.31);
      float n = 0.05 * sin(uTime * 0.23 + 2.0);
      float env = 0.02 + 0.40 * exp(-pow((uv.x - 0.62 - m) / 0.17, 2.0)) + 0.24 * exp(-pow((uv.x - 0.31 - n) / 0.15, 2.0));
      env *= 0.90 + 0.10 * sin(uTime * 0.6 + uv.x * 6.0);
      float i = exp(-max(uv.y, 0.0) / env * 1.7) * smoothstep(0.0, 0.12, uv.x) * smoothstep(1.0, 0.86, uv.x);
      return wheel(uv.x) * i;
    }

    vec3 paint(vec2 uv) {
      uv = mix(uv, 1.0 - uv, uFlip);
      if (uShape == 0) return valley(uv);
      if (uShape == 1) return corner(uv);
      if (uShape == 2) return band(uv);
      return horizon(uv);
    }

    // how strongly a cell wants to be a pixel
    float mosaic(vec2 cell, vec2 cuv) {
      vec2 f = mix(cuv, 1.0 - cuv, uFlip);
      float grain = noise(cell * 0.22 + vec2(uTime * 0.10, -uTime * 0.07)) - 0.5;
      float m;
      if (uShape == 0) m = smoothstep(0.58, 0.92, f.x) + 0.62 * smoothstep(0.20, 0.0, f.x) * smoothstep(0.42, 0.05, f.y);
      else if (uShape == 1) m = smoothstep(0.30, 0.80, f.x + f.y * 0.35);
      else if (uShape == 2) m = smoothstep(0.50, 0.86, f.x);
      else m = smoothstep(0.50, 0.68, f.x) * smoothstep(0.96, 0.84, f.x) * 1.1;
      m += grain * 0.75;
      vec2 away = (cell + 0.5) * uCell - uPointer.xy;
      m += uPointer.z * 1.2 * exp(-dot(away, away) / (uCell * uCell * 22.0));
      m += (1.0 - uIn) * 1.4;
      return m;
    }

    void main() {
      vec2 px = gl_FragCoord.xy;
      vec2 uv = px / uRes;
      // cells hang from the top right, so the mosaic never shows a sliver on that edge
      vec2 origin = mod(uRes, uCell);
      vec2 cell = floor((px - origin) / uCell);
      vec2 cuv = clamp(((cell + 0.5) * uCell + origin) / uRes, 0.0, 1.0);
      vec3 col;
      if (mosaic(cell, cuv) > 0.5) {
        float beat = sin(uTime * (0.7 + hash(cell + 7.0)) + hash(cell) * 6.283);
        col = paint(cuv) * (1.0 + 0.055 * beat);
      } else {
        col = paint(uv);
      }
      // the entrance: cells light up from the bottom, each a little out of step
      float wake = smoothstep(0.0, 0.22, uIn * 1.5 - cuv.y * 0.75 - hash(cell + 3.0) * 0.45);
      col *= mix(wake, 1.0, step(1.0, uIn));
      col += (hash(px + fract(uTime)) - 0.5) / 255.0 * 1.5;
      col = clamp(col, 0.0, 1.0);
      float alpha = uShape == 3 ? clamp(max(col.r, max(col.g, col.b)), 0.0, 1.0) : 1.0;
      gl_FragColor = vec4(col, alpha);
    }`;

  // ------------------------------------------------------------ the one context
  const glCanvas = document.createElement("canvas");
  const gl = glCanvas.getContext("webgl", { alpha: true, antialias: false, premultipliedAlpha: true, depth: false });
  if (!gl) return;

  function compile(type, src) {
    const sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      console.warn("spectrum:", gl.getShaderInfoLog(sh));
      return null;
    }
    return sh;
  }
  let u = null;
  function build() {
    const vs = compile(gl.VERTEX_SHADER, VERT);
    const fs = compile(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return false;
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return false;
    gl.useProgram(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    u = {};
    ["uRes", "uTime", "uCell", "uIn", "uShape", "uFlip", "uPointer"].forEach((n) => { u[n] = gl.getUniformLocation(prog, n); });
    return true;
  }
  if (!build()) return;
  glCanvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); u = null; });
  glCanvas.addEventListener("webglcontextrestored", () => { if (build()) wake(); });

  // ------------------------------------------------------------ surfaces
  const surfaces = new Map();
  let quality = 1;       // drops once if the machine cannot keep up
  let raf = 0;
  let last = 0;
  let slow = 0;
  const pointer = { x: -9999, y: -9999, moved: 0 };

  const seen = "IntersectionObserver" in window
    ? new IntersectionObserver((entries) => entries.forEach((e) => {
      const s = surfaces.get(e.target);
      if (!s) return;
      s.visible = e.isIntersecting;
      if (s.visible) { s.dirty = true; wake(); }
    }), { rootMargin: "80px" })
    : null;
  const sized = new ResizeObserver((entries) => entries.forEach((e) => {
    const s = surfaces.get(e.target);
    if (s) { s.dirty = true; wake(); }
  }));

  function add(host) {
    if (surfaces.has(host) || !(host.dataset.spectrum in SHAPES)) return;
    const canvas = document.createElement("canvas");
    host.appendChild(canvas);
    const flip = host.dataset.flip || "";
    surfaces.set(host, {
      host, canvas, ctx: canvas.getContext("2d"),
      shape: SHAPES[host.dataset.spectrum],
      flip: [flip.includes("x") ? 1 : 0, flip.includes("y") ? 1 : 0],
      cell: Number(host.dataset.cell) || 22,
      seed: surfaces.size * 17 + 9,
      born: 0, visible: !seen, dirty: true, px: 0, py: 0, pz: 0,
    });
    if (seen) seen.observe(host);
    sized.observe(host);
  }

  function draw(s, now) {
    const box = s.host.getBoundingClientRect();
    if (box.width < 2 || box.height < 2) return;
    const still = reducedQuery.matches;
    if (!s.born) s.born = now;
    const scale = quality * Math.min(1, 1600 / box.width);
    const w = Math.max(2, Math.round(box.width * scale));
    const h = Math.max(2, Math.round(box.height * scale));
    if (s.canvas.width !== w || s.canvas.height !== h) { s.canvas.width = w; s.canvas.height = h; }
    if (glCanvas.width < w) glCanvas.width = w;
    if (glCanvas.height < h) glCanvas.height = h;

    // the cursor breaks the gradient into pixels around it, then lets go
    const over = pointer.x >= box.left && pointer.x <= box.right && pointer.y >= box.top && pointer.y <= box.bottom;
    const want = over && now - pointer.moved < 2600 ? 1 : 0;
    s.pz += (want - s.pz) * 0.09;
    const tx = (pointer.x - box.left) * scale;
    const ty = h - (pointer.y - box.top) * scale;
    if (over) {
      const k = s.pz < 0.05 ? 1 : 0.2;
      s.px += (tx - s.px) * k;
      s.py += (ty - s.py) * k;
    }

    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform2f(u.uRes, w, h);
    gl.uniform1f(u.uTime, still ? s.seed : s.seed + now / 1000);
    gl.uniform1f(u.uCell, Math.max(4, Math.round(s.cell * scale)));
    gl.uniform1f(u.uIn, still ? 1 : Math.min(1, (now - s.born) / ENTRANCE_MS));
    gl.uniform1i(u.uShape, s.shape);
    gl.uniform2f(u.uFlip, s.flip[0], s.flip[1]);
    gl.uniform3f(u.uPointer, s.px, s.py, still ? 0 : s.pz);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    s.ctx.clearRect(0, 0, w, h);
    s.ctx.drawImage(glCanvas, 0, glCanvas.height - h, w, h, 0, 0, w, h);
    s.host.classList.add("is-live");
    s.dirty = false;
  }

  function tick(now) {
    raf = 0;
    if (!u || document.hidden) return;
    const live = [];
    surfaces.forEach((s, host) => {
      if (!host.isConnected) {
        if (seen) seen.unobserve(host);
        sized.unobserve(host);
        surfaces.delete(host);
      } else if (s.visible) live.push(s);
    });
    const still = reducedQuery.matches;
    if (now - last >= FRAME_MS - 2) {
      const gap = now - last;
      last = now;
      live.forEach((s) => { if (!still || s.dirty) draw(s, now); });
      // a run of slow frames means a weak GPU: draw at half size from then on
      if (gap < 1000) slow = gap > 70 ? slow + 1 : Math.max(0, slow - 1);
      if (slow > 14 && quality === 1) { quality = 0.5; slow = 0; }
    }
    if (live.length && !still) raf = requestAnimationFrame(tick);
  }
  function wake() {
    if (!raf && u && !document.hidden) raf = requestAnimationFrame(tick);
  }

  document.addEventListener("visibilitychange", wake);
  reducedQuery.addEventListener("change", () => { surfaces.forEach((s) => { s.dirty = true; }); wake(); });
  if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    window.addEventListener("pointermove", (e) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.moved = performance.now();
    }, { passive: true });
  }

  // For markup added later: Spectrum.scan(parent)
  window.Spectrum = {
    scan(root) { (root || document).querySelectorAll("[data-spectrum]").forEach(add); wake(); },
  };
  window.Spectrum.scan();
})();
