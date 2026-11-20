// Interactive demo: replays stored benchmark records. No live telemetry; nothing is computed in the browser except drawing.
(function () {
  "use strict";
  const root = document.getElementById("demo");
  if (!root) return;
  const COLORS = { rules: "var(--s-rules)", robust_z: "var(--s-z)", model: "var(--s-model)" };
  const NAMES = { rules: "Respite rules (shipped)", robust_z: "Robust z baseline", model: "Trained model (draw 101)" };
  const MEAS = [
    ["rec_ratio", "Recorder rate / declared rate", 2],
    ["max_gap_s", "Longest gap between rows (s)", 2],
    ["cam_rate_ratio_min", "Slowest camera rate / declared", 2],
    ["cam_offset_max_s", "Camera start/end offset (s)", 2],
    ["delay_ms", "Arms trail commands (ms)", 0],
    ["n_cams", "Camera streams present", 0],
  ];

  function el(tag, attrs, text) {
    const e = document.createElement(tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function spark(values, affected, digits) {
    const W = 280, H = 70, P = 6;
    const ok = values.map((v, i) => [i, v]).filter((p) => p[1] !== null && p[1] !== undefined && isFinite(p[1]));
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("role", "img");
    if (!ok.length) {
      const t = document.createElementNS(svg.namespaceURI, "text");
      t.setAttribute("x", 6); t.setAttribute("y", 38); t.setAttribute("fill", "var(--ink-3)"); t.setAttribute("font-size", "12");
      t.textContent = "not measured in this format";
      svg.appendChild(t);
      svg.setAttribute("aria-label", "not measured in this format");
      return svg;
    }
    let lo = Math.min(...ok.map((p) => p[1])), hi = Math.max(...ok.map((p) => p[1]));
    const rawLo = lo, rawHi = hi;
    if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
    const x = (i) => P + (i * (W - 2 * P)) / (values.length - 1);
    const y = (v) => H - P - ((v - lo) * (H - 2 * P)) / (hi - lo);
    const step = (W - 2 * P) / (values.length - 1);
    affected.forEach((a, i) => {
      if (!a) return;
      const r = document.createElementNS(svg.namespaceURI, "rect");
      r.setAttribute("x", x(i) - step / 2); r.setAttribute("y", 0); r.setAttribute("width", step); r.setAttribute("height", H);
      r.setAttribute("fill", "var(--accent-soft)");
      svg.appendChild(r);
    });
    for (const [val, yy] of (rawHi === rawLo ? [[rawHi, 10]] : [[rawHi, 10], [rawLo, H - 2]])) {
      const t = document.createElementNS(svg.namespaceURI, "text");
      t.setAttribute("x", W - 2); t.setAttribute("y", yy); t.setAttribute("text-anchor", "end"); t.setAttribute("class", "axis");
      t.textContent = val.toFixed(digits);
      svg.appendChild(t);
    }
    const path = document.createElementNS(svg.namespaceURI, "polyline");
    path.setAttribute("points", ok.map((p) => `${x(p[0])},${y(p[1])}`).join(" "));
    path.setAttribute("fill", "none"); path.setAttribute("stroke", "var(--ink)"); path.setAttribute("stroke-width", "1.6");
    svg.appendChild(path);
    for (const p of ok) {
      const c = document.createElementNS(svg.namespaceURI, "circle");
      c.setAttribute("cx", x(p[0])); c.setAttribute("cy", y(p[1])); c.setAttribute("r", 2.4); c.setAttribute("fill", "var(--ink)");
      const tt = document.createElementNS(svg.namespaceURI, "title");
      tt.textContent = `episode ${p[0] + 1}: ${p[1].toFixed(digits)}`;
      c.appendChild(tt);
      svg.appendChild(c);
    }
    svg.setAttribute("aria-label", `from ${ok[0][1].toFixed(digits)} to ${ok[ok.length - 1][1].toFixed(digits)} over ${values.length} episodes`);
    return svg;
  }

  function show(s) {
    const out = document.getElementById("demo-out");
    out.innerHTML = "";
    const head = el("p");
    const tag = el("span", { class: "tag " + (s.kind === "evaluation record" ? "syn" : "ill") }, s.kind === "evaluation record" ? "Evaluation record" : "Illustrative");
    head.appendChild(tag);
    head.appendChild(document.createTextNode(" " + s.description));
    out.appendChild(head);
    const charts = el("div", { class: "charts" });
    for (const [key, label, digits] of MEAS) {
      const c = el("div", { class: "chart" });
      c.appendChild(el("h4", {}, label));
      c.appendChild(spark(s.steps.map((st) => st.m[key]), s.steps.map((st) => st.affected), digits));
      charts.appendChild(c);
    }
    out.appendChild(charts);
    const hit = s.steps.filter((st) => st.affected).map((st) => st.index + 1);
    const leg = el("p", { class: "kbd" }, hit.length ? `Shaded: the episodes the fault was written into (${hit.join(", ")}). Small numbers: the lowest and highest value shown.` : "No fault was written into this sequence. Small numbers: the lowest and highest value shown.");
    out.appendChild(leg);
    const strips = el("div", { class: "explain" });
    strips.appendChild(el("h3", {}, "What each detector said after every episode"));
    for (const d of ["rules", "robust_z", "model"]) {
      const row = el("div", { class: "status-row" });
      const name = el("div");
      const sw = el("span", { class: "swatch" });
      sw.style.background = COLORS[d];
      name.appendChild(sw);
      name.appendChild(document.createTextNode(NAMES[d]));
      row.appendChild(name);
      const cells = el("div", { class: "cells", role: "list" });
      s.detectors[d].forEach((o, i) => {
        const c = el("div", { class: "cell" + (o.alert ? " alert" : "") + (i === s.onset ? " onset" : ""), role: "listitem",
          title: `episode ${i + 1}: ${o.alert ? "ALERT " + (o.category || "") : "no alert"}` });
        c.setAttribute("aria-label", `episode ${i + 1}: ${o.alert ? "alert, " + (o.category || "no category") : "no alert"}`);
        cells.appendChild(c);
      });
      row.appendChild(cells);
      strips.appendChild(row);
      const first = s.detectors[d].findIndex((o, i) => o.alert && (s.onset === null || i >= s.onset));
      const pre = s.onset !== null && s.detectors[d].slice(0, s.onset).some((o) => o.alert);
      let why;
      if (first < 0) why = pre ? "Already alerting before the fault started; no new alert after it." : "No alert after the fault started.";
      else why = `First alert after episode ${first + 1}` + (s.onset !== null ? ` (${first - s.onset + 1} episode(s) after the fault started)` : "") +
        `: ${s.detectors[d][first].category || "no category"}. ${s.detectors[d][first].why || ""}`;
      strips.appendChild(el("p", { class: "kbd" }, why));
    }
    out.appendChild(strips);
  }

  fetch("data/demo.json").then((r) => r.json()).then((data) => {
    const bar = document.getElementById("demo-controls");
    data.scenarios.forEach((s, i) => {
      const b = el("button", { type: "button", "aria-pressed": i === 0 ? "true" : "false" }, s.label);
      b.addEventListener("click", () => {
        bar.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", "false"));
        b.setAttribute("aria-pressed", "true");
        show(s);
      });
      bar.appendChild(b);
    });
    show(data.scenarios[0]);
  }).catch(() => {
    document.getElementById("demo-out").textContent = "The demo data could not be loaded.";
  });
})();
