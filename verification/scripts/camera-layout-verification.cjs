const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const out = path.join(root, 'output/playwright/camera-layout-20261013');
fs.mkdirSync(out, { recursive: true });

process.env.TEMP = path.join(root, '.cache/tmp');
process.env.TMP = process.env.TEMP;

const env = {
  ...process.env,
  MORPH_REVIEW: '1',
  NEXT_TELEMETRY_DISABLED: '1',
  BACKEND_URL: 'http://127.0.0.1:8007',
  MPLCONFIGDIR: path.join(root, '.cache/matplotlib'),
  PYTHONUNBUFFERED: '1',
};

const children = [];
function start(exe, args, cwd, name) {
  const log = fs.openSync(path.join(out, name + '.log'), 'w');
  const p = spawn(exe, args, { cwd, env, windowsHide: true, stdio: ['ignore', log, log] });
  children.push(p);
  p.on('error', (e) => console.error(name, e));
}

async function ready(url) {
  for (let i = 0; i < 90; i++) {
    try {
      if ((await fetch(url, { signal: AbortSignal.timeout(1500) })).ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 700));
  }
  throw Error('Not ready ' + url);
}

(async () => {
  let browser;
  const errors = [];
  const consoleErrors = [];
  const measurements = {};

  try {
    start(
      path.join(root, 'backend/.venv/Scripts/python.exe'),
      ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8007'],
      path.join(root, 'backend'),
      'backend'
    );
    start(
      process.execPath,
      [path.join(root, 'frontend/node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', '3107'],
      path.join(root, 'frontend'),
      'frontend'
    );

    await Promise.all([
      ready('http://127.0.0.1:8007/api/health'),
      ready('http://127.0.0.1:3107'),
    ]);
    console.log('SERVERS READY');

    browser = await chromium.launchPersistentContext(
      path.join(root, '.cache/camera-layout-browser'),
      {
        executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
        headless: true,
        env,
        viewport: { width: 1920, height: 1080 },
      }
    );

    const fixtures = Object.fromEntries(
      ['front', 'side'].map((key) => [
        key,
        'data:image/png;base64,' +
          fs.readFileSync(path.join(root, 'verification/scripts/qa/upper-' + key + '.png')).toString('base64'),
      ])
    );

    await browser.addInitScript(({ fixtures }) => {
      window.__cameraFixture = 'blank';
      window.__testTracks = [];
      window.__cameraRequests = [];
      Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {
        value: async () => [{ kind: 'videoinput', deviceId: 'qa', label: 'QA HD Webcam' }],
      });
      Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
        value: async (request) => {
          window.__cameraRequests.push(request);
          const images = {};
          for (const k of ['front', 'side']) {
            const img = new Image();
            img.src = fixtures[k];
            await img.decode();
            images[k] = img;
          }
          const canvas = document.createElement('canvas');
          // Standard 16:9 aspect ratio 1280x720
          canvas.width = 1280;
          canvas.height = 720;
          const ctx = canvas.getContext('2d');
          const draw = () => {
            ctx.fillStyle = '#26211A';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            if (images[window.__cameraFixture]) {
              // Draw image centered with contain
              const img = images[window.__cameraFixture];
              const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
              const x = (canvas.width - img.width * scale) / 2;
              const y = (canvas.height - img.height * scale) / 2;
              ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
            }
          };
          draw();
          const timer = setInterval(draw, 100);
          const stream = canvas.captureStream(15);
          window.__testTracks.push(...stream.getTracks());
          for (const t of stream.getTracks()) {
            const stop = t.stop.bind(t);
            t.stop = () => {
              clearInterval(timer);
              stop();
            };
          }
          return stream;
        },
      });
    }, { fixtures });

    const page = await browser.newPage();
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => {
      if (m.type() === 'error') consoleErrors.push(m.text());
    });

    console.log('--- 1. Testing /scan at 1920x1080 ---');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('http://127.0.0.1:3107/scan', { waitUntil: 'networkidle' });

    // Step into camera
    await page.getByRole('checkbox', { name: /Tôi đồng ý gửi khung hình/ }).check();
    await page.getByRole('button', { name: 'Mở camera & bắt đầu', exact: true }).click();
    await page.locator('.capture-session').waitFor({ timeout: 10000 });
    await page.locator('.capture-live video').waitFor({ timeout: 10000 });
    await page.waitForTimeout(1000);

    // Measure at 1920x1080
    const videoBox1920 = await page.locator('.capture-live video').boundingBox();
    const stageBox1920 = await page.locator('.capture-stage-wrapper').boundingBox();
    const sidebarBox1920 = await page.locator('.capture-sidebar').boundingBox();
    const actionsBox1920 = await page.locator('.capture-session-actions').boundingBox();
    const scrollH1920 = await page.evaluate(() => document.documentElement.scrollHeight);
    const clientH1920 = await page.evaluate(() => window.innerHeight);

    measurements['1920x1080'] = {
      video: videoBox1920,
      stage: stageBox1920,
      sidebar: sidebarBox1920,
      actions: actionsBox1920,
      scrollHeight: scrollH1920,
      clientHeight: clientH1920,
    };
    console.log('1920x1080 Video BoundingBox:', videoBox1920);
    console.log('1920x1080 Stage BoundingBox:', stageBox1920);

    // Verify instruction is NOT inside .capture-live
    const instructionsInsideLive = await page.locator('.capture-live .capture-instruction').count();
    if (instructionsInsideLive > 0) {
      throw Error('Instruction banner is still inside .capture-live!');
    }

    // Verify view pill is present
    const pillBox = await page.locator('.capture-view-pill').boundingBox();
    console.log('1920x1080 View Pill Box:', pillBox);

    await page.screenshot({ path: path.join(out, 'camera-1920x1080.png'), fullPage: false });

    // --- 2. Test Expand Workspace ("Mở rộng camera") ---
    console.log('--- 2. Testing Expand Workspace button & Escape collapse ---');
    const expandBtn = page.locator('.capture-expand-btn');
    await expandBtn.click();
    await page.waitForTimeout(600);

    const isExpanded = await page.locator('.capture-session.is-expanded').count();
    if (!isExpanded) throw Error('CaptureSession did not enter is-expanded mode');

    const videoBoxExpanded = await page.locator('.capture-live video').boundingBox();
    measurements['1920x1080_expanded'] = { video: videoBoxExpanded };
    console.log('Expanded Video BoundingBox:', videoBoxExpanded);
    await page.screenshot({ path: path.join(out, 'camera-1920x1080-expanded.png'), fullPage: false });

    // Test Escape key collapse
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    const isStillExpanded = await page.locator('.capture-session.is-expanded').count();
    if (isStillExpanded) throw Error('Escape key failed to collapse expanded mode');
    console.log('Escape successfully collapsed expanded mode back to normal grid');

    // --- 3. Measure Laptop 1366x768 ---
    console.log('--- 3. Testing Laptop 1366x768 ---');
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.waitForTimeout(600);

    const videoBox1366 = await page.locator('.capture-live video').boundingBox();
    const stageBox1366 = await page.locator('.capture-stage-wrapper').boundingBox();
    const actionsBox1366 = await page.locator('.capture-session-actions').boundingBox();
    const scrollH1366 = await page.evaluate(() => document.documentElement.scrollHeight);
    const overflow1366 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);

    measurements['1366x768'] = {
      video: videoBox1366,
      stage: stageBox1366,
      actions: actionsBox1366,
      scrollHeight: scrollH1366,
      clientHeight: 768,
      horizontalOverflow: overflow1366,
    };
    console.log('1366x768 Video BoundingBox:', videoBox1366);
    console.log('1366x768 Stage BoundingBox:', stageBox1366);
    console.log('1366x768 Actions Bottom:', actionsBox1366 ? actionsBox1366.y + actionsBox1366.height : null);
    if (overflow1366) throw Error('Horizontal overflow on 1366x768');

    await page.screenshot({ path: path.join(out, 'camera-1366x768.png'), fullPage: false });

    // --- 4. Measure Mobile 390x844 ---
    console.log('--- 4. Testing Mobile 390x844 ---');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(600);

    const videoBox390 = await page.locator('.capture-live video').boundingBox();
    const stageBox390 = await page.locator('.capture-stage-wrapper').boundingBox();
    const overflow390 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    if (overflow390) {
      const bad = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('*'))
          .map(el => {
            const r = el.getBoundingClientRect();
            return { tag: el.tagName, class: el.className, w: el.scrollWidth, r: r.right };
          })
          .filter(item => item.r > 390.5 || item.w > 390.5);
      });
      console.error('Overflowing elements at 390px:', bad);
    }

    measurements['390x844'] = {
      video: videoBox390,
      stage: stageBox390,
      horizontalOverflow: overflow390,
    };
    console.log('390x844 Video BoundingBox:', videoBox390);
    if (overflow390) throw Error('Horizontal overflow on 390x844');

    await page.screenshot({ path: path.join(out, 'camera-390x844.png'), fullPage: true });

    // --- 5. Measure Mobile 360x800 ---
    console.log('--- 5. Testing Mobile 360x800 ---');
    await page.setViewportSize({ width: 360, height: 800 });
    await page.waitForTimeout(600);

    const videoBox360 = await page.locator('.capture-live video').boundingBox();
    const stageBox360 = await page.locator('.capture-stage-wrapper').boundingBox();
    const overflow360 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    if (overflow360) {
      const bad = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('*'))
          .map(el => {
            const r = el.getBoundingClientRect();
            return { tag: el.tagName, class: el.className, w: el.scrollWidth, r: r.right };
          })
          .filter(item => item.r > 360.5 || item.w > 360.5);
      });
      console.error('Overflowing elements at 360px:', bad);
    }

    measurements['360x800'] = {
      video: videoBox360,
      stage: stageBox360,
      horizontalOverflow: overflow360,
    };
    console.log('360x800 Video BoundingBox:', videoBox360);
    if (overflow360) throw Error('Horizontal overflow on 360x800');

    await page.screenshot({ path: path.join(out, 'camera-360x800.png'), fullPage: true });

    // --- 6. Test Modal Flow & Modal Expansion ---
    console.log('--- 6. Testing Modal in Storefront ---');
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('http://127.0.0.1:3107', { waitUntil: 'networkidle' });

    // Open size modal
    await page.getByRole('button', { name: /Bạn chưa chắc về size/ }).click();
    await page.locator('.shop-modal.fit-modal').waitFor();

    // Check consent & start
    await page.getByRole('checkbox', { name: /Tôi đồng ý gửi khung hình/ }).check();
    await page.getByRole('button', { name: 'Mở camera & bắt đầu', exact: true }).click();
    await page.locator('.capture-session').waitFor();
    await page.waitForTimeout(800);

    const modalVideoBox = await page.locator('.capture-live video').boundingBox();
    measurements['modal_1440x900'] = { video: modalVideoBox };
    console.log('Modal Video BoundingBox:', modalVideoBox);
    await page.screenshot({ path: path.join(out, 'camera-modal-1440x900.png'), fullPage: false });

    // Expand inside modal
    await page.locator('.capture-expand-btn').click();
    await page.waitForTimeout(500);
    const modalExpandedVideo = await page.locator('.capture-live video').boundingBox();
    measurements['modal_expanded'] = { video: modalExpandedVideo };
    console.log('Modal Expanded Video BoundingBox:', modalExpandedVideo);
    await page.screenshot({ path: path.join(out, 'camera-modal-expanded.png'), fullPage: false });

    // Escape collapse inside modal
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    const modalStillOpen = await page.locator('.shop-modal.fit-modal').count();
    if (!modalStillOpen) throw Error('Escape accidentally closed modal instead of collapsing');
    const modalSessionStillOpen = await page.locator('.capture-session').count();
    if (!modalSessionStillOpen) throw Error('Escape cancelled capture session inside modal');
    console.log('Modal expand Escape collapse passed: modal and capture session remain intact!');

    // Close modal
    await page.getByRole('button', { name: 'Đóng camera', exact: true }).click();
    await page.getByRole('button', { name: 'Đóng Tìm size của tôi', exact: true }).click();

    // --- 7. Full Automated Scan Sequence Verification ---
    console.log('--- 7. Full automated capture sequence ---');
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto('http://127.0.0.1:3107/scan', { waitUntil: 'networkidle' });
    await page.getByRole('checkbox', { name: /Tôi đồng ý gửi khung hình/ }).check();
    await page.getByRole('button', { name: 'Mở camera & bắt đầu', exact: true }).click();

    // Click "Bắt đầu quét"
    await page.getByRole('button', { name: 'Bắt đầu quét', exact: true }).click();
    await page.waitForTimeout(2000);

    // Front pose
    await page.evaluate(() => (window.__cameraFixture = 'front'));
    await page.locator('.capture-count').waitFor({ timeout: 20000 });
    const countBox = await page.locator('.capture-count').boundingBox();
    const liveBox = await page.locator('.capture-live').boundingBox();
    console.log('Countdown circle box:', countBox);
    console.log('Live container box:', liveBox);

    // Verify countdown is centered
    const countCenterX = countBox.x + countBox.width / 2;
    const liveCenterX = liveBox.x + liveBox.width / 2;
    if (Math.abs(countCenterX - liveCenterX) > 10) {
      console.warn('Countdown circle slightly off-center horizontally:', countCenterX, liveCenterX);
    } else {
      console.log('Countdown circle perfectly centered horizontally!');
    }

    await page.screenshot({ path: path.join(out, 'camera-countdown-front.png'), fullPage: false });

    // Wait for transition screen 90 deg
    await page.getByRole('heading', { name: 'Xoay người 90°', exact: true }).waitFor({ timeout: 30000 });
    await page.screenshot({ path: path.join(out, 'camera-transition-90deg.png'), fullPage: false });

    // Side pose
    await page.evaluate(() => (window.__cameraFixture = 'side'));
    await page.locator('.capture-count').waitFor({ timeout: 20000 });
    await page.screenshot({ path: path.join(out, 'camera-countdown-side.png'), fullPage: false });

    // Wait for 3D model result screen
    await page.getByRole('heading', { name: 'Hình thể 3D của bạn', exact: true }).waitFor({ timeout: 60000 });
    await page.locator('.scan-stage canvas').waitFor();
    await page.waitForTimeout(1500);

    await page.screenshot({ path: path.join(out, 'camera-result-desktop.png'), fullPage: true });

    // Save final measurements
    fs.writeFileSync(
      path.join(out, 'measurements.json'),
      JSON.stringify({ measurements, errors, consoleErrors, success: true }, null, 2)
    );

    console.log('ALL CAMERA LAYOUT VERIFICATIONS PASSED SUCCESSFULLY!');
  } finally {
    if (browser) await browser.close();
    for (const p of children) p.kill();
  }
})().catch((e) => {
  console.error('VERIFICATION FAILED:', e);
  process.exitCode = 1;
});
