/* Geo-intelligence live view: polls /api/state, draws an orthographic globe that eases towards the current focus and
   hands over to imagery tiles when the focus is small, and fills the side panel. Plain browser JS, no dependencies. */
(() => {
  "use strict";

  const STATIC = !!window.GEO_STATE;          // viewer.html snapshot: no server, state and outlines inlined, links relative
  const D = Math.PI / 180;
  const EARTH_KM = 6371;
  const WORLD_KM = 40075;
  const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const TILE_SOURCES = {
    esri: { url: (z, x, y) => `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`, max: 19, credit: "Imagery: Esri, Maxar, Earthstar Geographics" },
    osm: { url: (z, x, y) => `https://tile.openstreetmap.org/${z}/${x}/${y}.png`, max: 19, credit: "Map: OpenStreetMap contributors" },
  };
  const HANDOFF_Z = 3.6;          // globe zoom (log2 of radius growth) where tiles take over
  const FOCUS_FRACTION = 0.28;    // the focus radius fills this fraction of the shorter canvas side
  const COLORS = {
    ocean0: "#17305A", ocean1: "#0C1D38", land: "#1E2F4C", coast: "#3E5A83", grat: "rgba(140,170,220,0.10)",
    glow: "rgba(96,150,230,0.35)", amber: "#F0B445", teal: "#49C2B4",
    muted: "rgba(139,153,179,0.7)", ink: "#E6ECF5", halo: "rgba(11,21,38,0.85)",
  };

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------------------------------------------------------------- globe + tiles

  class Stage {
    constructor(globeCanvas, tileCanvas) {
      this.gc = globeCanvas; this.tc = tileCanvas;
      this.g = globeCanvas.getContext("2d"); this.t = tileCanvas.getContext("2d");
      this.countries = null; this.highlight = new Map();   // iso2 -> alpha
      this.markers = [];                                    // {lat, lon, radius_km, share, excluded, name, lead}
      this.focus = null;                                    // {lat, lon, radius_km, name, heading, final}
      this.focusKey = "";
      this.truth = null;                                    // {lat, lon, name}
      this.manual = null;                                   // centre chosen by dragging, until Follow
      this.layers = { matches: true, coverage: false, marks: true };
      this.data = { cameras: [], lines: [], points: [], images: [], areas: [], levels: [], matches: [], coverage: [] };
      this.level = null;                                    // the level chip shown (null: every level)
      this.selected = null;                                 // {kind, item}
      this.hits = [];                                       // screen positions of clickable markers, rebuilt each frame
      this.lastScreen = null;
      this.zoomOffset = 0;                                  // wheel/button zoom relative to the focus zoom
      this.view = { lat: 20, lon: 10, z: 0 };
      this.target = null;
      this.tiles = TILE_SOURCES.esri;
      this.tileCache = new Map();
      this.w = 0; this.h = 0; this.dpr = 1;
      this.last = performance.now();
      window.addEventListener("resize", () => this.resize());
      this.resize();
      if (window.GEO_COUNTRIES) this.countries = window.GEO_COUNTRIES.features;
      else fetch("/countries.json").then((r) => r.json()).then((j) => { this.countries = j.features; });
      this.bindControls(globeCanvas.parentElement);
      requestAnimationFrame((t) => this.frame(t));
    }

    // wheel and buttons zoom, drag pans; Follow hands control back to the analysis
    bindControls(el) {
      el.addEventListener("wheel", (e) => {
        if (e.target.tagName !== "CANVAS") return;
        e.preventDefault(); this.nudgeZoom(-Math.sign(e.deltaY) * 0.5);
      }, { passive: false });
      let drag = null, moved = 0;
      el.addEventListener("pointerdown", (e) => {
        if (e.button !== 0 || e.target.tagName !== "CANVAS") return;
        drag = { x: e.clientX, y: e.clientY }; moved = 0; e.target.setPointerCapture(e.pointerId);
      });
      el.addEventListener("pointermove", (e) => {
        if (!drag) return;
        moved += Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y);
        this.pan(e.clientX - drag.x, e.clientY - drag.y); drag = { x: e.clientX, y: e.clientY };
      });
      const end = (e) => {
        if (drag && moved < 4 && e.target.tagName === "CANVAS") {
          const r = el.getBoundingClientRect();
          this.pick(e.clientX - r.left, e.clientY - r.top);
        }
        drag = null;
      };
      el.addEventListener("pointerup", end); el.addEventListener("pointercancel", () => { drag = null; });
    }

    nudgeZoom(d) {
      if (!this.focus && !this.manual) return;                      // nothing to zoom on yet
      const base = this.baseZ || 0;
      this.zoomOffset = Math.min(Math.max(this.zoomOffset + d, -base), 17 - base);
      this.retarget();
    }

    static wrapLon(lon) { return ((lon + 180) % 360 + 360) % 360 - 180; }

    pan(dx, dy) {
      const v = this.view, cosl = Math.max(Math.cos(v.lat * D), 0.1);
      let dlat, dlon;
      if (v.z > HANDOFF_Z) { const base = 360 / (256 * Math.pow(2, this.tileZoom())); dlat = dy * base * cosl; dlon = -dx * base; }
      else { const base = 180 / (Math.PI * this.baseRadius() * Math.pow(2, v.z)); dlat = dy * base; dlon = -dx * base / cosl; }
      this.manual = { lat: Math.min(Math.max(v.lat + dlat, -85), 85), lon: Stage.wrapLon(v.lon + dlon) };
      this.view.lat = this.manual.lat; this.view.lon = this.manual.lon;    // immediate while dragging
      this.retarget();
    }

    follow() { this.manual = null; this.zoomOffset = 0; this.retarget(); }

    // centre and radius (km) of a list of [lat, lon]: where a layer's points are, for flying to them
    static extent(pts) {
      const ll = pts.map((p) => Array.isArray(p) ? p : [p.lat, p.lon]);
      let n = 0, sx = 0, sy = 0, sz = 0;
      for (const [lat, lon] of ll) {
        const la = lat * D, lo = lon * D;
        sx += Math.cos(la) * Math.cos(lo); sy += Math.cos(la) * Math.sin(lo); sz += Math.sin(la); n++;
      }
      const lat = Math.atan2(sz, Math.hypot(sx, sy)) / D, lon = Math.atan2(sy, sx) / D;
      let radius_km = 0;
      for (const [la, lo] of ll) {
        const dlat = (la - lat) * D, dlon = (lo - lon) * D * Math.cos(lat * D);
        radius_km = Math.max(radius_km, Math.hypot(dlat, dlon) * EARTH_KM);
      }
      return { lat, lon, radius_km: Math.max(radius_km, 0.05), n };
    }

    // take the view to a point and a radius (like the focus does), until Follow
    flyTo(lat, lon, radiusKm) {
      const px = FOCUS_FRACTION * Math.min(this.w, this.h);
      const R = px * EARTH_KM / Math.max(radiusKm, 0.02);
      const z = Math.min(Math.max(Math.log2(R / this.baseRadius()), 0), 16);
      this.manual = { lat, lon };
      this.zoomOffset = z - (this.baseZ || 0);
      this.retarget();
    }

    pick(x, y) {
      let best = null, bd = 16;
      for (const h of this.hits) { const d = Math.hypot(h.x - x, h.y - y); if (d < bd) { bd = d; best = h; } }
      this.selected = best ? { kind: best.kind, item: best.item } : null;
      if (this.onSelect) this.onSelect(this.selected);
    }

    // marks, matches and coverage: drawn in both modes through the same projection helpers
    drawLayers(g, toScreen, kmToPx) {
      this.hits = [];
      const d = this.data;
      if (this.layers.coverage && d.coverage.length) {
        // panorama positions: dots when the view resolves them, one ring with the count when they collapse into a few pixels
        const ext = Stage.extent(d.coverage);
        const c = toScreen(ext.lat, ext.lon);
        const rPx = kmToPx(ext.radius_km);
        if (c.visible && rPx < 14) {
          g.beginPath(); g.arc(c.x, c.y, 12, 0, Math.PI * 2);
          g.strokeStyle = COLORS.teal; g.lineWidth = 1.5; g.setLineDash([3, 3]); g.stroke(); g.setLineDash([]);
          g.fillStyle = COLORS.teal; g.font = "11px system-ui, sans-serif"; g.textAlign = "left"; g.textBaseline = "middle";
          g.fillText(`${d.coverage.length} panoramas`, c.x + 16, c.y);
        } else {
          g.fillStyle = "rgba(73,194,180,0.75)";
          for (const c of d.coverage) {
            const p = toScreen(c.lat, c.lon); if (!p.visible) continue;
            g.fillRect(p.x - 1.5, p.y - 1.5, 3, 3);
            this.hits.push({ x: p.x, y: p.y, kind: "coverage", item: c });        // a click opens the panorama's card
          }
        }
      }
      if (this.layers.matches) {
        const n = d.matches.length;
        d.matches.forEach((m, i) => {
          const p = toScreen(m.lat, m.lon); if (!p.visible) return;
          const top = i < 3, r = top ? 6 : 4;
          if (m.heading != null) {
            const a = (m.heading - 90) * D;
            g.beginPath(); g.moveTo(p.x, p.y); g.lineTo(p.x + Math.cos(a) * (r + 8), p.y + Math.sin(a) * (r + 8));
            g.strokeStyle = top ? COLORS.amber : "rgba(240,180,69,0.6)"; g.lineWidth = 1.5; g.stroke();
          }
          g.beginPath(); g.arc(p.x, p.y, r, 0, Math.PI * 2);
          g.fillStyle = top ? "rgba(240,180,69,0.9)" : "rgba(240,180,69,0.45)"; g.fill();
          g.strokeStyle = COLORS.halo; g.lineWidth = 1; g.stroke();
          if (top) { g.font = "600 11px " + getComputedStyle(document.body).fontFamily; g.fillStyle = COLORS.halo; g.textAlign = "center"; g.fillText(String(i + 1), p.x, p.y + 4); g.textAlign = "start"; }
          this.hits.push({ x: p.x, y: p.y, kind: "match", item: m });
        });
      }
      if (this.layers.marks) {
        const labels = [];
        for (const a of d.areas) this.drawArea(g, toScreen, kmToPx, a, labels);   // under the other marks
        g.font = "600 12px " + getComputedStyle(document.body).fontFamily;
        for (const l of d.lines) {
          const a = toScreen(l.from[0], l.from[1]), b = toScreen(l.to[0], l.to[1]);
          if (!a.visible && !b.visible) continue;
          g.setLineDash([6, 5]); g.strokeStyle = "rgba(240,180,69,0.75)"; g.lineWidth = 1.2;
          g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke(); g.setLineDash([]);
          if (l.label && b.visible) { g.lineWidth = 4; g.strokeStyle = COLORS.halo; g.fillStyle = COLORS.ink; g.strokeText(l.label, b.x + 6, b.y - 6); g.fillText(l.label, b.x + 6, b.y - 6); }
        }
        for (const c of d.cameras) {
          const p = toScreen(c.lat, c.lon); if (!p.visible) continue;
          const a = (c.heading - 90) * D, half = ((c.fov || 90) / 2) * D, len = this.coneLen(kmToPx);
          g.beginPath(); g.moveTo(p.x, p.y); g.arc(p.x, p.y, len, a - half, a + half); g.closePath();
          g.fillStyle = "rgba(240,180,69,0.16)"; g.fill(); g.strokeStyle = "rgba(240,180,69,0.7)"; g.lineWidth = 1; g.stroke();
          g.beginPath(); g.moveTo(p.x, p.y); g.lineTo(p.x + Math.cos(a) * len, p.y + Math.sin(a) * len); g.strokeStyle = COLORS.amber; g.lineWidth = 1.5; g.stroke();
          if (c.radius_m) { g.beginPath(); g.arc(p.x, p.y, Math.max(kmToPx(c.radius_m / 1000), 3), 0, Math.PI * 2); g.strokeStyle = "rgba(240,180,69,0.5)"; g.lineWidth = 1; g.stroke(); }
          g.beginPath(); g.arc(p.x, p.y, 4, 0, Math.PI * 2); g.fillStyle = COLORS.amber; g.fill();
          g.lineWidth = 4; g.strokeStyle = COLORS.halo; g.fillStyle = COLORS.ink; g.strokeText(c.label, p.x + 10, p.y - 8); g.fillText(c.label, p.x + 10, p.y - 8);
          this.hits.push({ x: p.x, y: p.y, kind: "camera", item: c });
        }
        for (const pt of d.points) {
          const p = toScreen(pt.lat, pt.lon); if (!p.visible) continue;
          g.beginPath(); g.arc(p.x, p.y, 3.5, 0, Math.PI * 2); g.fillStyle = COLORS.ink; g.fill(); g.strokeStyle = COLORS.halo; g.lineWidth = 1; g.stroke();
          g.lineWidth = 4; g.strokeStyle = COLORS.halo; g.fillStyle = COLORS.ink; g.strokeText(pt.label, p.x + 8, p.y + 4); g.fillText(pt.label, p.x + 8, p.y + 4);
          this.hits.push({ x: p.x, y: p.y, kind: "point", item: pt });
        }
        for (const im of d.images) {
          const p = toScreen(im.lat, im.lon); if (!p.visible) continue;
          g.fillStyle = COLORS.halo; g.fillRect(p.x - 7, p.y - 5, 14, 10);
          g.strokeStyle = COLORS.ink; g.lineWidth = 1; g.strokeRect(p.x - 7, p.y - 5, 14, 10);
          if (im.heading != null) { const a = (im.heading - 90) * D; g.beginPath(); g.moveTo(p.x, p.y); g.lineTo(p.x + Math.cos(a) * 16, p.y + Math.sin(a) * 16); g.strokeStyle = COLORS.ink; g.stroke(); }
          this.hits.push({ x: p.x, y: p.y, kind: "image", item: im });
        }
      }
      if (this.selected) {
        const s = this.selected.item;
        const p = toScreen(s.lat ?? s.from?.[0], s.lon ?? s.from?.[1]);
        if (p.visible) { g.beginPath(); g.arc(p.x, p.y, 11, 0, Math.PI * 2); g.strokeStyle = COLORS.ink; g.lineWidth = 1.5; g.stroke(); this.lastScreen = p; }
        else this.lastScreen = null;
      }
    }

    // a `mark area` file: rings with a faint fill and lines (corridors, shores), dashed below ground. While a level chip is on,
    // features of other levels hide and those without a level (the footprint) stay; a name shows once its feature is readable
    // and its box overlaps no name already drawn in this frame (labels: the frame's boxes, reset by drawLayers)
    drawArea(g, toScreen, kmToPx, a, labels) {
      const font = "600 11px " + getComputedStyle(document.body).fontFamily;
      const text = (lat, lon, s) => {
        const p = toScreen(lat, lon);
        if (!p.visible) return;
        const t = s.length > 28 ? s.slice(0, 27) + "…" : s;
        g.font = font;
        const w = g.measureText(t).width + 8, box = { x0: p.x - w / 2, x1: p.x + w / 2, y0: p.y - 9, y1: p.y + 7 };
        if (labels.some((o) => box.x0 < o.x1 && o.x0 < box.x1 && box.y0 < o.y1 && o.y0 < box.y1)) return;
        labels.push(box);
        g.textAlign = "center"; g.lineWidth = 4; g.strokeStyle = COLORS.halo; g.fillStyle = COLORS.ink;
        g.strokeText(t, p.x, p.y); g.fillText(t, p.x, p.y); g.textAlign = "start";
      };
      let named = false;
      for (const f of a.features || []) {
        const lv = f.levels || [], rings = f.rings || [], lines = f.lines || [];
        if (this.level != null && lv.length && !lv.includes(this.level)) continue;
        g.beginPath();
        let seen = false;
        for (const r of rings) seen = this.trace(g, toScreen, r, true) || seen;
        if (seen && rings.length) { g.fillStyle = "rgba(230,236,245,0.08)"; g.fill("evenodd"); }
        for (const l of lines) seen = this.trace(g, toScreen, l, false) || seen;
        if (!seen) continue;
        g.setLineDash(f.dashed ? [5, 4] : []);
        g.strokeStyle = "rgba(11,21,38,0.55)"; g.lineWidth = 3; g.stroke();        // dark halo: the line reads on bright imagery too
        g.strokeStyle = "rgba(230,236,245,0.9)"; g.lineWidth = 1.2; g.stroke(); g.setLineDash([]);
        const name = f.tags && f.tags.name;
        named = named || !!name;
        if (name && kmToPx(f.r_km || 0) >= 24) text(f.lat, f.lon, name);
      }
      if (!named && a.label && a.lat != null && kmToPx(a.r_km || 0) >= 24) text(a.lat, a.lon, a.label);
    }

    // a view cone is a direction glyph, not a range: short on the globe (48 px), growing with the map up to 220 px (2 km on screen)
    coneLen(kmToPx) { return Math.max(Math.min(Math.min(this.w, this.h) * 0.22, 220, kmToPx(2)), 48); }

    // one ring or line of [lon, lat] into the current path; back-side globe points sit on the limb, so a ring closes along the horizon
    trace(g, toScreen, coords, closed) {
      let first = true, seen = false;
      for (const [lon, lat] of coords) {
        const p = toScreen(lat, lon);
        seen = seen || p.visible;
        if (first) { g.moveTo(p.x, p.y); first = false; } else g.lineTo(p.x, p.y);
      }
      if (closed) g.closePath();
      return seen;
    }

    get controlled() { return !!this.manual || this.zoomOffset !== 0; }

    resize() {
      const rect = this.gc.parentElement.getBoundingClientRect();
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.w = Math.max(rect.width, 1); this.h = Math.max(rect.height, 1);
      for (const c of [this.gc, this.tc]) { c.width = this.w * this.dpr; c.height = this.h * this.dpr; }
      this.g.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      this.t.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      this.retarget();
    }

    baseRadius() { return Math.min(this.w, this.h) * 0.42; }

    setTiles(key) { this.tiles = TILE_SOURCES[key] || TILE_SOURCES.esri; }

    setFocus(focus) {
      const key = focus ? `${focus.name}|${focus.level}|${focus.final}|${focus.radius_km}` : "";
      if (key !== this.focusKey) { this.manual = null; this.zoomOffset = 0; this.focusKey = key; }   // the analysis moved on
      this.focus = focus;
      this.retarget();
    }

    retarget() {
      const f = this.focus;
      if (!f && !this.manual) { this.target = null; return; }
      let z = 0;
      if (f) {
        const px = FOCUS_FRACTION * Math.min(this.w, this.h);
        const R = px * EARTH_KM / Math.max(f.view_radius_km || f.radius_km, 0.02);
        z = Math.min(Math.max(Math.log2(R / this.baseRadius()), 0), 16);
      }
      this.baseZ = z;
      z = Math.min(Math.max(z + this.zoomOffset, 0), 17);
      const c = this.manual || (f ? { lat: f.view_lat ?? f.lat, lon: f.view_lon ?? f.lon } : { lat: this.view.lat, lon: this.view.lon });
      this.target = { lat: c.lat, lon: c.lon, z };
      if (REDUCED) this.view = { ...this.target };
    }

    // orthographic projection around the view centre
    project(lat, lon, R, cx, cy) {
      const p = lat * D, l = lon * D, p0 = this.view.lat * D, l0 = this.view.lon * D;
      const cosc = Math.sin(p0) * Math.sin(p) + Math.cos(p0) * Math.cos(p) * Math.cos(l - l0);
      let x = R * Math.cos(p) * Math.sin(l - l0);
      let y = R * (Math.cos(p0) * Math.sin(p) - Math.sin(p0) * Math.cos(p) * Math.cos(l - l0));
      const visible = cosc > 0;
      if (!visible) {   // push back-side points onto the limb so polygons close along the horizon
        const d = Math.hypot(x, y) || 1;
        x = x / d * R; y = y / d * R;
      }
      return { x: cx + x, y: cy - y, visible };
    }

    frame(now) {
      const dt = Math.min((now - this.last) / 16.67, 3); this.last = now;
      const v = this.view;
      if (this.target) {
        const k = REDUCED ? 1 : 1 - Math.pow(1 - 0.045, dt);
        let dl = ((this.target.lon - v.lon + 540) % 360) - 180;
        v.lon += dl * k; v.lat += (this.target.lat - v.lat) * k; v.z += (this.target.z - v.z) * k;
      } else if (!REDUCED) {
        v.lon -= 0.035 * dt;                         // slow search sweep while nothing is on the board
        v.lat += (18 - v.lat) * 0.01 * dt; v.z += (0 - v.z) * 0.02 * dt;
      }
      v.lon = Stage.wrapLon(v.lon);                  // markers project from the wrapped centre, never from lon ± 360
      const tileAlpha = Math.min(Math.max((v.z - HANDOFF_Z + 0.4) / 0.8, 0), 1);
      this.tc.style.opacity = tileAlpha.toFixed(2);
      const credit = document.getElementById("attribution");
      if (credit) credit.hidden = tileAlpha === 0;   // imagery on screen means its credit on screen, whatever moved the view
      if (tileAlpha < 1) this.drawGlobe(now); else this.g.clearRect(0, 0, this.w, this.h);
      if (tileAlpha > 0) this.drawTiles(now); else this.t.clearRect(0, 0, this.w, this.h);
      requestAnimationFrame((t) => this.frame(t));
    }

    drawGlobe(now) {
      const g = this.g, cx = this.w / 2, cy = this.h / 2;
      const R = this.baseRadius() * Math.pow(2, this.view.z);
      g.clearRect(0, 0, this.w, this.h);
      // atmosphere
      const glow = g.createRadialGradient(cx, cy, R * 0.96, cx, cy, R * 1.08);
      glow.addColorStop(0, COLORS.glow); glow.addColorStop(1, "rgba(96,150,230,0)");
      g.fillStyle = glow; g.beginPath(); g.arc(cx, cy, R * 1.08, 0, Math.PI * 2); g.fill();
      g.save();
      g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.clip();
      const ocean = g.createRadialGradient(cx - R * 0.3, cy - R * 0.35, R * 0.1, cx, cy, R);
      ocean.addColorStop(0, COLORS.ocean0); ocean.addColorStop(1, COLORS.ocean1);
      g.fillStyle = ocean; g.fillRect(cx - R, cy - R, 2 * R, 2 * R);
      this.drawGraticule(g, R, cx, cy);
      if (this.countries) this.drawCountries(g, R, cx, cy);
      this.drawMarkers(g, (lat, lon) => this.project(lat, lon, R, cx, cy), (km) => km * R / EARTH_KM, now);
      g.restore();
      g.strokeStyle = "rgba(160,190,240,0.35)"; g.lineWidth = 1;
      g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.stroke();
    }

    drawGraticule(g, R, cx, cy) {
      g.strokeStyle = COLORS.grat; g.lineWidth = 1;
      const step = this.view.z > 2 ? 5 : 15;
      for (let lat = -75; lat <= 75; lat += step) this.strokeLine(g, R, cx, cy, Array.from({ length: 73 }, (_, i) => [lat, -180 + i * 5]));
      for (let lon = -180; lon < 180; lon += step) this.strokeLine(g, R, cx, cy, Array.from({ length: 37 }, (_, i) => [-90 + i * 5, lon]));
    }

    strokeLine(g, R, cx, cy, pts) {
      g.beginPath(); let pen = false;
      for (const [lat, lon] of pts) {
        const p = this.project(lat, lon, R, cx, cy);
        if (!p.visible) { pen = false; continue; }
        if (pen) g.lineTo(p.x, p.y); else g.moveTo(p.x, p.y);
        pen = true;
      }
      g.stroke();
    }

    drawCountries(g, R, cx, cy) {
      const zoomed = this.view.z > 1.5;
      const proj = (lat, lon) => this.project(lat, lon, R, cx, cy);
      for (const f of this.countries) {
        const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
        const hl = this.highlight.get(f.properties.iso2);
        g.beginPath();
        let any = false;
        for (const poly of polys) for (const ring of poly) any = this.trace(g, proj, ring, true) || any;
        if (!any) continue;
        g.fillStyle = hl ? `rgba(240,180,69,${(0.18 + 0.45 * hl).toFixed(3)})` : COLORS.land;
        g.fill();
        g.strokeStyle = hl ? COLORS.amber : COLORS.coast; g.lineWidth = hl ? 1.2 : (zoomed ? 0.9 : 0.6);
        g.stroke();
      }
    }

    // ---- tiles (Web Mercator)
    merc(lat, lon, z) {
      const n = 256 * Math.pow(2, z);
      const s = Math.sin(Math.max(Math.min(lat, 85.05), -85.05) * D);
      return { x: (lon + 180) / 360 * n, y: (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * n };
    }

    tileZoom() {
      // same ground scale as the globe at the view centre, so the handoff does not jump
      const R = this.baseRadius() * Math.pow(2, this.view.z);
      const pxPerKm = R / EARTH_KM;
      const cosl = Math.max(Math.cos(this.view.lat * D), 0.05);
      return Math.log2(pxPerKm * WORLD_KM * cosl / 256);
    }

    drawTiles(now) {
      const t = this.t, cx = this.w / 2, cy = this.h / 2;
      const v = this.view, tg = this.target;
      const flying = !!tg && (Math.abs(tg.z - v.z) > 0.12 || Math.abs(tg.lat - v.lat) > 0.02 || Math.abs(((tg.lon - v.lon + 540) % 360) - 180) > 0.02);
      this.loadTiles = !flying;                       // only fetch tiles for frames near the destination
      const zf = this.tileZoom();
      const zi = Math.max(2, Math.min(this.tiles.max, Math.round(zf)));
      const scale = Math.pow(2, zf - zi), size = 256 * scale, n = Math.pow(2, zi);
      const c = this.merc(this.view.lat, this.view.lon, zi);
      t.fillStyle = "#06101C"; t.fillRect(0, 0, this.w, this.h);
      const x0 = Math.floor((c.x - cx / scale) / 256), x1 = Math.ceil((c.x + (this.w - cx) / scale) / 256);
      const y0 = Math.max(0, Math.floor((c.y - cy / scale) / 256)), y1 = Math.min(n - 1, Math.ceil((c.y + (this.h - cy) / scale) / 256));
      for (let ty = y0; ty <= y1; ty++) {
        for (let tx = x0; tx <= x1; tx++) {
          const img = this.tile(zi, ((tx % n) + n) % n, ty);
          if (!img) continue;
          t.drawImage(img, cx + (tx * 256 - c.x) * scale, cy + (ty * 256 - c.y) * scale, size + 0.5, size + 0.5);
        }
      }
      const toScreen = (lat, lon) => {                                // longitude relative to the centre: no jump across ±180
        const m = this.merc(lat, this.view.lon + Stage.wrapLon(lon - this.view.lon), zi);
        return { x: cx + (m.x - c.x) * scale, y: cy + (m.y - c.y) * scale, visible: true };
      };
      const kmToPx = (km) => km * 256 * n * scale / (WORLD_KM * Math.max(Math.cos(this.view.lat * D), 0.05));
      this.drawMarkers(t, toScreen, kmToPx, now);
    }

    tile(z, x, y) {
      const key = `${z}/${x}/${y}`;
      let img = this.tileCache.get(key);
      if (img !== undefined) { this.tileCache.delete(key); this.tileCache.set(key, img); }   // most recently used last
      if (img === undefined) {
        if (this.loadTiles === false) return null;
        img = new Image();
        img.crossOrigin = "anonymous";
        img.decoding = "async";
        const entry = { img, ok: false };
        img.onload = () => { entry.ok = true; };
        img.onerror = () => { entry.ok = false; };
        img.src = this.tiles.url(z, x, y);
        this.tileCache.set(key, entry);
        if (this.tileCache.size > 1500) this.tileCache.delete(this.tileCache.keys().next().value);   // drops the least recently used
        return null;
      }
      return img.ok ? img.img : null;
    }

    drawMarkers(g, toScreen, kmToPx, now) {
      this.drawLayers(g, toScreen, kmToPx);
      const pulse = REDUCED ? 0 : (now % 2200) / 2200;
      for (const m of this.markers) {
        const p = toScreen(m.lat, m.lon);
        if (!p.visible) continue;
        const r = Math.max(kmToPx(m.radius_km), 3);
        g.beginPath(); g.arc(p.x, p.y, r, 0, Math.PI * 2);
        if (m.excluded) { g.strokeStyle = COLORS.muted; g.lineWidth = 1; g.setLineDash([3, 4]); g.stroke(); g.setLineDash([]); continue; }
        g.fillStyle = `rgba(240,180,69,${(0.06 + 0.25 * m.share).toFixed(3)})`; g.fill();
        g.strokeStyle = m.lead ? COLORS.amber : "rgba(240,180,69,0.55)"; g.lineWidth = m.lead ? 1.5 : 1; g.stroke();
      }
      const f = this.focus;
      const t = this.truth;
      if (t) {
        const q = toScreen(t.lat, t.lon);
        if (q.visible) {
          if (f) {
            const a = toScreen(f.lat, f.lon);
            if (a.visible) { g.setLineDash([4, 5]); g.strokeStyle = "rgba(73,194,180,0.7)"; g.lineWidth = 1.2; g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(q.x, q.y); g.stroke(); g.setLineDash([]); }
          }
          g.beginPath(); g.arc(q.x, q.y, 9, 0, Math.PI * 2); g.strokeStyle = COLORS.teal; g.lineWidth = 1.5; g.stroke();
          g.beginPath(); g.arc(q.x, q.y, 3.5, 0, Math.PI * 2); g.fillStyle = COLORS.teal; g.fill();
          g.font = "600 13px " + getComputedStyle(document.body).fontFamily;
          g.lineWidth = 4; g.strokeStyle = COLORS.halo; g.fillStyle = COLORS.teal;
          g.strokeText(t.name, q.x + 16, q.y + 4); g.fillText(t.name, q.x + 16, q.y + 4);
        }
      }
      if (!f) return;
      const p = toScreen(f.lat, f.lon);
      if (!p.visible) return;
      const r = Math.max(kmToPx(f.radius_km), 4);
      if (f.final && f.heading == null && f.heading_hint != null) {   // suggested by the best match: dashed, labelled
        const a = (f.heading_hint - 90) * D, len = this.coneLen(kmToPx);
        g.setLineDash([5, 5]);
        g.beginPath(); g.moveTo(p.x, p.y); g.arc(p.x, p.y, len, a - 25 * D, a + 25 * D); g.closePath();
        g.fillStyle = "rgba(240,180,69,0.08)"; g.fill(); g.strokeStyle = "rgba(240,180,69,0.7)"; g.lineWidth = 1; g.stroke();
        g.setLineDash([]);
        g.font = "600 11px " + getComputedStyle(document.body).fontFamily; g.lineWidth = 4; g.strokeStyle = COLORS.halo; g.fillStyle = COLORS.muted;
        const lx = p.x + Math.cos(a) * len * 0.6, ly = p.y + Math.sin(a) * len * 0.6;
        g.strokeText("suggested heading", lx, ly); g.fillText("suggested heading", lx, ly);
      }
      if (f.final && f.heading != null) {
        const a = (f.heading - 90) * D, len = this.coneLen(kmToPx);
        g.beginPath(); g.moveTo(p.x, p.y); g.arc(p.x, p.y, len, a - 25 * D, a + 25 * D); g.closePath();
        g.fillStyle = "rgba(240,180,69,0.18)"; g.fill();
        g.strokeStyle = "rgba(240,180,69,0.6)"; g.lineWidth = 1; g.stroke();
      }
      g.beginPath(); g.arc(p.x, p.y, r, 0, Math.PI * 2);
      g.strokeStyle = COLORS.amber; g.lineWidth = 1.5; g.stroke();
      if (pulse) {
        g.beginPath(); g.arc(p.x, p.y, r + 6 + 22 * pulse, 0, Math.PI * 2);
        g.strokeStyle = `rgba(240,180,69,${(0.5 * (1 - pulse)).toFixed(3)})`; g.lineWidth = 1.5; g.stroke();
      }
      g.beginPath(); g.arc(p.x, p.y, 3.5, 0, Math.PI * 2); g.fillStyle = COLORS.amber; g.fill();
      g.font = "600 13px " + getComputedStyle(document.body).fontFamily;
      g.lineWidth = 4; g.strokeStyle = COLORS.halo; g.fillStyle = COLORS.ink;
      const lx = p.x + Math.min(r, 14) + 10;
      g.strokeText(f.name, lx, p.y + 4); g.fillText(f.name, lx, p.y + 4);
    }
  }

  // ---------------------------------------------------------------- panel

  const stage = new Stage($("globe"), $("tiles"));
  window.geoStage = stage;   // for debugging from the console
  let etag = null, state = null, startedAt = null, stopped = false;

  function fmtCoord(lat, lon) {
    const f = (v, pos, neg) => `${Math.abs(v).toFixed(5)}° ${v >= 0 ? pos : neg}`;
    return `${f(lat, "N", "S")}  ${f(lon, "E", "W")}`;
  }

  function mapPosition(lat, lon) {
    return Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180
      ? `${lat},${lon}` : null;
  }

  function mapsURL(lat, lon) {
    const pos = mapPosition(lat, lon);
    return pos == null ? null : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(pos)}`;
  }

  function streetViewURL(it) {
    const pos = mapPosition(it.lat, it.lon);
    if (pos == null) return null;
    const params = new URLSearchParams({ api: "1", map_action: "pano", viewpoint: pos });
    if (Number.isFinite(it.heading)) params.set("heading", ((it.heading % 360) + 360) % 360);
    if (Number.isFinite(it.fov)) params.set("fov", Math.min(100, Math.max(10, it.fov)));
    return `https://www.google.com/maps/@?${params}`;
  }

  function setMapLink(id, url) {
    const a = $(id);
    a.hidden = !url;
    if (url) a.href = url; else a.removeAttribute("href");
  }

  function fmtRadius(km) {
    if (km >= 100) return `${Math.round(km)} km`;
    if (km >= 1) return `${km.toFixed(1)} km`;
    return `${Math.round(km * 1000)} m`;
  }

  function fmtTime(iso) {
    if (!iso) return "";
    const m = /T(\d\d:\d\d)/.exec(iso);
    return m ? m[1] : iso;
  }

  function elapsed() {
    if (!startedAt) return "";
    const s = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    return h ? `${h} h ${m} min` : `${m} min ${s % 60} s`;
  }

  function renderMeta() {
    if (!state || stopped) return;
    const started = state.started_at ? fmtTime(state.started_at) : "";
    const parts = [];
    if (started) parts.push(`Started ${started}.`);
    if (state.status === "completed") parts.push("Finished.");
    else if (STATIC) parts.push("Not finished when this snapshot was taken.");
    else parts.push(`Running ${elapsed()}.`);
    if (STATIC && state.snapshot_at) parts.push(`Snapshot ${fmtTime(state.snapshot_at)}, offline copy.`);
    $("meta-text").textContent = parts.join(" ");
    $("live").hidden = STATIC || state.status === "completed";
  }

  let lastPhotos = "", lastFolder = "";
  function renderPhotos(s) {
    const key = s.photos.map((p) => p.url).join("|");
    if (key !== lastPhotos) {
      $("photos").innerHTML = s.photos.map((p) =>
        `<button type="button" data-url="${esc(p.url)}" data-cap="${esc(p.path)}" title="${esc(p.name)}"><img src="${esc(p.url)}" alt="${esc(p.name)}" decoding="async"></button>`).join("");
      lastPhotos = key;
    }
    if (s.folder !== lastFolder) { $("folder").textContent = s.folder; lastFolder = s.folder; }
  }

  let lastSkyline = "";
  function renderSkyline(s) {
    const k = s.skyline;
    $("skyline-section").hidden = !k;
    if (!k) { lastSkyline = ""; return; }
    const key = k.image + (k.time || "") + k.top.length;
    if (key === lastSkyline) return;
    lastSkyline = key;
    const rows = k.top.map((t) => {
      const bits = [`score ${Number(t.total).toFixed(3)}`, `heading ${Math.round(t.heading)}°`];
      if (t.f35) bits.push(`${Math.round(t.f35)} mm`);
      if (t.rms_px != null) bits.push(`rms ${Math.round(t.rms_px)} px`);
      if (t.tie && t.tie.n > 1 && t.tie.span_m > 0) bits.push(`${t.tie.n} positions tie over ${Math.round(t.tie.span_m)} m along ${Math.round(t.tie.bearing)}°`);
      const peaks = (t.peaks || []).map((p) => `${p.name} (${(p.dist_m / 1000).toFixed(1)} km)`).join(", ");
      const pf = t.peakfinder_url ? ` <a href="${esc(t.peakfinder_url)}" target="_blank" rel="noopener" title="The same camera in PeakFinder, with peak names">PeakFinder</a>` : "";
      return `<li><b>#${t.rank}</b> ${esc(t.name)} <span class="muted">${esc(bits.join(" · "))}</span>${pf}${peaks ? `<br><span class="muted">summits: ${esc(peaks)}</span>` : ""}</li>`;
    }).join("");
    $("skyline").innerHTML = `<button type="button" class="skyline-img" data-url="${esc(k.image)}" data-cap="Skyline: top ${k.top.length} candidates over the photo"><img src="${esc(k.image)}" alt="synthetic skyline of the best candidates over the photo"></button>`
      + `<ol class="skyline-top">${rows}</ol>`
      + `<p class="muted small">Red line: the skyline computed from elevation data at each candidate camera; yellow dots: the ridge read from the photo. Ranked by fit score, best first; a match fixes a sight line, not a point.</p>`;
  }

  let lastGallery = "";
  function renderGallery(s) {
    const imgs = s.analysis_images || [];
    $("analysis-section").hidden = !imgs.length;
    const key = imgs.map((a) => a.url + a.mtime).join("|");
    if (key === lastGallery) return;
    lastGallery = key;
    $("analysis").innerHTML = imgs.map((a) =>
      `<button type="button" data-url="${esc(a.url)}" data-cap="${esc(a.path)}"><img loading="lazy" decoding="async" src="${esc(a.url)}" alt=""><span title="${esc(a.path)}">${esc(a.path.split("/").pop())}</span></button>`).join("");
  }

  function layerCounts(s) {
    const L = s.layers || {};
    $("layer-matches").textContent = `Matches ${(L.matches || []).length}`;
    $("layer-coverage").textContent = `Coverage ${(L.coverage || []).length}`;
    $("layer-coverage").title = (L.coverage || []).length
      ? "Every panorama position found for the search (gsv.py area, pano.py list). On: dots, or one ring with the count when they are too close to tell apart; the view flies to them. Follow returns."
      : "No panorama list in the session yet (gsv.py area or pano.py list writes one).";
    $("layer-marks").textContent = `Marks ${(L.cameras || []).length + (L.lines || []).length + (L.points || []).length + (L.images || []).length + (L.areas || []).length}`;
  }

  // level chips beside the layer toggles, once an area feature carries a level: all, then each level, sorted numerically
  let lastLevels = "";
  function renderLevels(s) {
    const lv = (s.layers && s.layers.levels) || [];
    if (stage.level != null && !lv.includes(stage.level)) stage.level = null;   // that level left the marks
    const key = lv.join("|") + "#" + stage.level;
    if (key === lastLevels) return;
    lastLevels = key;
    $("levels").hidden = !lv.length;
    $("levels").innerHTML = [null, ...lv].map((v) =>
      `<button type="button" data-level="${v == null ? "" : esc(v)}" class="${v === stage.level ? "on" : ""}" title="${v == null ? "Every level" : `Level ${esc(v)} and the outlines without a level`}">${v == null ? "all" : esc(v)}</button>`).join("");
  }

  const generated = (s) => s.status === "completed" && !!s.result && s.result.outcome === "generated";

  // the truth line when a generated image is involved: a generated answer against any truth, or a place answer against a
  // generated truth; "" otherwise (the place-to-place line is written where it is shown)
  function generatedTruth(s, lead) {
    const t = s.truth;
    if (!t) return "";
    if (generated(s)) {
      if (t.outcome === "generated") return `${lead}: generated image (confirmed).`;
      return t.latitude != null ? `${lead}: ${truthName(t)}, ${fmtCoord(t.latitude, t.longitude)} (false stop: the photo shows a real place).` : "";
    }
    return t.outcome === "generated" ? `${lead}: generated image, no real place (missed generation).` : "";
  }

  function showCard(sel) {
    const card = $("card");
    if (!sel) { card.hidden = true; return; }
    const it = sel.item, img = $("card-img");
    let title = "", meta = "", url = null, link = null;
    if (sel.kind === "match") {
      title = `Match ${it.rank ?? ""}${it.label ? ": " + it.label : ""}`.trim();
      meta = [it.score != null ? `score ${Number(it.score).toFixed(3)}` : null, it.inliers != null ? `${it.inliers} inliers` : null,
              it.heading != null ? `heading ${Math.round(it.heading)}°` : null, fmtCoord(it.lat, it.lon), it.source].filter(Boolean).join(", ");
      url = it.view;
    } else if (sel.kind === "camera") {
      title = it.label || "Camera";
      meta = [`heading ${Math.round(it.heading)}°`, `field of view ${Math.round(it.fov || 90)}°`, it.radius_m ? `radius ${fmtRadius(it.radius_m / 1000)}` : null, fmtCoord(it.lat, it.lon)].filter(Boolean).join(", ");
    } else if (sel.kind === "image") {
      title = it.label || it.file; meta = [it.heading != null ? `heading ${Math.round(it.heading)}°` : null, fmtCoord(it.lat, it.lon)].filter(Boolean).join(", "); url = it.url;
    } else if (sel.kind === "coverage") {
      title = `Panorama ${it.id || ""}`.trim();
      meta = [it.provider, it.date ? `date ${it.date}` : null, it.road ? `road ${it.road}` : null, it.heading != null ? `heading ${Math.round(it.heading)}°` : null,
              fmtCoord(it.lat, it.lon), it.list ? `list ${it.list}` : null].filter(Boolean).join(", ");
      link = it.url || ((it.provider === "google" || (!it.provider && /^[A-Za-z0-9_-]{22}$/.test(it.id || "")))
        ? `https://www.google.com/maps/@?api=1&map_action=pano&pano=${encodeURIComponent(it.id)}` : null);
    } else {
      title = it.label || "Point"; meta = fmtCoord(it.lat, it.lon); url = it.url || null;
    }
    $("card-title").textContent = title; $("card-meta").textContent = meta;
    const street = sel.kind === "camera" || sel.kind === "match";
    if (street) link = streetViewURL(it);
    const a = $("card-link");
    a.textContent = street ? "Street View" : "Open the panorama";
    a.title = street ? "Nearest Google Street View panorama, using this position and heading" : "Open the source panorama";
    setMapLink("card-link", link);
    setMapLink("card-map", mapsURL(it.lat, it.lon));
    if (url) { img.src = url; img.hidden = false; img.onclick = () => openLightbox(url, title); } else { img.hidden = true; img.src = ""; }
    card.hidden = false;
  }

  function placeCard() {
    const card = $("card");
    if (card.hidden || !stage.selected) return;
    const p = stage.lastScreen;
    if (!p) { card.style.visibility = "hidden"; return; }
    card.style.visibility = "visible";
    const w = card.offsetWidth, h = card.offsetHeight;
    let x = p.x + 16, y = p.y - h / 2;
    if (x + w > stage.w - 8) x = p.x - w - 16;
    y = Math.min(Math.max(y, 8), stage.h - h - 8);
    card.style.left = `${x}px`; card.style.top = `${y}px`;
  }

  function renderStages(s) {
    const idx = s.stages.indexOf(s.stage);
    $("stages").innerHTML = s.stages.map((name, i) =>
      `<li class="${i < idx ? "done" : i === idx ? "current" : ""}">${esc(name)}</li>`).join("");
  }

  function renderScope(s) {
    const f = s.focus;
    setMapLink("scope-map", f && !generated(s) ? mapsURL(f.lat, f.lon) : null);
    const note = $("scope-note");
    if (generated(s)) {                                   // finished with no place: before the no-focus branch, which means "no candidate yet"
      $("scope-level").textContent = "Answer";
      $("scope-name").textContent = "Generated image: no real place";
      $("scope-coords").textContent = "";
      note.textContent = `Basis: ${(s.result.generated || {}).basis || "not recorded"}.`;
      const tr = $("scope-truth"), line = generatedTruth(s, "Truth");
      tr.hidden = !line; tr.textContent = line;
      return;
    }
    if (!f) {
      $("scope-level").textContent = "Whole world";
      $("scope-name").textContent = "No candidate yet";
      $("scope-coords").textContent = "";
      note.textContent = "The globe turns to the leading candidate as soon as one is on the board.";
      return;
    }
    if (f.final) {
      $("scope-level").textContent = `Answer, ${f.confidence || "unrated"} confidence`;
      $("scope-name").textContent = f.name;
      $("scope-coords").textContent = fmtCoord(f.lat, f.lon);
      const tk = s.result && s.result.taken, wt = s.result && s.result.when_text;
      note.textContent = (f.radius_known ? `Radius ${fmtRadius(f.radius_km)}` : "No radius given") + (f.heading != null ? `, camera heading ${Math.round(f.heading)}°` : "")
        + (tk ? `. Taken ${tk.text}${tk.time ? " " + tk.time : ""} (${tk.confidence})` : (wt ? `. When: ${wt.length > 110 ? wt.slice(0, 110) + "…" : wt}` : ". When: not given")) + ".";
      const tr = $("scope-truth"), missed = generatedTruth(s, "Truth");
      if (missed) {
        tr.hidden = false;
        tr.textContent = missed;
      } else if (s.truth && s.truth.latitude != null) {
        tr.hidden = false;
        tr.textContent = `Truth: ${truthName(s.truth)}, ${fmtCoord(s.truth.latitude, s.truth.longitude)}` + (s.truth.error_km != null ? `, ${fmtRadius(s.truth.error_km)} from the answer` : "") + ".";
      } else tr.hidden = true;
      return;
    }
    const pct = Math.round((f.share || 0) * 100);
    $("scope-level").textContent = f.label === "gut call" ? `Gut call leader, ${pct}% (no board yet)` : `Leading ${f.label || f.level}, ${pct}% of the open candidates`;
    $("scope-name").textContent = f.name;
    $("scope-coords").textContent = fmtCoord(f.lat, f.lon);
    note.textContent = f.placed_by && f.placed_by !== f.name
      ? `${f.name} has no coordinates on the board yet; showing ${f.placed_by} (${fmtRadius(f.radius_km)}).`
      : `Extent about ${fmtRadius(f.radius_km)}.`;
  }

  function truthName(t) {
    return [t.city, t.region, t.country].filter(Boolean).join(", ") || "recorded location";
  }

  function renderAnswer(s) {
    const box = $("answer");
    const r = s.result;
    const gen = generated(s);
    setMapLink("answer-map", s.status === "completed" && r && !gen ? mapsURL(r.latitude, r.longitude) : null);
    $("answer-badge").hidden = !gen;                      // red only on a finished generated outcome
    if (gen) {
      const g = r.generated || {};
      box.hidden = false;
      $("answer-place").textContent = "Generated image: no real place";
      $("answer-coords").textContent = "";
      $("answer-when").innerHTML = `<b>Basis:</b> ${esc(g.basis || "not recorded")}`;
      $("answer-detail").textContent = (g.score != null ? `Detector ${Number(g.score).toFixed(2)}${g.model ? " (" + g.model + ")" : ""}: a ranking, not the basis`
        : g.skipped ? `Detector skipped (${g.skipped})` : "Detector not run")
        + (g.override ? `; the operator had said real (${g.override.reason})` : "") + ".";
      const tr = $("answer-truth"), line = generatedTruth(s, "Truth recorded");
      tr.hidden = !line; tr.textContent = line;
      $("answer-evidence").hidden = true;
      return;
    }
    if (s.status !== "completed" || !r || r.latitude == null) { box.hidden = true; return; }
    box.hidden = false;
    $("answer-place").textContent = [r.city_or_nearest_locality, r.region, r.country].filter(Boolean).join(", ");
    $("answer-coords").textContent = fmtCoord(r.latitude, r.longitude);
    const bits = [`Confidence ${r.confidence || "unrated"}`];
    if (r.supporting_artifacts === 0 || r.accepted_unverified) bits.push("unverified estimate");
    if (r.radius_m) bits.push(`radius ${fmtRadius(r.radius_m / 1000)}`);
    if (r.heading != null) bits.push(`heading ${Math.round(r.heading)}°`);
    if (r.heading == null && r.heading_hint) bits.push(`heading unknown, best match looks at ${Math.round(r.heading_hint.heading)}° (suggested)`);
    $("answer-detail").textContent = bits.join(", ") + ".";
    const w = $("answer-when");
    if (r.taken) {
      w.innerHTML = `<b>Taken:</b> ${esc(r.taken.text)}${r.taken.time ? " " + esc(r.taken.time) : ""} <span class="muted">(${esc(r.taken.confidence)}${r.taken.basis ? ": " + esc(r.taken.basis) : ""})</span>`;
    } else if (r.when_text) {
      w.innerHTML = `<b>Taken:</b> not pinned to a date <span class="muted">(report: ${esc(r.when_text)})</span>`;
    } else {
      w.innerHTML = `<b>Taken:</b> <span class="muted">not given</span>`;
    }
    const tr = $("answer-truth"), missed = generatedTruth(s, "Truth recorded");
    if (missed) {
      tr.hidden = false;
      tr.textContent = missed;
    } else if (s.truth && s.truth.latitude != null) {
      tr.hidden = false;
      const hits = [s.truth.country_hit === true ? "country right" : s.truth.country_hit === false ? "country wrong" : null,
                    s.truth.region_hit === true ? "region right" : s.truth.region_hit === false ? "region wrong" : null].filter(Boolean).join(", ");
      tr.textContent = `Truth recorded: ${truthName(s.truth)}, ${fmtCoord(s.truth.latitude, s.truth.longitude)}` +
        (s.truth.error_km != null ? `, ${fmtRadius(s.truth.error_km)} from the answer` : "") + (hits ? ` (${hits})` : "") + ".";
    } else tr.hidden = true;
    const ev = s.artifacts.find((a) => /^evidence.*\.(jpe?g|png)$/i.test(a.path));
    const link = $("answer-evidence");
    if (ev) { link.hidden = false; link.href = ev.url; $("answer-evidence-img").src = ev.url; link.onclick = (e) => { e.preventDefault(); openLightbox(ev.url, ev.path); }; }
    else link.hidden = true;
  }

  function renderCandidates(s) {
    const box = $("candidates");
    if (!s.candidates.length) {
      box.innerHTML = '<p class="empty">Nothing yet. The gut call in report.md and the first board.py calls fill this list.</p>';
      return;
    }
    const gut = s.candidates_source === "gut";
    const notes = (s.coherence || []).map((n) => `<p class="empty">${esc(n)}</p>`).join("");
    const byLevel = new Map();
    for (const c of s.candidates) { if (!byLevel.has(c.level)) byLevel.set(c.level, []); byLevel.get(c.level).push(c); }
    let html = "";
    for (const [level, rows] of byLevel) {
      const open = rows.filter((r) => !r.excluded).length;
      const unplaced = rows.filter((r) => !r.excluded && !r.dormant && !r.superseded && !r.has_geo).length;
      const placing = unplaced ? (unplaced === open ? ", none placed on the globe yet" : `, ${unplaced} not placed on the globe yet`) : "";
      html += `<div class="level"><p class="level-name">${gut ? `gut call, before any board entry: ${rows.length} countries` : `${esc(rows[0].label)}: ${open} open of ${rows.length}${placing}`}</p>`;
      rows.slice(0, 12).forEach((r, i) => {
        const ev = r.n_ev ? `<span class="ev">${r.n_verified ? `<b>${r.n_verified} verified</b> of ` : ""}${r.n_ev} evidence</span>` : "";
        html += `<div class="cand${r.excluded || r.superseded || r.dormant ? " excluded" : ""}${i === 0 && !r.excluded ? " lead" : ""}">
          <span class="name">${esc(r.name)}</span><span class="share">${r.excluded ? "excluded" : r.superseded ? "superseded" : r.dormant ? "not pursued" : r.settled ? "settled" : Math.round(r.share * 100) + "%"}</span>
          <span class="bar"><i style="width:${(r.excluded ? 0 : r.share * 100).toFixed(1)}%"></i></span>${ev}</div>`;
      });
      if (rows.length > 12) html += `<p class="empty">${rows.length - 12} more at this level.</p>`;
      html += "</div>";
    }
    box.innerHTML = notes + html;
  }

  function renderActivity(s) {
    const list = $("activity");
    const rows = s.activity.slice(0, 60);
    if (!rows.length) { list.innerHTML = '<li class="more">Nothing yet.</li>'; return; }
    list.innerHTML = rows.map((e) => {
      const time = `<time>${esc(fmtTime(e.time))}</time>`;
      if (e.source === "file") {
        const name = e.text.split("/").pop();
        const link = `<a href="${esc(e.url)}" target="_blank" rel="noopener" title="${esc(e.text)}">${esc(name)}</a>`;
        const thumb = e.kind === "image" ? `<button class="thumb-btn" type="button" data-url="${esc(e.url)}" data-cap="${esc(e.text)}"><img class="thumb" loading="lazy" decoding="async" src="${esc(e.url)}" alt=""></button>` : "<span></span>";
        return `<li class="file">${time}<span class="text">${link}</span>${thumb}</li>`;
      }
      return `<li class="${e.source}">${time}<span class="text">${esc(e.text)}</span><span></span></li>`;
    }).join("") + (s.activity.length > 60 ? `<li class="more">${s.activity.length - 60} earlier entries not shown.</li>` : "");
  }

  // minimal markdown: headings, lists, bold, code, links, tables, html comments as muted notes
  function md(text) {
    if (!text) return "";
    const lines = text.replace(/\r/g, "").split("\n");
    let out = "", list = null, para = [], code = false, table = [];
    const inline = (s) => esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/&lt;!--\s*(.*?)\s*--&gt;/g, '<span class="fill">$1</span>');
    const flushPara = () => { if (para.length) { out += `<p>${inline(para.join(" "))}</p>`; para = []; } };
    const flushList = () => { if (list) { out += `</${list}>`; list = null; } };
    const flushTable = () => {
      if (!table.length) return;
      const rows = table.filter((r) => !/^\s*\|?\s*:?-{2,}/.test(r)).map((r) => r.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|"));
      out += "<table>" + rows.map((cells, i) => `<tr>${cells.map((c) => `<${i ? "td" : "th"}>${inline(c.trim())}</${i ? "td" : "th"}>`).join("")}</tr>`).join("") + "</table>";
      table = [];
    };
    for (const raw of lines) {
      if (raw.startsWith("```")) { flushPara(); flushList(); flushTable(); code = !code; out += code ? "<pre>" : "</pre>"; continue; }
      if (code) { out += esc(raw) + "\n"; continue; }
      const h = /^(#{1,3})\s+(.*)/.exec(raw);
      if (h) { flushPara(); flushList(); flushTable(); out += `<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`; continue; }
      if (/^\s*\|/.test(raw)) { flushPara(); flushList(); table.push(raw); continue; }
      flushTable();
      const li = /^\s*(?:[-*]|\d+\.)\s+(.*)/.exec(raw);
      if (li) { flushPara(); const kind = /^\s*\d/.test(raw) ? "ol" : "ul"; if (list !== kind) { flushList(); out += `<${kind}>`; list = kind; } out += `<li>${inline(li[1])}</li>`; continue; }
      if (!raw.trim()) { flushPara(); flushList(); continue; }
      flushList(); para.push(raw.trim());
    }
    flushPara(); flushList(); flushTable();
    return out;
  }

  let lastReport = null, lastRecon = null;
  function renderText(s) {
    if (s.report_md !== lastReport) { $("report").innerHTML = md(s.report_md) || '<p class="empty">report.md is empty.</p>'; lastReport = s.report_md; }
    if (s.recon_md !== lastRecon) { $("recon").innerHTML = md(s.recon_md) || '<p class="empty">recon.py has not written recon/recon.md yet.</p>'; lastRecon = s.recon_md; }
  }

  function applyGlobe(s) {
    stage.setTiles(s.tiles);
    stage.highlight = new Map();
    const finest = s.focus && !s.focus.final ? s.focus.level : null;
    const markers = [];
    // an ancestor with an open candidate below it is a container, not a place to show: its big circle would only hide the finer ones
    const hasOpenChild = new Set(s.candidates.filter((c) => !c.excluded && c.parent).map((c) => c.parent));
    s.candidates.forEach((c, i) => {
      if (c.level === "country" && c.iso2 && !c.excluded) stage.highlight.set(c.iso2, c.share);
      if (c.level !== "country" && c.has_geo && !(hasOpenChild.has(c.name) && !c.excluded))
        markers.push({ lat: c.lat, lon: c.lon, radius_km: c.radius_km, share: c.share, excluded: c.excluded, name: c.name, lead: finest === c.level && !c.excluded && s.candidates.find((x) => x.level === c.level && !x.excluded) === c });
    });
    // when the answer is in, only the answer stays on the map
    stage.markers = s.status === "completed" ? [] : markers;
    stage.data = Object.assign({ cameras: [], lines: [], points: [], images: [], areas: [], levels: [], matches: [], coverage: [] }, s.layers || {});
    stage.data.coverage = (stage.data.coverage || []).map((c) => Array.isArray(c) ? { lat: c[0], lon: c[1] } : c);   // snapshots made before the cards
    layerCounts(s);
    renderLevels(s);
    const focus = s.focus ? { ...s.focus } : null;
    if (s.truth && s.truth.latitude != null) {
      stage.truth = { lat: s.truth.latitude, lon: s.truth.longitude, name: truthName(s.truth) };
      if (focus && s.truth.error_km != null) {   // keep both the answer and the truth on screen, centred between them
        focus.view_radius_km = Math.max(focus.radius_km, s.truth.error_km * 0.75);
        focus.view_lat = (focus.lat + s.truth.latitude) / 2;
        focus.view_lon = Stage.wrapLon(focus.lon + Stage.wrapLon(s.truth.longitude - focus.lon) / 2);
      }
    } else stage.truth = null;
    stage.setFocus(focus);
    $("attribution").textContent = (TILE_SOURCES[s.tiles] || TILE_SOURCES.esri).credit;
  }

  function render(s) {
    state = s;
    startedAt = s.started_at ? Date.parse(s.started_at) : null;
    document.title = `${s.title}: ${s.stage}`;
    document.body.classList.toggle("running", !STATIC && s.status !== "completed");
    document.body.classList.toggle("static", STATIC);
    $("title").textContent = s.photos.length > 1 ? `${s.photos.length} photos, ${s.title} first` : s.title;
    renderPhotos(s);
    renderMeta();
    renderStages(s);
    renderScope(s);
    $("now").textContent = s.warning ? `Attention: ${s.warning}` : (s.now || "Waiting for the first command.");
    const ck = generated(s) ? [] : (s.checks || []);      // a generated image has no place left to check
    $("checks").hidden = !ck.length;
    if (ck.length) {
      // the same four states as `photo_session.py checks`: a waived or skipped check no longer blocks finish
      const state = (c) => c.done ? "✓" : c.skipped ? `skipped: ${c.skipped}` : (c.waived_by || []).length ? `waived by ${c.waived_by[0]}` : "missing";
      $("checks").innerHTML = "Required checks: " + ck.map((c) => `<span class="${state(c) === "missing" ? "check-missing" : "check-done"}" title="${esc(c.why || "")}">${esc(c.name)} ${esc(state(c))}</span>`).join(" · ");
    }
    // the detector before the finish: model status, never a verdict; the operator's "it is real" replaces it
    const ad = s.aidet, ov = s.generated_override;
    const flag = s.status === "completed" ? "" : ov ? "Operator: real, continue"
      : ad && ad.flagged ? `Detector ${Number(ad.p_ai).toFixed(2)} generated-like: a ranking, not a verdict` : "";
    $("aidet").hidden = !flag;
    $("aidet").textContent = flag;
    $("aidet").title = ov ? ov.reason || "" : ad && ad.model ? `${ad.model}, threshold ${ad.threshold}` : "";
    renderAnswer(s);
    renderCandidates(s);
    renderActivity(s);
    renderSkyline(s);
    renderGallery(s);
    renderText(s);
    applyGlobe(s);
  }

  // ---------------------------------------------------------------- lightbox

  function openLightbox(url, caption) {
    $("lightbox-img").src = url; $("lightbox-img").alt = caption; $("lightbox-cap").textContent = caption;
    $("lightbox").hidden = false; $("lightbox-close").focus();
  }
  function closeLightbox() { $("lightbox").hidden = true; $("lightbox-img").src = ""; }
  $("lightbox").addEventListener("click", (e) => { if (e.target.id !== "lightbox-img") closeLightbox(); });
  $("lightbox-close").addEventListener("click", closeLightbox);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeLightbox(); });
  $("photos").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) openLightbox(b.dataset.url, b.dataset.cap);
  });
  $("folder").addEventListener("click", async () => {
    const b = $("folder"), text = b.textContent;
    if (STATIC) {
      try { await navigator.clipboard.writeText(text); b.textContent = "Path copied"; } catch (err) { b.textContent = text; }
      setTimeout(() => { b.textContent = text; }, 1800);
      return;
    }
    try {
      const r = await fetch("/api/open", { method: "POST" });
      b.textContent = r.ok ? "Opened in your file manager" : "Could not open the folder from here";
    } catch (err) {
      b.textContent = "Could not open the folder from here";
    }
    setTimeout(() => { b.textContent = text; }, 1800);
  });
  stage.onSelect = showCard;
  $("card-close").addEventListener("click", () => { stage.selected = null; showCard(null); });
  $("analysis").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) openLightbox(b.dataset.url, b.dataset.cap); });
  $("skyline").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) openLightbox(b.dataset.url, b.dataset.cap); });
  for (const name of ["matches", "coverage", "marks"]) {
    $(`layer-${name}`).addEventListener("click", () => {
      stage.layers[name] = !stage.layers[name];
      $(`layer-${name}`).classList.toggle("on", stage.layers[name]);
      if (!stage.layers[name]) { stage.selected = null; showCard(null); return; }
      // switching a layer on takes the view to its points (Follow returns to the analysis)
      const pts = name === "coverage" ? stage.data.coverage
        : name === "matches" ? stage.data.matches.map((m) => [m.lat, m.lon])
        : [...stage.data.cameras, ...stage.data.points, ...stage.data.images, ...stage.data.areas.flatMap((a) => a.features || [])]
          .filter((m) => m.lat != null).map((m) => [m.lat, m.lon]);
      if (pts.length) { const e = Stage.extent(pts); stage.flyTo(e.lat, e.lon, Math.max(e.radius_km * 1.4, 0.3)); }
    });
  }
  $("levels").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    stage.level = b.dataset.level === "" ? null : Number(b.dataset.level);
    if (state) renderLevels(state);
  });
  setInterval(placeCard, 50);
  $("zoom-in").addEventListener("click", () => stage.nudgeZoom(1));
  $("zoom-out").addEventListener("click", () => stage.nudgeZoom(-1));
  $("follow").addEventListener("click", () => stage.follow());
  setInterval(() => { $("follow").disabled = !stage.controlled; }, 300);
  $("activity").addEventListener("click", (e) => {
    const b = e.target.closest("button.thumb-btn");
    if (b) openLightbox(b.dataset.url, b.dataset.cap);
  });

  // ---------------------------------------------------------------- polling

  let failures = 0;
  $("close-viewer").addEventListener("click", async () => {
    try { await fetch("/api/stop", { method: "POST" }); } catch (err) { /* the socket may close before the reply */ }
    stopped = true;
    document.body.classList.remove("running");
    document.body.classList.add("stopped");
    $("live").hidden = true;
    $("now").textContent = "Viewer closed. The analysis continues in the agent; run viewer.py serve on this session to reopen the page.";
  });
  async function poll() {
    if (stopped) return;
    try {
      const r = await fetch("/api/state", { headers: etag ? { "If-None-Match": etag } : {}, cache: "no-store" });
      if (r.status === 200) {
        etag = r.headers.get("ETag");
        const s = await r.json();
        render(s);
        if (s.stopping) {                               // the server's last word: final state shown, no more polling
          stopped = true;
          document.body.classList.remove("running");
          document.body.classList.add("stopped");
          $("live").hidden = true;
          $("now").textContent = (s.status === "completed" ? "Analysis finished; the viewer server has stopped. " : "Viewer server stopped; the analysis may go on. ")
            + "Offline copy: " + (s.snapshot || "viewer.html in the session folder") + ".";
          return;
        }
      }
      failures = 0;
    } catch (err) {
      failures += 1;
      if (failures === 3) $("now").textContent = "The viewer server is gone. If the analysis finished, open viewer.html in the session folder; otherwise run viewer.py serve on it again.";
    } finally {
      if (!stopped) setTimeout(poll, 2000);
    }
  }
  setInterval(renderMeta, 1000);
  if (STATIC) render(window.GEO_STATE); else poll();
})();
