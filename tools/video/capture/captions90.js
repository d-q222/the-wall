// Renders transparent 1920x1080 caption PNGs (and the scene-2 title card) for the 90 s video.
const { chromium } = require('playwright'); const fs = require('fs');
const dir = process.argv[2]; const lines = fs.readFileSync(dir + '/lines.txt', 'utf8').trim().split('\n');
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const cap = (t) => `<div style="position:absolute;left:50%;bottom:60px;transform:translateX(-50%);max-width:1500px;background:rgba(0,0,0,.72);color:#fff;font:600 42px/1.3 Helvetica,Arial,sans-serif;padding:18px 32px;border-radius:14px;text-align:center">${esc(t)}</div>`;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  for (let i = 0; i < lines.length; i++) {
    await p.setContent(`<body style="margin:0;background:transparent">${cap(lines[i])}</body>`);
    await p.screenshot({ path: `${dir}/cap${i + 1}.png`, omitBackground: true });
  }
  await p.setContent(`<body style="margin:0;background:#fff;height:1080px;display:flex;align-items:center;justify-content:center"><div style="font:700 88px Helvetica,Arial,sans-serif;color:#111;margin-bottom:200px">So their AI has to forget everything.</div></body>`);
  await p.screenshot({ path: `${dir}/title.png` });
  await b.close();
})();
