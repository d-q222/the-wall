// Record one clip per scene of the live presenter at 1920x1080; each clip is as long as its narration.
import { chromium } from '/Users/dqi26/the-wall-wt/v1-capture/tools/video/capture/node_modules/playwright/index.mjs';
import { execSync } from 'node:child_process';
const dur = f => parseFloat(execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 ${f}`).toString()) + 3.0;
const scenes = [ // [narration, slide hash, action]
  ['n1.aiff', 0, null], ['n3.aiff', 1, 'Try to break the wall'], ['n4.aiff', 2, 'Hide who it is'],
  ['n5.aiff', 3, null], ['n6.aiff', 4, null], ['n7.aiff', 5, null]];
const browser = await chromium.launch({ channel: 'chrome' });
for (const [i, [n, slide, button]] of scenes.entries()) {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: `clip${i}`, size: { width: 1920, height: 1080 } } });
  const page = await ctx.newPage();
  await page.goto(`http://localhost:8788/demo/present.html#${slide}`);
  const total = dur(n) * 1000, t0 = Date.now();
  if (button) { await page.waitForTimeout(slide === 2 ? 3200 : 1200); await page.getByRole('button', { name: button }).click(); }
  await page.waitForTimeout(Math.max(0, total - (Date.now() - t0)) + 600);
  await ctx.close();
  console.log('scene', i, 'recorded', (Date.now() - t0) / 1000, 's');
}
await browser.close();
