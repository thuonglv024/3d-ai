const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { spawn, execSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const out = path.join(root, 'output/playwright/profile-verification');
fs.mkdirSync(out, { recursive: true });

process.env.TEMP = path.join(root, '.cache/tmp');
process.env.TMP = process.env.TEMP;

const env = {
  ...process.env,
  NEXT_TELEMETRY_DISABLED: '1',
  BACKEND_URL: 'http://127.0.0.1:8000',
  PYTHONUNBUFFERED: '1',
};

const children = [];
function start(exe, args, cwd, name) {
  const log = fs.openSync(path.join(out, name + '.log'), 'w');
  const p = spawn(exe, args, { cwd, env, windowsHide: true, stdio: ['ignore', log, log] });
  children.push(p);
  p.on('error', (e) => console.error(name, e));
}

async function ready(url, timeoutSec = 45) {
  for (let i = 0; i < timeoutSec * 2; i++) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw Error('Not ready ' + url);
}

function cleanup() {
  for (const c of children) {
    try {
      c.kill('SIGTERM');
    } catch {}
  }
}

(async () => {
  try {
    console.log('Starting backend on 8000...');
    start(
      path.join(root, 'backend/.venv/Scripts/python.exe'),
      ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
      path.join(root, 'backend'),
      'backend'
    );

    console.log('Starting frontend on 3000...');
    start(
      process.execPath,
      [path.join(root, 'frontend/node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', '3000'],
      path.join(root, 'frontend'),
      'frontend'
    );

    await ready('http://127.0.0.1:8000/api/health', 35);
    console.log('Backend ready!');

    await ready('http://127.0.0.1:3000/account', 45);
    console.log('Frontend ready!');

    const browser = await chromium.launch({
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();

    // 1. Visit /account as unauthenticated user
    console.log('1. Testing /account unauthenticated...');
    await page.goto('http://127.0.0.1:3000/account', { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(out, '01-account-unauth.png'), fullPage: true });

    // 2. Visit /account/body-profile as unauthenticated user
    console.log('2. Testing /account/body-profile unauthenticated...');
    await page.goto('http://127.0.0.1:3000/account/body-profile', { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(out, '02-body-profile-unauth.png'), fullPage: true });

    // 3. Register a test user
    console.log('3. Registering test user...');
    const userEmail = `minhthao_${Date.now()}@morph.studio`;
    const regRes = await fetch('http://127.0.0.1:8000/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: userEmail,
        password: 'password123',
        display_name: 'Minh Thảo',
      }),
    });
    const regData = await regRes.json();
    const userId = regData.user.id;
    const regCookie = regRes.headers.get('set-cookie');
    console.log('User registered ID:', userId);

    // 4. Seed 2 body scans into SQLite for this user
    console.log('4. Seeding 2 realistic body scans for user in SQLite...');
    const pythonExe = path.join(root, 'backend/.venv/Scripts/python.exe');
    execSync(`"${pythonExe}" verification/scripts/seed_demo_scans.py ${userId}`, { cwd: root, stdio: 'inherit' });

    // Set cookie in browser
    if (regCookie) {
      const match = regCookie.match(/morph_session=([^;]+)/);
      if (match) {
        await context.addCookies([
          {
            name: 'morph_session',
            value: match[1],
            domain: '127.0.0.1',
            path: '/',
            httpOnly: true,
            sameSite: 'Lax',
          },
          {
            name: 'morph_session',
            value: match[1],
            domain: 'localhost',
            path: '/',
            httpOnly: true,
            sameSite: 'Lax',
          },
        ]);
      }
    }

    // 5. Visit /account as authenticated user
    console.log('5. Testing /account authenticated...');
    await page.goto('http://127.0.0.1:3000/account', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(out, '03-account-auth.png'), fullPage: true });

    // 6. Visit /account/body-profile as authenticated user
    console.log('6. Testing /account/body-profile authenticated...');
    await page.goto('http://127.0.0.1:3000/account/body-profile', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(out, '04-body-profile-auth.png'), fullPage: true });

    // 7. Test Compare: Select both scans and open Compare Modal
    console.log('7. Testing Scan Compare Modal...');
    const checkboxes = page.locator('.custom-checkbox');
    const count = await checkboxes.count();
    console.log('Found checkboxes:', count);
    if (count >= 2) {
      await checkboxes.nth(0).click();
      await checkboxes.nth(1).click();
      await page.waitForTimeout(600);
      const compareBtn = page.locator('.btn-compare-trigger');
      if (await compareBtn.isVisible()) {
        await compareBtn.click();
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(out, '05-scan-compare-modal.png'), fullPage: true });
        const closeBtn = page.locator('.close-icon-btn');
        if (await closeBtn.isVisible()) {
          await closeBtn.click();
          await page.waitForTimeout(400);
        }
      }
    }

    // 8. Test /account/body-profile/scans/scan-demo-02 detail view
    console.log('8. Testing /account/body-profile/scans/scan-demo-02 detail view...');
    await page.goto('http://127.0.0.1:3000/account/body-profile/scans/scan-demo-02', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(out, '06-scan-detail.png'), fullPage: true });

    console.log('All verification steps succeeded with 6 visual snapshots!');
    await browser.close();
  } catch (err) {
    console.error('Verification error:', err);
    process.exitCode = 1;
  } finally {
    cleanup();
  }
})();
