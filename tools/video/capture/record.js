// Records one real-screen clip per demo beat from the live preview.
// Usage: node record.js [beat numbers...]   (default: all)
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const BASE = process.env.WALL_API_URL || 'http://localhost:8788';
const OUT = '/Users/dqi26/the-wall/.runtime/video/clips';
const RAW = path.join(OUT, 'raw');
// Browser storage carried across runs, so pages can replay their cached last live result (demo-safe rule).
const STATE = path.join(RAW, 'storage.json');
const W = 1920, H = 1080;

// Headless video has no pointer, so draw one that follows real mouse events.
const CURSOR = `
addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.id = '__cursor';
  c.style.cssText = 'position:fixed;left:0;top:0;width:22px;height:22px;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px);transition:scale .12s';
  c.innerHTML = '<svg width="22" height="22" viewBox="0 0 22 22"><path d="M3 2l14 8-6 1.5L8 18z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  addEventListener('mousemove', e => { c.style.transform = 'translate(' + (e.clientX - 3) + 'px,' + (e.clientY - 2) + 'px)'; }, true);
  addEventListener('mousedown', () => { c.style.scale = '0.8'; }, true);
  addEventListener('mouseup', () => { c.style.scale = '1'; }, true);
});
try { localStorage.setItem('theme', 'light'); localStorage.setItem('wall-theme', 'light'); localStorage.setItem('wall-demo-theme', 'light'); } catch (e) {}
document.documentElement.setAttribute('data-theme', 'light');
`;

const sleep = ms => new Promise(r => setTimeout(r, ms));
let mouse = { x: W / 2, y: H / 2 };
let marks = [], markT0 = 0;
const mark = label => marks.push({ t: Math.round((Date.now() - markT0) / 100) / 10, label });

async function moveTo(page, locator) {
  await locator.scrollIntoViewIfNeeded();
  const b = await locator.boundingBox();
  const x = b.x + b.width / 2, y = b.y + b.height / 2;
  const d = Math.hypot(x - mouse.x, y - mouse.y);
  await page.mouse.move(x, y, { steps: Math.max(15, Math.round(d / 18)) });
  mouse = { x, y };
  await sleep(350);
}
async function click(page, locator) {
  await moveTo(page, locator);
  await page.mouse.down(); await sleep(90); await page.mouse.up();
  await sleep(400);
}
async function select(page, locator, value) {
  await moveTo(page, locator);
  await locator.selectOption(value);
  await sleep(700);
}
async function glideRight(page, locator) {
  // Glide along the row so the eye follows the numbers.
  const b = await locator.boundingBox();
  await page.mouse.move(b.x + 260, b.y + b.height / 2, { steps: 40 });
  mouse = { x: b.x + 260, y: b.y + b.height / 2 };
}
async function scrollBy(page, dy, steps = 20) {
  for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await sleep(35); }
  await sleep(500);
}

const BEATS = {
  1: ['wall', 'Access wall: attacker agent vs target matter, wall holds', async p => {
    await p.goto(BASE + '/demo/wall.html', { waitUntil: 'networkidle' });
    await sleep(1500);
    await select(p, p.locator('#attackerSelect'), 'reyes');
    await select(p, p.locator('#targetSelect'), 'delmarva');
    await click(p, p.locator('#runBtn'));
    mark('attack started');
    await p.getByText(/held/i).first().waitFor({ timeout: 90000 });
    mark('wall held result');
    await sleep(1500);
    await moveTo(p, p.getByText(/held/i).first());
    await sleep(5000);
  }],
  2: ['review', 'Review: de-identify O-1 recommendation letter (o1-umeh), chips + inspector + judge', async p => {
    await p.goto(BASE + '/demo/', { waitUntil: 'networkidle' });
    await sleep(1200);
    await select(p, p.locator('#matter-switcher'), 'o1-umeh');
    await sleep(800);
    await click(p, p.locator('.binder-tab', { hasText: 'Recommendation' }));
    await sleep(1500);
    let res;
    for (let attempt = 0; attempt < 2; attempt++) {
      const done = p.waitForResponse(r => r.url().includes('/deidentify'), { timeout: 120000 });
      await click(p, p.locator('#run'));
      mark('de-identify clicked');
      res = await done;
      if (res.ok()) break;
      await sleep(1500);
    }
    if (!res.ok()) throw new Error('/deidentify returned HTTP ' + res.status());
    mark('de-identify result');
    await sleep(4000);
    const chip = p.locator('.chip, .placeholder-chip, [data-span], mark').first();
    if (await chip.count()) { await moveTo(p, chip); await click(p, chip); }
    await sleep(3000);
    const verdict = p.getByText(/verdict|judge/i).first();
    if (await verdict.count()) await moveTo(p, verdict);
    await sleep(4000);
  }],
  3: ['datasets', 'Datasets: de-identify all exhibits, rows complete, export training JSONL', async p => {
    await p.goto(BASE + '/demo/datasets.html', { waitUntil: 'networkidle' });
    await sleep(1500);
    await click(p, p.locator('#run'));
    mark('rows processing (speed-ramp candidate)');
    await p.waitForFunction(() => !document.querySelector('#run').disabled, null, { timeout: 180000, polling: 500 }).catch(() => {});
    mark('all rows complete');
    await sleep(2500);
    await moveTo(p, p.locator('#export'));
    mark('hover export');
    await sleep(3500);
  }],
  4: ['model', 'Model: held-out score, attorney correction typed (not submitted), retrain (never confirmed)', async p => {
    await p.goto(BASE + '/demo/training.html', { waitUntil: 'networkidle' });
    await sleep(2000);
    await scrollBy(p, 250);
    mark('held-out score');
    await sleep(2500);
    // Synthetic correction typed to show the flow; not submitted, so shared state is untouched.
    const form = p.locator('textarea[name=passage]');
    await click(p, form);
    await form.pressSequentially('Recognized by the [ORG_1] Fellows Program in 2024 for grid research.', { delay: 28 });
    const kind = p.locator('select[name=span_kind]');
    if (await kind.locator('option', { hasText: 'Award' }).count()) await select(p, kind, { label: 'Award' });
    const exact = p.locator('input[name=span_text]');
    await click(p, exact);
    await exact.pressSequentially('Fellows Program', { delay: 45 });
    mark('correction typed');
    await moveTo(p, p.getByRole('button', { name: 'Add correction' }));
    await sleep(1500);
    const retrain = p.locator('#retrain');
    await moveTo(p, retrain);
    if (await retrain.isEnabled()) {
      await click(p, retrain);
      await sleep(2500);
      const cancel = p.locator('#confirm-cancel');
      if (await cancel.isVisible()) await click(p, cancel);  // never start a real retrain
    }
    await sleep(3000);
  }],
  5: ['compound', 'Compounding: know-how carries over, 0 Delmarva facts', async p => {
    await p.goto(BASE + '/demo/compound.html', { waitUntil: 'networkidle' });
    await sleep(1500);
    await click(p, p.locator('#run-btn'));
    const zero = p.getByText(/0 Delmarva facts/i).first();
    await zero.waitFor({ timeout: 120000 });
    mark('0 Delmarva facts');
    await sleep(1000);
    await moveTo(p, zero);
    await sleep(5000);
  }],
  6: ['policy', 'Policy: immigration lists of what may carry over vs never leaves', async p => {
    await p.goto(BASE + '/demo/policy.html', { waitUntil: 'networkidle' });
    await sleep(2000);
    const imm = p.getByText('Immigration', { exact: true }).first();
    const b = await imm.boundingBox();
    if (b) await scrollBy(p, b.y - 140, 40);
    await sleep(1000);
    await moveTo(p, imm);
    await sleep(5000);
  }],
  7: ['evaluation', 'Evaluation: scoreboard comparison table', async p => {
    await p.goto(BASE + '/scoreboard/', { waitUntil: 'networkidle' });
    await sleep(2500);
    const row = p.getByText(/river_judge/i).first();
    if (await row.count()) { await moveTo(p, row); await sleep(1500); await glideRight(p, row); }
    await sleep(7000);
  }],
  8: ['present', 'Presenter: cover slide', async p => {
    await p.goto(BASE + '/demo/present.html', { waitUntil: 'networkidle' });
    await sleep(8000);
  }],
};

async function record(browser, n) {
  const [name, notes, run] = BEATS[n];
  const dir = path.join(RAW, String(n));
  fs.rmSync(dir, { recursive: true, force: true });
  const ctx = await browser.newContext({
    viewport: { width: W, height: H }, colorScheme: 'light',
    storageState: fs.existsSync(STATE) ? STATE : undefined,
    recordVideo: { dir, size: { width: W, height: H } },
  });
  await ctx.addInitScript(CURSOR);
  const page = await ctx.newPage();
  const t0 = Date.now();
  mouse = { x: W / 2, y: H / 2 };
  marks = []; markT0 = t0;
  // Trim the blank pre-load frames: the clip starts once the first page has painted.
  let start = 0;
  page.once('load', () => { start = (Date.now() - t0) / 1000 + 0.6; });
  let ok = true;
  try { await run(page); } catch (e) { ok = false; console.error(`beat ${n} error:`, e.message.split('\n')[0]); }
  await page.screenshot({ path: path.join(OUT, `${n}-${name}.png`) });
  const total = (Date.now() - t0) / 1000;
  const video = page.video();
  await ctx.storageState({ path: STATE });
  await ctx.close();
  const src = await video.path();
  const base = path.join(OUT, `${n}-${name}`);
  const ss = String(start.toFixed(2));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', ss, '-i', src, '-c:v', 'libvpx-vp9', '-b:v', '4M', '-deadline', 'realtime', '-cpu-used', '8', '-row-mt', '1', '-an', base + '.tmp.webm']);
  fs.renameSync(base + '.tmp.webm', base + '.webm');
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-ss', ss, '-i', src, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'fast', '-an', base + '.tmp.mp4']);
  fs.renameSync(base + '.tmp.mp4', base + '.mp4');
  const dur = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', base + '.mp4']).toString().trim());
  console.log(`beat ${n} ${name}: ${dur.toFixed(1)}s ${ok ? 'ok' : 'INCOMPLETE'}`);
  return { file: `${n}-${name}.webm`, mp4: `${n}-${name}.mp4`, beat: n, name, duration_s: Math.round(dur * 10) / 10,
           notes: ok ? notes : notes + ' (INCOMPLETE: interaction failed, check clip)', recorded_at: new Date().toISOString(), ok,
           marks: marks.map(m => ({ t: Math.max(0, Math.round((m.t - start) * 10) / 10), label: m.label })) };
}

(async () => {
  fs.mkdirSync(RAW, { recursive: true });
  const want = process.argv.slice(2).map(Number);
  const beats = want.length ? want : Object.keys(BEATS).map(Number);
  const manifestPath = path.join(OUT, 'clips.json');
  const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath)) : [];
  const browser = await chromium.launch();
  for (const n of beats) {
    const entry = await record(browser, n);
    const i = manifest.findIndex(m => m.beat === n);
    if (i >= 0) manifest[i] = entry; else manifest.push(entry);
    manifest.sort((a, b) => a.beat - b.beat);
    fs.writeFileSync(manifestPath + '.tmp', JSON.stringify(manifest, null, 2));
    fs.renameSync(manifestPath + '.tmp', manifestPath);
  }
  await browser.close();
})();
