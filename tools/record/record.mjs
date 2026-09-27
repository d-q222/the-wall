// Drive the live presenter headless at 1920x1080 through every beat and record it.
// CDP screencast frames (with timestamps) -> ffmpeg concat -> H.264 mp4, plus one PNG per beat.
import { chromium } from "playwright-core";
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";

const BASE = process.env.WALL_API_URL || "http://localhost:8788";
const URL = process.env.PRESENT_URL || `${BASE}/demo/present.html`;
const OUT = process.env.BACKUP_DIR || "/Users/dqi26/the-wall/.runtime/backup";
const SCALE = Number(process.env.DWELL_SCALE || 1); // multiplies each beat's data-target seconds
const MAX_WAIT = Number(process.env.MAX_BEAT_S || 45); // cap per beat while live calls are in flight
const HIDE_CHROME = process.env.HIDE_CHROME !== "0"; // presenter clocks off by default

const d = new Date(), z = (n) => String(n).padStart(2, "0");
const stamp = `${d.getFullYear()}${z(d.getMonth() + 1)}${z(d.getDate())}-${z(d.getHours())}${z(d.getMinutes())}${z(d.getSeconds())}`; // local time
const frames = join(OUT, `.frames-${stamp}`);
mkdirSync(frames, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const log = (...a) => console.log(`[record ${((Date.now() - t0) / 1000).toFixed(1)}s]`, ...a);
const t0 = Date.now();

const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();

let inflight = 0;
const errors = [];
page.on("request", () => inflight++);
page.on("requestfinished", () => inflight--);
page.on("requestfailed", () => inflight--);
page.on("pageerror", (e) => errors.push(String(e)));
page.on("response", (r) => { if (r.status() >= 500) errors.push(`${r.status()} ${r.url()}`); });

const resp = await page.goto(URL, { waitUntil: "networkidle" });
if (!resp || !resp.ok()) throw new Error(`presenter not reachable: ${URL} -> ${resp && resp.status()}`);
await page.waitForSelector(".beat.on", { timeout: 10000 });

// Start the screencast.
const cdp = await ctx.newCDPSession(page);
const shots = [];
cdp.on("Page.screencastFrame", async ({ data, metadata, sessionId }) => {
  const f = join(frames, `f${String(shots.length).padStart(6, "0")}.jpg`);
  writeFileSync(f, Buffer.from(data, "base64"));
  shots.push({ f, t: metadata.timestamp });
  await cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
});
await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });

if (HIDE_CHROME) await page.keyboard.press("h");

const beatInfo = () =>
  page.evaluate(() => {
    const all = [...document.querySelectorAll(".beat")];
    const on = document.querySelector(".beat.on");
    return { i: all.indexOf(on), n: all.length, tab: on?.dataset.tab || "", target: Number(on?.dataset.target || 10), run: !!on?.dataset.run };
  });

// Wait at least the beat's target; if it triggers a live call, also wait for the network to settle.
async function dwell(b) {
  const start = Date.now();
  const min = b.target * SCALE * 1000;
  let quietSince = inflight === 0 ? Date.now() : 0;
  while (Date.now() - start < MAX_WAIT * 1000) {
    await sleep(250);
    if (inflight > 0) quietSince = 0;
    else if (!quietSince) quietSince = Date.now();
    const settled = quietSince && Date.now() - quietSince > 1500;
    if (Date.now() - start >= min && settled) break;
  }
}

const beats = [];
let b = await beatInfo();
while (true) {
  log(`beat ${b.i + 1}/${b.n} "${b.tab}" target ${b.target}s${b.run ? " (live)" : ""}`);
  await dwell(b);
  const png = join(OUT, `demo-${stamp}-beat${b.i + 1}-${b.tab.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.png`);
  await page.screenshot({ path: png });
  beats.push({ beat: b.i + 1, tab: b.tab, png });
  await page.keyboard.press("ArrowRight");
  let next = b;
  for (let k = 0; k < 20 && next.i === b.i; k++) { await sleep(150); next = await beatInfo(); }
  if (next.i === b.i) break; // last beat
  await sleep(600); // let the wall-sweep transition land before timing the next beat
  b = next;
}
await sleep(1500);
await cdp.send("Page.stopScreencast");
await sleep(300);
await browser.close();

// Frames arrive only on repaint; each frame lasts until the next one.
if (shots.length < 2) throw new Error(`only ${shots.length} screencast frames captured`);
const end = shots[shots.length - 1].t + 1.5;
const list = shots.map((s, i) => `file '${s.f}'\nduration ${((shots[i + 1]?.t ?? end) - s.t).toFixed(4)}`);
list.push(`file '${shots[shots.length - 1].f}'`);
writeFileSync(join(frames, "list.txt"), list.join("\n") + "\n");
const mp4 = join(OUT, `demo-${stamp}.mp4`);
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", join(frames, "list.txt"),
  "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30",
  "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", "-movflags", "+faststart", mp4]);
const dur = execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4]).toString().trim();
if (!process.env.KEEP_FRAMES) rmSync(frames, { recursive: true, force: true });

const summary = { mp4, duration_s: Number(Number(dur).toFixed(1)), frames: shots.length, beats, errors, url: URL };
writeFileSync(join(OUT, `demo-${stamp}.json`), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
