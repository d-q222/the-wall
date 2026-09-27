// Records the presenter for the 90 s video; prints slide start offsets (s) as JSON.
const { chromium } = require('playwright');
const OUT = process.argv[2];
const URL = (process.env.WALL_API_URL || 'http://localhost:8788') + '/demo/present.html';
const HOLD = [10, 0, 0, 13, 13, 10]; // extra seconds per slide (after its actions)
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: OUT, size: { width: 1920, height: 1080 } } });
  const p = await ctx.newPage();
  const t0 = Date.now(); const marks = [];
  const go = async (i) => { await p.goto('about:blank'); await p.goto(URL + '#' + i); await p.waitForTimeout(800); marks.push((Date.now() - t0) / 1000); };
  await go(0); await p.waitForTimeout(HOLD[0] * 1000);
  await go(1); await p.evaluate(() => document.getElementById('runWall').click());
  await p.waitForFunction(() => document.body.innerText.includes('The wall held'), null, { timeout: 20000 }).catch(() => {}); marks.push((Date.now() - t0) / 1000); await p.waitForTimeout(3000); marks.push((Date.now() - t0) / 1000); await p.waitForTimeout(4000);
  await go(2); await p.waitForTimeout(3000); await p.evaluate(() => [...document.querySelectorAll('button')].find(b => b.textContent.includes('Hide who it is')).click()); await p.waitForTimeout(12000);
  for (const i of [3, 4, 5]) { await go(i); await p.waitForTimeout(HOLD[i] * 1000); }
  marks.push((Date.now() - t0) / 1000);
  await ctx.close(); await b.close();
  console.log(JSON.stringify(marks));
})();
