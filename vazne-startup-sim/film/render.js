// Usage: node render.js scenes.json out.mp4 [--stills DIR] [--fps 30] [--from S --to S] [--frac 0.6] [--jpegq 90]
const { chromium } = require('playwright');
const { spawn, execSync } = require('child_process');
const fs = require('fs'), path = require('path');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const scenesPath = args[0], outPath = args[1];
const FPS = +opt('--fps', 30), stillsDir = opt('--stills', null), frac = +opt('--frac', 0.6), JQ = +opt('--jpegq', 90);
const from = opt('--from', null), to = opt('--to', null);
const ffmpeg = execSync('python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"').toString().trim();
(async () => {
  const data = JSON.parse(fs.readFileSync(scenesPath, 'utf8'));
  { let t = 0; for (const s of data.scenes) { s.start = t; t += s.dur; } }
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-gpu', '--font-render-hinting=none', '--hide-scrollbars'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE:', m.text()); });
  await page.goto('file://' + path.resolve(__dirname, 'film.html'));
  await page.evaluate(() => document.fonts.ready);
  const total = await page.evaluate(d => window.loadScenes(d), data);
  console.log(`total duration ${total.toFixed(2)}s, ${data.scenes.length} scenes`);
  if (stillsDir) {
    fs.mkdirSync(stillsDir, { recursive: true });
    for (let i = 0; i < data.scenes.length; i++) {
      const s = data.scenes[i]; const fr = Array.isArray(frac) ? frac : [frac];
      for (const f of [frac]) { const t = s.start + Math.min(s.dur - 0.05, s.dur * f);
        await page.evaluate(t => window.seek(t), t);
        await page.screenshot({ path: path.join(stillsDir, `${String(i).padStart(2, '0')}_${s.type}_${s.id || ''}.png`) }); }
    }
    console.log('stills written to', stillsDir); await browser.close(); return;
  }
  const t0s = from != null ? +from : 0, t1s = to != null ? +to : total;
  const N = Math.round((t1s - t0s) * FPS);
  const ff = spawn(ffmpeg, ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.1', '-movflags', '+faststart', outPath]);
  ff.stderr.on('data', d => process.stderr.write(d));
  const start = Date.now();
  for (let i = 0; i < N; i++) {
    const t = t0s + i / FPS;
    await page.evaluate(t => window.seek(t), t);
    const buf = await page.screenshot({ type: 'jpeg', quality: JQ });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % (FPS * 20) === 0) { const el = (Date.now() - start) / 1000; console.log(`frame ${i}/${N} t=${t.toFixed(1)}s elapsed ${el.toFixed(0)}s eta ${((N - i) / Math.max(i, 1) * el).toFixed(0)}s`); }
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  console.log(`done: ${outPath} (${N} frames in ${((Date.now() - start) / 1000).toFixed(0)}s)`);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
