"""
Graphique animé du patrimoine (SVG + JavaScript, sans dépendance).
Les deux courbes se dessinent année par année à chaque nouvelle simulation.
"""

import json

GABARIT = r"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  html, body {margin: 0; background: transparent; font-family: 'Inter', -apple-system, sans-serif; color: #efefef;}
  #wrap {position: relative;}
  svg {display: block; width: 100%; overflow: visible;}
  .axe text {fill: #b0b0b0; font-size: 12px;}
  .titre-axe {fill: #b0b0b0; font-size: 12px;}
  #compteur {position: absolute; left: 78px; top: 4px; font-size: 13px; color: #b0b0b0;}
  #compteur b {color: #efefef; font-size: 15px;}
  #rejouer {position: absolute; right: 6px; top: 0; background: rgba(255,255,255,.08); color: #efefef;
            border: 1px solid rgba(255,255,255,.18); border-radius: 999px; padding: 5px 12px; font: 500 12px Inter, sans-serif;
            cursor: pointer;}
  #rejouer:hover {background: rgba(255,255,255,.16);}
  #legende {position: absolute; left: 50%; transform: translateX(-50%); top: 2px; display: flex; gap: 18px; font-size: 13px;}
  #legende span {display: inline-flex; align-items: center; gap: 6px;}
  #legende i {display: inline-block; width: 14px; height: 3px; border-radius: 2px;}
  #bulle {position: absolute; pointer-events: none; background: #1b1e23; border: 1px solid #474c55; border-radius: 10px;
          padding: 8px 12px; font-size: 12.5px; line-height: 1.6; opacity: 0; transition: opacity .12s; white-space: nowrap;
          box-shadow: 0 6px 18px rgba(0,0,0,.35);}
  #bulle .an {color: #b0b0b0; font-weight: 600; margin-bottom: 2px;}
  #bulle .v {font-weight: 700; font-variant-numeric: tabular-nums;}
  @media (prefers-reduced-motion: reduce) {#rejouer {display: none;}}
</style></head><body>
<div id="wrap">
  <div id="compteur"></div>
  <div id="legende"><span><i style="background:#338ced"></i>Acheter</span><span><i style="background:#e76624"></i>Louer</span></div>
  <button id="rejouer">▶ Rejouer</button>
  <svg id="g"></svg>
  <div id="bulle"></div>
</div>
<script>
const D = __DATA__;
const COUL = {acheter: "#338ced", louer: "#e76624"};
const H = 400, M = {l: 64, r: 86, t: 36, b: 38};
const svg = document.getElementById("g"), bulle = document.getElementById("bulle"),
      compteur = document.getElementById("compteur"), wrap = document.getElementById("wrap");
const NS = "http://www.w3.org/2000/svg";
const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let W, sx, sy, anim = null;

function el(nom, attrs, parent) {
  const e = document.createElementNS(NS, nom);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  (parent || svg).appendChild(e); return e;
}
function court(v) {
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(a >= 1e7 ? 1 : 2).replace(/\.?0+$/, "") + " M";
  if (a >= 1e3) return Math.round(v / 1e3) + " k";
  return Math.round(v).toString();
}
function chf(v) { return (v < 0 ? "−" : "") + Math.round(Math.abs(v)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, "'") + " CHF"; }
function graduations(min, max, n) {
  const pas0 = (max - min) / n, p = Math.pow(10, Math.floor(Math.log10(pas0))), r = pas0 / p;
  const pas = (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * p;
  const out = []; for (let v = Math.floor(min / pas) * pas; v <= max + 1e-9; v += pas) out.push(v);
  return out;
}

function construire() {
  W = wrap.clientWidth || 700;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("height", H);
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const n = D.annees.length, x0 = n > 1 ? D.annees[0] : 0, x1 = D.annees[n - 1];
  const tous = D.acheter.concat(D.louer);
  let ymin = Math.min(0, ...tous), ymax = Math.max(...tous);
  const ticks = graduations(ymin, ymax, 5); ymin = ticks[0]; ymax = Math.max(ymax, ticks[ticks.length - 1]);
  sx = v => M.l + (v - x0) / (x1 - x0 || 1) * (W - M.l - M.r);
  sy = v => H - M.b - (v - ymin) / (ymax - ymin || 1) * (H - M.t - M.b);

  const axe = el("g", {class: "axe"});
  ticks.forEach(t => {
    el("line", {x1: M.l, x2: W - M.r, y1: sy(t), y2: sy(t), stroke: t === 0 ? "rgba(255,255,255,.28)" : "rgba(255,255,255,.07)"}, axe);
    const tx = el("text", {x: M.l - 10, y: sy(t) + 4, "text-anchor": "end"}, axe); tx.textContent = court(t);
  });
  const pasX = n > 20 ? 5 : n > 10 ? 2 : 1;
  D.annees.forEach(a => { if (a % pasX === 0 || a === x1) {
    const tx = el("text", {x: sx(a), y: H - M.b + 20, "text-anchor": "middle"}, axe); tx.textContent = a; } });
  const ta = el("text", {x: (M.l + W - M.r) / 2, y: H - 4, "text-anchor": "middle", class: "titre-axe"}); ta.textContent = "Années";

  // ligne d'équilibre (apparaît à la fin)
  const eqG = el("g", {opacity: 0, style: "transition: opacity .6s"});
  if (D.eq) {
    el("line", {x1: sx(D.eq), x2: sx(D.eq), y1: M.t, y2: H - M.b, stroke: "#b0b0b0", "stroke-dasharray": "5 5"}, eqG);
    const t = el("text", {x: sx(D.eq) + 6, y: M.t + 12, fill: "#b0b0b0", "font-size": 12}, eqG);
    t.textContent = "Équilibre : année " + D.eq;
  }
  const courbes = {}, tetes = {}, etiq = {};
  ["louer", "acheter"].forEach(k => {
    courbes[k] = el("path", {fill: "none", stroke: COUL[k], "stroke-width": 2.6, "stroke-linejoin": "round", "stroke-linecap": "round"});
    tetes[k] = el("circle", {r: 5.5, fill: COUL[k], stroke: "#2b2e34", "stroke-width": 2});
    etiq[k] = el("text", {fill: "#efefef", "font-size": 12.5, "font-weight": 700});
  });
  // couche de survol
  const curseur = el("line", {y1: M.t, y2: H - M.b, stroke: "rgba(255,255,255,.35)", opacity: 0});
  const pts = {acheter: el("circle", {r: 5, fill: COUL.acheter, stroke: "#fff", "stroke-width": 1.5, opacity: 0}),
               louer: el("circle", {r: 5, fill: COUL.louer, stroke: "#fff", "stroke-width": 1.5, opacity: 0})};
  const zone = el("rect", {x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b, fill: "transparent"});

  function dessiner(p) {               // p de 0 à 1
    const pos = p * (n - 1), i = Math.floor(pos), f = pos - i;
    ["acheter", "louer"].forEach(k => {
      const v = D[k]; let d = "";
      for (let j = 0; j <= i; j++) d += (j ? "L" : "M") + sx(D.annees[j]) + "," + sy(v[j]);
      let hx = sx(D.annees[i]), hv = v[i];
      if (i < n - 1) { hx = sx(D.annees[i] + f * (D.annees[i + 1] - D.annees[i])); hv = v[i] + f * (v[i + 1] - v[i]); d += "L" + hx + "," + sy(hv); }
      if (n === 1) d = "M" + sx(D.annees[0]) + "," + sy(v[0]) + "l0.1,0";
      courbes[k].setAttribute("d", d);
      tetes[k].setAttribute("cx", hx); tetes[k].setAttribute("cy", sy(hv));
      etiq[k].setAttribute("x", hx + 10); etiq[k].setAttribute("y", sy(hv) + 4);
      etiq[k].textContent = p < 1 ? court(hv) : (k === "acheter" ? "Acheter" : "Louer");
    });
    // évite que les deux étiquettes se chevauchent
    const ya = +etiq.acheter.getAttribute("y"), yl = +etiq.louer.getAttribute("y");
    if (Math.abs(ya - yl) < 16) { const m = (ya + yl) / 2, h = ya <= yl ? -1 : 1;
      etiq.acheter.setAttribute("y", m + h * 9); etiq.louer.setAttribute("y", m - h * 9); }
    const an = Math.min(n, Math.round(pos) + 1) - 1;
    const ec = D.acheter[an] - D.louer[an];
    compteur.innerHTML = `Année <b>${D.annees[an]}</b> &nbsp;·&nbsp; ${ec >= 0 ? "Acheter" : "Louer"} en tête de <b>${chf(Math.abs(ec))}</b>`;
    if (p >= 1) { eqG.setAttribute("opacity", 1); tetes.acheter.setAttribute("opacity", 0); tetes.louer.setAttribute("opacity", 0); }
    else { eqG.setAttribute("opacity", 0); tetes.acheter.setAttribute("opacity", 1); tetes.louer.setAttribute("opacity", 1); }
  }

  function jouer() {
    if (anim) cancelAnimationFrame(anim);
    if (reduit) { dessiner(1); return; }
    const duree = 1400 + 45 * n, t0 = performance.now();
    const pas = t => { const q = Math.min(1, (t - t0) / duree); dessiner(1 - Math.pow(1 - q, 2.2)); if (q < 1) anim = requestAnimationFrame(pas); };
    anim = requestAnimationFrame(pas);
  }
  document.getElementById("rejouer").onclick = jouer;

  zone.addEventListener("mousemove", e => {
    const r = svg.getBoundingClientRect(), mx = (e.clientX - r.left) * (W / r.width);
    let k = 0, best = Infinity; D.annees.forEach((a, j) => { const dd = Math.abs(sx(a) - mx); if (dd < best) { best = dd; k = j; } });
    const x = sx(D.annees[k]);
    curseur.setAttribute("x1", x); curseur.setAttribute("x2", x); curseur.setAttribute("opacity", 1);
    ["acheter", "louer"].forEach(c => { pts[c].setAttribute("cx", x); pts[c].setAttribute("cy", sy(D[c][k])); pts[c].setAttribute("opacity", 1); });
    const ec = D.acheter[k] - D.louer[k];
    bulle.innerHTML = `<div class="an">Année ${D.annees[k]}</div>
      <div><span style="color:${COUL.acheter}">●</span> Acheter <span class="v">${chf(D.acheter[k])}</span></div>
      <div><span style="color:${COUL.louer}">●</span> Louer <span class="v">${chf(D.louer[k])}</span></div>
      <div style="color:#b0b0b0">Écart <span class="v" style="color:#efefef">${ec >= 0 ? "+" : ""}${chf(ec)}</span></div>`;
    const px = x * (r.width / W);
    bulle.style.left = (px > r.width - 200 ? px - bulle.offsetWidth - 14 : px + 14) + "px";
    bulle.style.top = "40px"; bulle.style.opacity = 1;
  });
  zone.addEventListener("mouseleave", () => {
    curseur.setAttribute("opacity", 0); pts.acheter.setAttribute("opacity", 0); pts.louer.setAttribute("opacity", 0); bulle.style.opacity = 0;
  });
  return jouer;
}

let rejouer = construire(); rejouer();
let tempo; window.addEventListener("resize", () => { clearTimeout(tempo); tempo = setTimeout(() => { construire()(); }, 200); });
</script></body></html>
"""


def graphique_anime(annees, acheter, louer, eq):
    data = {"annees": [int(a) for a in annees],
            "acheter": [round(float(v)) for v in acheter],
            "louer": [round(float(v)) for v in louer],
            "eq": int(eq) if eq else None}
    return GABARIT.replace("__DATA__", json.dumps(data))
