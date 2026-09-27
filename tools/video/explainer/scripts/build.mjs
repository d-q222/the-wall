// Builds index.html from scripts/narration.json + audio/durations.json.
// Scene length = real voice length + 1.2 s of air; captions are phrase cues timed
// by character share of each scene's voice file. Numbers on screen are copied from
// evals/bakeoff/README.md (Results) and evals/independent/README.md (pooled + hard set).
import { readFileSync, writeFileSync } from "node:fs";
const root = new URL("..", import.meta.url).pathname;
const { scenes } = JSON.parse(readFileSync(root + "scripts/narration.json", "utf8"));
const dur = JSON.parse(readFileSync(root + "audio/durations.json", "utf8"));
const LEAD = 0.4, PAD = 1.2, END = 4.0;

let t = 0;
const S = {};
for (const s of scenes) {
  const d = Math.ceil((dur[s.id] + PAD) * 10) / 10;
  S[s.id] = { start: +t.toFixed(2), dur: d, text: s.text, audio: dur[s.id] };
  t += d;
}
S.end = { start: +t.toFixed(2), dur: END };
const TOTAL = +(t + END).toFixed(2);

// ---------- captions ----------
function cues(text) {
  const words = text.split(" ");
  const out = [];
  let cur = [];
  for (const w of words) {
    cur.push(w);
    const len = cur.join(" ").length;
    if ((/[.,:;?]$/.test(w) && len > 22) || len > 44) { out.push(cur.join(" ")); cur = []; }
  }
  if (cur.length) out.push(cur.join(" "));
  return out;
}
let caps = "";
let ci = 0;
for (const s of scenes) {
  const sc = S[s.id];
  const parts = cues(s.text);
  const total = parts.reduce((a, p) => a + p.length, 0);
  let c = sc.start + LEAD;
  for (const p of parts) {
    const d = (p.length / total) * sc.audio;
    caps += `<div class="cc clip" data-start="${c.toFixed(2)}" data-duration="${d.toFixed(2)}" data-track-index="8"><span>${p.replace(/&/g, "&amp;")}</span></div>\n`;
    c += d; ci++;
  }
}

// ---------- helpers ----------
const clip = (id, start, d, track, inner, cls = "") =>
  `<div id="${id}" class="clip ${cls}" data-start="${start.toFixed(2)}" data-duration="${d.toFixed(2)}" data-track-index="${track}">${inner}</div>`;
const card = (id, sid, a, b, phrase) => clip(id, S[sid].start + a, b - a, 3, `<div class="nc-in"><p>${phrase}</p></div>`, "ncard");
const mark = (size = 150) => `<div class="mark" style="width:${size}px;height:${size}px"><svg viewBox="0 0 100 100" width="${size}" height="${size}"><circle cx="50" cy="50" r="46" fill="#FBFBF9" stroke="#1F4E9E" stroke-width="6"/><rect x="27" y="30" width="12" height="42" rx="1.5" fill="#14213D"/><rect x="42" y="26" width="12" height="46" rx="1.5" fill="#1F4E9E"/><rect x="57" y="32" width="12" height="40" rx="1.5" fill="#14213D"/><rect x="72" y="22" width="4" height="54" fill="#C2410C"/></svg></div>`;
const sw = (id, a, type) => `<span class="sw" id="${id}"><span class="a">${a}</span><span class="b">${"#".repeat(Math.min(a.length, 14))}</span><span class="c">[${type}]</span></span>`;

// ---------- scenes ----------
const sc = {};
sc.s1 = `<div class="center col">
  <div id="s1-mark">${mark(190)}</div>
  <div id="s1-name" class="firm">Okafor &amp; Lind Immigration</div>
  <div id="s1-shelf" class="shelf">${Array.from({ length: 7 }, (_, i) => `<div class="binder" id="s1-b${i}"><span>O-1</span></div>`).join("")}</div>
</div>
<div id="s1-agenda" class="agenda">
  <div class="ag-head">${mark(84)}<span>Today</span></div>
  <div class="ag" id="s1-a0"><b>1</b>Take out private details</div>
  <div class="ag" id="s1-a1"><b>2</b>Catch the sneaky ones</div>
  <div class="ag" id="s1-a2"><b>3</b>Lock each client’s files</div>
</div>`;

sc.s2 = `<div class="label" id="s2-l1">Find the private details</div>
<div class="label" id="s2-l2">What stays, what goes</div>
<div id="s2-laptop" class="laptop"><div class="screen"><div class="bar"></div>
  <div class="rec">
   <div class="row"><span class="k">Beneficiary</span><span class="v" id="s2-v0">Adaeze Umeh</span></div>
   <div class="row"><span class="k">A-number</span><span class="v" id="s2-v1">A134-902-661</span></div>
   <div class="row"><span class="k">USCIS receipt</span><span class="v" id="s2-v2">IOE0912345682</span></div>
   <div class="row"><span class="k">Employer</span><span class="v" id="s2-v3">Terraform Grid Systems, Inc.</span></div>
   <div class="row"><span class="k">Salary</span><span class="v" id="s2-v4">$260,000</span></div>
   <div class="row"><span class="k">Classification</span><span class="v keep">O-1A, extraordinary ability in business</span></div>
  </div></div><div class="base"></div></div>
<div id="s2-factors" class="factors">
  <div class="fcard" id="s2-f1"><h3>Some are easy to spot</h3>
    <div class="chip"><span>A134-902-661</span><i>easy</i></div>
    <div class="chip"><span>$260,000</span><i>easy</i></div>
    <div class="chip"><span>“named to a founders list two years running”</span><i>hard</i></div></div>
  <div class="fcard" id="s2-f2"><h3>The rule</h3>
    <div class="pp ok" id="s2-p1"><b>Keep</b>how the case was won: the criteria, the structure, the reasoning</div>
    <div class="pp wall" id="s2-p2"><b>Remove</b>who it was about: name, employer, salary, ID numbers</div></div>
</div>`;

const letter = (p) => `<div class="sheet" id="${p}-sheet"><div class="sheet-in serif">
<p>I have worked alongside ${sw(p + "-n", "Adaeze Umeh", "NAME")}, the company's founder and CEO, since our first investment.</p>
<p>${sw(p + "-o", "Terraform Grid Systems, Inc.", "ORG")} closed an ${sw(p + "-m", "$18,500,000", "AMOUNT")} round she led personally through six months of due diligence.</p>
<p>The board compensates her at ${sw(p + "-s", "$260,000", "AMOUNT")} annually.</p>
</div><div class="tear"></div></div>`;
sc.s3 = `<div class="label" id="s3-l1">Blacking out</div><div class="label" id="s3-l2">Swapping in labels</div>
<div class="stage">${letter("s3")}</div>`;

sc.s4 = `<div class="label" id="s4-l1">The sneaky ones</div>
<div class="stage" id="s4-a"><div class="sheet wide" id="s4-sheet"><div class="sheet-in serif big">
<p>The beneficiary is <span id="s4-q" class="q">the founder of the delivery startup that raised its Series A last year</span>.</p>
<p class="dim">No name. No number. Still one person.</p></div><div class="tear"></div></div></div>
<div id="s4-stat" class="stat"><div class="sn">0<span>/102</span></div><div class="sl">sneaky leaks caught by simple search rules</div>
<div class="note">Hard held-out set: synthetic legal drafts, not O-1 petitions. n = 102 leaks.</div></div>
<div id="s4-judge" class="judge"><div class="jh">AI reviewer</div><div class="jv">Flagged</div>
<div class="jq">“…the delivery startup that raised its Series A last year” points to one person.</div></div>`;

sc.s5 = `<div class="label">A wall around each client</div>
<div class="wallstage">
  <div class="src" id="s5-a"><div class="sh">Client files</div><div class="sid">Umeh</div><div class="cred">only Umeh’s assistant can read these</div></div>
  <div class="wbar" id="s5-w"></div>
  <div class="src" id="s5-b"><div class="sh">Client files</div><div class="sid">Achterberg</div><div class="cred">only Achterberg’s assistant can read these</div></div>
</div>
<table class="tbl req" id="s5-t"><tr><th>Umeh’s assistant asks to…</th><th>Answer</th></tr>
<tr id="s5-r0"><td>search Umeh’s own files</td><td class="okc">Here you go</td></tr>
<tr id="s5-r1"><td>open Achterberg’s file</td><td><span id="s5-deny" class="deny">Access denied</span></td></tr></table>`;

// trade-off chart: x = over-redaction % (0..40), y = identifiers removed of 123
const pts = [
  ["facts (other matters' sheets)", 0.0, 4, "r"],
  ["rules", 5.2, 88, "l"],
  ["rules+facts", 5.2, 92, ""],
  ["river_base", 9.0, 118, "l2"],
  ["rules+facts+river_base", 12.2, 118, ""],
  ["claude", 28.6, 119, "l"],
  ["river_tuned", 29.1, 120, ""],
  ["rules+facts+river (tuned)", 31.3, 123, ""],
  ["rules+facts+claude", 32.3, 123, ""],
  ["rules+facts+river+claude", 38.4, 123, "t"],
];
const X0 = 140, X1 = 1180, Y0 = 600, Y1 = 40;
const px = (v) => X0 + (v / 40) * (X1 - X0), py = (v) => Y0 - (v / 123) * (Y0 - Y1);
const labels = {
  "facts (other matters' sheets)": ["Facts, blind: 4", 18, -14],
  rules: ["Rules: 88", 18, 6],
  river_base: ["River base: 118 at 9.0%", 16, 36],
  claude: ["Claude: 119", -150, 34],
  "rules+facts+river+claude": ["All four: 123 at 38.4%", -190, -22],
};
let dots = "";
pts.forEach(([n, x, y], i) => {
  const lab = labels[n];
  dots += `<g class="dot" id="s6-d${i}"><circle cx="${px(x)}" cy="${py(y)}" r="11" fill="${n === "river_base" ? "#1E7B4F" : "#1F4E9E"}" stroke="#FBFBF9" stroke-width="3"/>${lab ? `<text x="${px(x) + lab[1]}" y="${py(y) + lab[2]}" class="dl">${lab[0]}</text>` : ""}</g>`;
});
let ticks = "";
for (const v of [0, 10, 20, 30, 40]) ticks += `<text x="${px(v)}" y="${Y0 + 40}" class="tk" text-anchor="middle">${v}%</text>`;
for (const v of [0, 40, 80, 123]) ticks += `<text x="${X0 - 18}" y="${py(v) + 8}" class="tk" text-anchor="end">${v}</text>`;
const APP = [["welcome", 0], ["onb1", 2.4], ["onb2", 4.0], ["onb3", 5.4], ["onb4", 6.8], ["review", 8.3], ["review-after", 10.2]];
sc.s6 = `<div class="label">The app</div>
<div class="app-frame"><div class="app-bar"><i></i><i></i><i></i><span>the-wall · Okafor &amp; Lind Immigration</span></div>
<div class="app-view">${APP.map(([n]) => `<img class="app-shot" id="s6-${n}" src="assets/app/${n}.png"/>`).join("")}</div></div>`;

sc.s7 = `<div class="label">The honest scoreboard</div>
<table class="tbl score" id="s7-t"><tr><th>Detector</th><th>Our hardest test<small>102 leaks, 98 clean letters</small></th><th>New tests by others<small>100 leaks, 100 clean letters</small></th></tr>
<tr id="s7-r0"><td>Simple search rules</td><td>0/102 caught, 0/98 false alarms</td><td>38/100 caught, 1/100 false alarms</td></tr>
<tr id="s7-r1"><td>General AI (Claude Sonnet 5)</td><td>59/102 caught, 7/98 false alarms</td><td>99/100 caught, 3/100 false alarms</td></tr>
<tr id="s7-r2"><td>Our trained AI reviewer (River)</td><td><span class="bx" id="s7-h">102/102 caught, 0/98 false alarms</span></td><td><span class="bx" id="s7-i">100/100 caught, <em id="s7-fa">12/100 false alarms</em></span></td></tr></table>
<div class="src-note" id="s7-n">The hardest test was built the same way as our reviewer’s training data. The new tests came from 5 writers who never saw it. Source: evals/independent/README.md.</div>`;

sc.s8 = `<div class="center col">${mark(170)}<div class="close" id="s8-c1">Learn from every case.</div><div class="close" id="s8-c2">Keep every client private.</div></div>`;

sc.end = `<div class="center col"><div class="et">The Wall</div><div class="eu">github.com/d-q222/the-wall</div>
<div class="ef">Removes identifiers, with residual leakage measured. Synthetic data; every person and firm shown is fictional.</div></div>`;

let body = "";
for (const id of [...scenes.map((s) => s.id), "end"]) {
  body += clip(`${id}`, S[id].start, S[id].dur, 1, sc[id], "scene") + "\n";
}
// narrator cards: full-frame spoken key phrases, keeping a cut every 5-8 s
body += card("nc1", "s1", 7.0, 12.6, "A great example. And one person’s private file.") + "\n";
body += card("nc3", "s3", 11.0, 13.7, "The letter still reads clearly.") + "\n";
body += card("nc5", "s5", 10.6, 13.3, "A real lock, not a polite request.") + "\n";
body += card("nc7", "s7", 14.4, 17.2, "Catches every leak. Fewer false alarms is next.") + "\n";
let audio = "";
for (const s of scenes) audio += `<audio id="vo-${s.id}" src="audio/${s.id}.wav" data-start="${(S[s.id].start + LEAD).toFixed(2)}" data-duration="${dur[s.id]}" data-track-index="10"></audio>\n`;

// ---------- motion (local scene time -> absolute) ----------
const m = [];
const at = (sid, x) => (S[sid].start + x).toFixed(2);
const pop = (sel, sid, x, extra = "") => m.push(`tl.fromTo("${sel}",{opacity:0,y:24},{opacity:1,y:0,duration:0.5,ease:"power2.out"${extra}},${at(sid, x)});`);
const fade = (sel, sid, x, d = 0.4) => m.push(`tl.fromTo("${sel}",{opacity:0},{opacity:1,duration:${d}},${at(sid, x)});`);
const out = (sel, sid, x, d = 0.3) => m.push(`tl.to("${sel}",{opacity:0,duration:${d}},${at(sid, x)});`);
const swap = (id, sid, x) => { m.push(`tl.to("#${id} .a",{opacity:0,duration:0.35},${at(sid, x)});`); m.push(`tl.fromTo("#${id} .b",{opacity:0},{opacity:1,duration:0.35},${at(sid, x + 0.15)});`); };
const hl = (sel, sid, x) => m.push(`tl.fromTo("${sel}",{"--hl":0},{"--hl":1,duration:0.35},${at(sid, x)});`);

// s1
m.push(`tl.fromTo("#s1-mark",{scale:0.6,opacity:0},{scale:1,opacity:1,duration:0.6,ease:"back.out(1.6)"},${at("s1", 0.1)});`);
pop("#s1-name", "s1", 0.6);
for (let i = 0; i < 7; i++) pop(`#s1-b${i}`, "s1", 2.6 + i * 0.07);
out("#s1-mark,#s1-name,#s1-shelf", "s1", 7.0, 0.01);
fade("#s1-agenda .ag-head", "s1", 12.8);
pop("#s1-a0", "s1", 13.6); pop("#s1-a1", "s1", 15.2); pop("#s1-a2", "s1", 16.5);
// s2
fade("#s2-l1", "s2", 0.1); pop("#s2-laptop", "s2", 0.1);
[3.4, 4.1, 4.8, 5.6, 6.3].forEach((x, i) => hl(`#s2-v${i}`, "s2", x));
out("#s2-l1,#s2-laptop", "s2", 7.4, 0.01);
fade("#s2-l2", "s2", 7.4); pop("#s2-f1", "s2", 7.5); m.push(`tl.fromTo("#s2-f1 .chip",{opacity:0,x:-20},{opacity:1,x:0,duration:0.4,stagger:0.5},${at("s2", 8.1)});`);
pop("#s2-f2", "s2", 10.0); pop("#s2-p1", "s2", 11.0); pop("#s2-p2", "s2", 12.5);
// s3: masking, then the SAME sheet gets replacement
fade("#s3-l1", "s3", 0.1); pop("#s3-sheet", "s3", 0.1);
for (const k of ["n", "o", "m", "s"]) swap(`s3-${k}`, "s3", 3.0);
m.push(`tl.set("#s3-l1",{opacity:0},${at("s3", 6.6)});`); fade("#s3-l2", "s3", 6.6, 0.2);
m.push(`tl.set("#s3 .sw .b",{opacity:0},${at("s3", 6.6)});`);
m.push(`tl.set("#s3 .sw .a",{opacity:1},${at("s3", 6.6)});`);
for (const k of ["n", "o", "m", "s"]) { m.push(`tl.to("#s3-${k} .a",{opacity:0,duration:0.3},${at("s3", 7.6)});`); m.push(`tl.fromTo("#s3-${k} .c",{opacity:0},{opacity:1,duration:0.3},${at("s3", 7.75)});`); }
m.push(`tl.fromTo("#s3 .c",{outlineColor:"rgba(194,65,12,0)"},{outlineColor:"rgba(194,65,12,1)",duration:0.3},${at("s3", 9.4)});`);
// s4
fade("#s4-l1", "s4", 0.1); pop("#s4-sheet", "s4", 0.1);
m.push(`tl.fromTo("#s4-q",{outlineColor:"rgba(194,65,12,0)"},{outlineColor:"rgba(194,65,12,1)",duration:0.3},${at("s4", 1.4)});`);
fade("#s4-sheet .dim", "s4", 4.2);
out("#s4-a", "s4", 6.8, 0.01); pop("#s4-stat", "s4", 6.8);
out("#s4-stat", "s4", 11.0, 0.01); pop("#s4-judge", "s4", 11.0);
// s5
pop("#s5-a", "s5", 0.2); pop("#s5-b", "s5", 0.5); m.push(`tl.fromTo("#s5-w",{scaleY:0},{scaleY:1,duration:0.6,ease:"power2.out"},${at("s5", 1.0)});`);
pop("#s5-t", "s5", 3.0); pop("#s5-r0", "s5", 3.3); pop("#s5-r1", "s5", 5.2);
m.push(`tl.fromTo("#s5-deny",{outlineColor:"rgba(194,65,12,0)"},{outlineColor:"rgba(194,65,12,1)",duration:0.3},${at("s5", 9.2)});`);
// s6: real app screens, one after another
pop(".app-frame", "s6", 0.05);
APP.forEach(([n, x]) => fade(`#s6-${n}`, "s6", x, 0.35));
// s7
pop("#s7-t", "s7", 0.2); pop("#s7-r0", "s7", 0.6); pop("#s7-r1", "s7", 1.0); pop("#s7-r2", "s7", 1.4);
m.push(`tl.fromTo("#s7-h",{outlineColor:"rgba(194,65,12,0)"},{outlineColor:"rgba(194,65,12,1)",duration:0.3},${at("s7", 5.4)});`);
m.push(`tl.fromTo("#s7-i",{outlineColor:"rgba(194,65,12,0)"},{outlineColor:"rgba(194,65,12,1)",duration:0.3},${at("s7", 9.4)});`);
m.push(`tl.fromTo("#s7-fa",{color:"#14213D"},{color:"#C2410C",duration:0.3},${at("s7", 12.2)});`);
fade("#s7-n", "s7", 2.0);
// s8 + end
m.push(`tl.fromTo("#s8 .mark",{scale:0.7,opacity:0},{scale:1,opacity:1,duration:0.5,ease:"back.out(1.6)"},${at("s8", 0.1)});`);
pop("#s8-c1", "s8", 0.3); pop("#s8-c2", "s8", 1.7);
pop("#end .et", "end", 0.1); pop("#end .eu", "end", 0.5); fade("#end .ef", "end", 0.9);
m.push(`tl.to("#end .center",{opacity:0,duration:0.5},${(TOTAL - 0.6).toFixed(2)});`);
// narrator cards
out("#s3 .stage,#s3-l2", "s3", 11.0, 0.01); out("#s7-t,#s7-n", "s7", 14.4, 0.01); out("#s5 .wallstage,#s5-t", "s5", 10.6, 0.01);
for (const id of ["nc1", "nc3", "nc5", "nc7"]) m.push(`tl.fromTo("#${id} p",{opacity:0,y:18},{opacity:1,y:0,duration:0.45,ease:"power2.out"},document.getElementById("${id}").dataset.start*1+0.05);`);

const ff = (fam, file, w, style = "normal") => `@font-face{font-family:"${fam}";src:url("assets/fonts/${file}") format("woff2");font-weight:${w};font-style:${style};}`;
const html = `<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920, height=1080"/>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
${ff("Public Sans", "public-sans-400.woff2", 400)}${ff("Public Sans", "public-sans-500.woff2", 500)}${ff("Public Sans", "public-sans-600.woff2", 600)}${ff("Public Sans", "public-sans-700.woff2", 700)}
${ff("Source Serif 4", "source-serif-4-400.woff2", 400)}${ff("Source Serif 4", "source-serif-4-600.woff2", 600)}${ff("Source Serif 4", "source-serif-4-400-italic.woff2", 400, "italic")}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;background:#FFFFFF}
#root{width:100%;height:100%;position:relative;font-family:"Public Sans",sans-serif;color:#14213D;font-variant-numeric:tabular-nums;
 background-color:#FFFFFF;background-image:linear-gradient(#EEF1F5 1px,transparent 1px),linear-gradient(90deg,#EEF1F5 1px,transparent 1px);background-size:48px 48px}
.scene{position:absolute;inset:0}
.center{position:absolute;left:0;right:0;top:0;height:900px;display:flex;align-items:center;justify-content:center}
.col{flex-direction:column;gap:28px}
.label{position:absolute;left:96px;top:72px;font-size:40px;font-weight:500;letter-spacing:-0.01em}
.firm{font-size:48px;font-weight:600}
.mark{display:block}
.shelf{display:flex;gap:14px;margin-top:20px;align-items:flex-end}
.binder{width:62px;height:190px;background:#1F4E9E;border-radius:2px;display:flex;align-items:flex-end;justify-content:center;padding-bottom:16px;color:#FBFBF9;font-weight:600;font-size:18px}
.binder:nth-child(2n){background:#14213D;height:170px}.binder:nth-child(3n){height:205px}
.agenda{position:absolute;left:0;right:0;top:170px;display:flex;flex-direction:column;align-items:center;gap:34px}
.ag-head{display:flex;align-items:center;gap:22px;font-size:44px;font-weight:600;margin-bottom:12px;opacity:0}
.ag{width:900px;font-size:46px;display:flex;align-items:center;gap:30px;opacity:0}
.ag b{width:64px;height:64px;border-radius:50%;background:#1F4E9E;color:#fff;display:flex;align-items:center;justify-content:center;font-size:32px}
.laptop{position:absolute;left:460px;top:190px;width:1000px}
.screen{height:560px;border:18px solid #14213D;border-radius:14px 14px 0 0;background:#FBFBF9;overflow:hidden}
.screen .bar{height:26px;background:#1F4E9E}
.base{height:26px;background:#2B3A55;margin:0 -60px;border-radius:0 0 18px 18px}
.rec{padding:30px 44px;display:flex;flex-direction:column;gap:14px}
.row{display:flex;font-size:30px;gap:24px;align-items:center}
.row .k{width:250px;color:#4A5876}
.row .v{--hl:0;padding:4px 10px;border-radius:4px;background:rgba(255,229,138,var(--hl));outline:3px solid rgba(194,65,12,var(--hl));font-weight:600}
.row .v.keep{font-weight:400}
.factors{position:absolute;left:0;right:0;top:190px;display:flex;justify-content:center;gap:60px}
.fcard{width:760px;background:#FBFBF9;border:2px solid #D5DBE4;border-radius:8px;padding:36px 40px;display:flex;flex-direction:column;gap:22px;opacity:0}
.fcard h3{font-size:38px;font-weight:600}
.chip{display:flex;justify-content:space-between;align-items:center;gap:20px;font-size:28px;padding:14px 18px;border-radius:4px;background:#F1F3F7;opacity:0}
.chip span{font-weight:600}.chip i{font-style:normal;color:#4A5876;white-space:nowrap}
.pp{font-size:30px;padding:20px 22px;border-radius:4px;display:flex;flex-direction:column;gap:6px;opacity:0}
.pp b{font-size:36px}.pp.ok{background:#E3F1EA;color:#14532D}.pp.ok b{color:#1E7B4F}.pp.wall{background:#FBE9E0;color:#7C2D12}.pp.wall b{color:#C2410C}
.stage{position:absolute;left:0;right:0;top:170px;display:flex;justify-content:center}
.sheet{width:1080px;filter:drop-shadow(0 6px 14px rgba(20,33,61,.14))}
.sheet.wide{width:1240px}
.sheet-in{background:#FBFBF9;padding:56px 64px 40px;display:flex;flex-direction:column;gap:26px}
.serif{font-family:"Source Serif 4",serif;font-size:36px;line-height:1.5}
.big{font-size:44px}
.tear{height:22px;background:#FBFBF9;clip-path:polygon(${Array.from({ length: 41 }, (_, i) => `${i * 2.5}% ${i % 2 ? 100 : 0}%`).join(",")})}
.sw{display:inline-grid;--mode:0}.sw>span{grid-area:1/1;white-space:nowrap}
.sw .b,.sw .c{opacity:0}
.sw .b{font-family:"Public Sans",sans-serif;font-weight:600;letter-spacing:.06em;color:#14213D}
.sw .c{font-family:"Public Sans",sans-serif;font-size:28px;font-weight:600;color:#1F4E9E;background:#E4ECF8;border-radius:4px;padding:0 10px;align-self:center;justify-self:start;outline:3px solid rgba(194,65,12,0);outline-offset:3px}
.q{outline:4px solid rgba(194,65,12,0);outline-offset:6px;border-radius:2px}
.dim{color:#4A5876;font-style:italic;opacity:0}
.stat{position:absolute;left:0;right:0;top:220px;display:flex;flex-direction:column;align-items:center;gap:20px;opacity:0}
.sn{font-size:220px;font-weight:700;line-height:1;color:#C2410C}.sn span{color:#14213D;font-size:120px}
.sl{font-size:44px;font-weight:500}.note{font-size:28px;color:#4A5876}
.judge{position:absolute;left:560px;top:250px;width:800px;background:#FBFBF9;border:2px solid #D5DBE4;border-radius:8px;padding:40px 48px;display:flex;flex-direction:column;gap:18px;opacity:0}
.jh{font-size:30px;color:#4A5876;font-weight:600}.jv{font-size:72px;font-weight:700;color:#C2410C}.jq{font-family:"Source Serif 4",serif;font-size:34px;line-height:1.4}
.wallstage{position:absolute;left:0;right:0;top:170px;display:flex;justify-content:center;align-items:stretch;gap:70px}
.src{width:520px;background:#FBFBF9;border:2px solid #D5DBE4;border-radius:8px;padding:30px 36px;display:flex;flex-direction:column;gap:10px;opacity:0}
.sh{font-size:24px;color:#4A5876}.sid{font-size:42px;font-weight:700}.cred{font-size:24px;color:#1F4E9E}
.wbar{width:26px;background:#C2410C;border-radius:3px;transform-origin:50% 100%}
.tbl{position:absolute;left:0;right:0;margin:0 auto;border-collapse:collapse;background:#FFFFFF;opacity:0}
.tbl th{background:#E9EDF3;text-align:left;font-weight:600;padding:18px 26px;font-size:28px}
.tbl th small{display:block;font-size:22px;font-weight:400;color:#4A5876}
.tbl td{padding:18px 26px;border-bottom:1px solid #D5DBE4;font-size:28px}
.tbl tr{opacity:1}
.req{top:520px;width:1170px}
.okc{color:#1E7B4F;font-weight:600}
.deny{font-weight:700;color:#C2410C;outline:4px solid rgba(194,65,12,0);outline-offset:6px;padding:0 4px}
.score{top:220px;width:1640px}.score td:first-child{font-weight:600}
.bx{outline:4px solid rgba(194,65,12,0);outline-offset:8px;border-radius:2px}
.bx em{font-style:normal;font-weight:700}
.app-frame{position:absolute;left:280px;top:140px;width:1360px;border-radius:10px;overflow:hidden;background:#FFFFFF;box-shadow:0 10px 30px rgba(20,33,61,.18);border:1px solid #D5DBE4;opacity:0}
.app-bar{height:40px;background:#E9EDF3;display:flex;align-items:center;gap:8px;padding:0 16px}
.app-bar i{width:12px;height:12px;border-radius:50%;background:#C5CCD8}.app-bar span{margin-left:14px;font-size:18px;color:#4A5876}
.app-view{position:relative;width:1360px;height:750px;overflow:hidden;background:#E6E9ED}
.app-shot{position:absolute;left:0;top:0;width:1360px;height:850px;opacity:0}
#s6-review-after{width:2040px;height:1275px;left:-200px;top:-400px}
.tk{font-size:24px;fill:#4A5876}.ax{font-size:28px;fill:#14213D;font-weight:500}
.dl{font-size:24px;fill:#14213D;font-weight:600}
.capline{stroke:#C2410C;stroke-width:3;stroke-dasharray:10 8;opacity:0}.capl{fill:#C2410C;font-size:24px;font-weight:600;opacity:0}
.src-note{position:absolute;left:96px;right:96px;top:860px;font-size:22px;color:#4A5876;text-align:center;opacity:0}
#s7-n{top:640px}
.close{font-family:"Source Serif 4",serif;font-size:84px;font-weight:600}
.et{font-size:120px;font-weight:700;letter-spacing:-0.02em}.eu{font-size:44px;color:#1F4E9E;font-weight:600}.ef{font-size:26px;color:#4A5876;margin-top:24px}
.ncard{position:absolute;inset:0;background:#F4EEE2}
.nc-in{position:absolute;left:160px;right:160px;top:0;height:900px;display:flex;align-items:center;justify-content:center}
.nc-in p{font-family:"Source Serif 4",serif;font-size:96px;font-weight:600;line-height:1.15;text-align:center;color:#14213D}
.cc.clip{position:absolute;left:0;right:0;top:940px;display:flex;justify-content:center}
.cc.clip span{background:rgba(20,33,61,.9);color:#FFFFFF;font-size:38px;font-weight:500;padding:10px 26px;border-radius:6px;max-width:1600px;text-align:center}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="${TOTAL}" data-width="1920" data-height="1080">
${body}
${caps}
${audio}
</div>
<script>
const tl = gsap.timeline({ paused: true });
${m.join("\n")}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body></html>
`;
writeFileSync(root + "index.html", html);
console.log("total", TOTAL, JSON.stringify(Object.fromEntries(Object.entries(S).map(([k, v]) => [k, [v.start, v.dur]]))));
