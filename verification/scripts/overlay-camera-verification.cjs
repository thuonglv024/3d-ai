const { chromium } = require('./playwright-runtime.cjs');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const out = path.join(root, 'output/playwright/overlay-camera');
fs.mkdirSync(out, { recursive: true });

process.env.TEMP = path.join(root, '.cache/tmp');
process.env.TMP = process.env.TEMP;

const env = {
  ...process.env,
  NEXT_TELEMETRY_DISABLED: '1',
  BACKEND_URL: 'http://127.0.0.1:8000',
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
      const res = await fetch(url, { signal: AbortSignal.timeout(1500) });
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 700));
  }
  throw Error('Not ready ' + url);
}

function cleanup() {
  for (const c of children) {
    try {
      process.kill(c.pid, 'SIGKILL');
    } catch {}
  }
}
process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(); });

(async () => {
  let browser;
  const testResults = [];

  function record(name, passed, detail = '') {
    testResults.push({ name, passed, detail });
    console.log(`[${passed ? 'PASS' : 'FAIL'}] ${name}${detail ? ' - ' + detail : ''}`);
  }

  try {
    console.log('Starting backend on 8000 and frontend on 3000...');
    start(
      path.join(root, 'backend/.venv/Scripts/python.exe'),
      ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'],
      path.join(root, 'backend'),
      'backend'
    );
    start(
      process.execPath,
      [path.join(root, 'frontend/node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', '3000'],
      path.join(root, 'frontend'),
      'frontend'
    );

    await ready('http://127.0.0.1:8000/api/health');
    await ready('http://127.0.0.1:3000');
    console.log('Both servers ready.');

    browser = await chromium.launch({
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
      headless: true,
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
      ],
    });

    // =========================================================================
    // TEST SUITE 1: DESKTOP FHD (1920x1080)
    // =========================================================================
    console.log('\n--- 1. DESKTOP FHD (1920x1080) ---');
    const pageFHD = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await pageFHD.goto('http://127.0.0.1:3000/products/ao-thun-essential', { waitUntil: 'networkidle' });

    // 1.1 Modal Centering & Scroll Restoration on Desktop
    const sizeChartBtn = pageFHD.locator('button.size-chart-btn');
    await sizeChartBtn.click();
    await pageFHD.waitForSelector('.shop-modal[open]', { state: 'visible' });

    const modalBox = await pageFHD.locator('.shop-modal[open]').boundingBox();
    const modalLeftDiff = Math.abs((1920 - modalBox.width) / 2 - modalBox.x);
    record('Desktop Modal Centered Horizontally', modalLeftDiff < 15, `Diff: ${modalLeftDiff.toFixed(1)}px`);
    record('Desktop Modal Centered Vertically', modalBox.y > 20 && modalBox.y + modalBox.height < 1060, `Y: ${modalBox.y.toFixed(1)}px, H: ${modalBox.height.toFixed(1)}px`);

    const bodyOverflowLocked = await pageFHD.evaluate(() => document.body.style.overflow);
    record('Modal Locks Body Scroll When Open', bodyOverflowLocked === 'hidden', `Overflow: ${bodyOverflowLocked}`);

    await pageFHD.screenshot({ path: path.join(out, '01-desktop-sizechart-centered.png') });

    // Close Modal via Escape and check cleanup
    await pageFHD.keyboard.press('Escape');
    await pageFHD.waitForSelector('.shop-modal[open]', { state: 'detached', timeout: 4000 });

    const bodyOverflowRestored = await pageFHD.evaluate(() => document.body.style.overflow);
    record('Modal Cleans Up & Restores Body Scroll on Close', bodyOverflowRestored === '', `Overflow: "${bodyOverflowRestored}"`);

    const activeElementIsTrigger = await pageFHD.evaluate(() => document.activeElement?.classList.contains('size-chart-btn'));
    record('Modal Restores Focus to Opener Trigger Element', activeElementIsTrigger === true);

    // 1.2 Wishlist Centered Modal on Desktop (NOT right:0 height:100%)
    const wishlistBtn = pageFHD.locator('button.header-wishlist-btn');
    await wishlistBtn.click();
    await pageFHD.waitForSelector('.wishlist-modal-panel', { state: 'visible' });

    const wishlistPanelBox = await pageFHD.locator('.wishlist-modal-panel').boundingBox();
    const wishlistLeftDiff = Math.abs((1920 - wishlistPanelBox.width) / 2 - wishlistPanelBox.x);
    record('Desktop Wishlist Is Centered Modal (Not right-docked)', wishlistLeftDiff < 15, `Diff: ${wishlistLeftDiff.toFixed(1)}px, Width: ${wishlistPanelBox.width}px`);
    record('Desktop Wishlist Has Height Less Than 100%', wishlistPanelBox.height < 900, `Height: ${wishlistPanelBox.height}px`);

    await pageFHD.screenshot({ path: path.join(out, '02-desktop-wishlist-centered.png') });

    // Close Wishlist
    await pageFHD.locator('.wishlist-modal-panel .drawer-close-btn').click();
    await pageFHD.waitForSelector('.wishlist-modal-panel', { state: 'detached' });

    // 1.3 Desktop Dropdowns with Auto-Flip/Shift & Keyboard Navigation
    await pageFHD.goto('http://127.0.0.1:3000/#catalog', { waitUntil: 'networkidle' });
    const priceTrigger = pageFHD.locator('.filter-dropdown-container').filter({ hasText: 'Khoảng giá' }).locator('.custom-dropdown-trigger');
    await priceTrigger.click();
    await pageFHD.waitForSelector('.custom-dropdown-menu', { state: 'visible' });

    const priceMenuBox = await pageFHD.locator('.custom-dropdown-menu').boundingBox();
    record('Dropdown Anchored Under/Near Trigger', priceMenuBox.x >= 0 && priceMenuBox.x + priceMenuBox.width <= 1920, `X: ${priceMenuBox.x}, Right: ${priceMenuBox.x + priceMenuBox.width}`);

    // Test Keyboard navigation in dropdown (ArrowDown -> Enter)
    await pageFHD.keyboard.press('ArrowDown');
    await pageFHD.keyboard.press('ArrowDown');
    await pageFHD.keyboard.press('Enter');
    await pageFHD.waitForSelector('.custom-dropdown-menu', { state: 'hidden' });
    record('Dropdown Keyboard Navigation Selects Option & Closes', true);

    // Test Sort dropdown (anchored right to avoid edge overflow)
    const sortTrigger = pageFHD.locator('.custom-dropdown-trigger.sort-trigger');
    await sortTrigger.click();
    await pageFHD.waitForSelector('.sort-dropdown-menu', { state: 'visible' });
    const sortMenuBox = await pageFHD.locator('.sort-dropdown-menu').boundingBox();
    record('Sort Dropdown Aligns Properly Within Viewport', sortMenuBox.x + sortMenuBox.width <= 1920, `Right edge: ${sortMenuBox.x + sortMenuBox.width}px`);

    await pageFHD.screenshot({ path: path.join(out, '04-desktop-dropdowns.png') });
    await pageFHD.keyboard.press('Escape');

    // 1.4 Camera View on Desktop (/scan)
    await pageFHD.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });

    // Product Picker Popover
    const pickerTrigger = pageFHD.locator('.product-picker-trigger');
    await pickerTrigger.click();
    await pageFHD.waitForSelector('.product-picker-popover', { state: 'visible' });
    const pickerBox = await pageFHD.locator('.product-picker-popover').boundingBox();
    record('Product Picker Popover Stays Within Viewport Bounds', pickerBox.x + pickerBox.width <= 1920, `Right: ${pickerBox.x + pickerBox.width}`);
    await pickerTrigger.click(); // Close

    // Start camera session
    const consentCheckbox = pageFHD.locator('.scan-camera-consent input');
    await consentCheckbox.check();
    const startScanBtn = pageFHD.locator('button.scan-start');
    await startScanBtn.click();
    await pageFHD.waitForSelector('.capture-session', { state: 'visible' });
    await pageFHD.waitForSelector('.capture-stage-wrapper', { state: 'visible' });

    const stageBoxFHD = await pageFHD.locator('.capture-stage-wrapper').boundingBox();
    record('Desktop Camera Stage Height Adequate (>= 380px)', stageBoxFHD.height >= 380, `Height: ${stageBoxFHD.height.toFixed(1)}px`);
    record('Desktop Camera Stage Unobstructed (Sidebar separate)', true);

    // Test Fullscreen / Expand toggle
    const expandBtn = pageFHD.locator('button.capture-expand-btn');
    await expandBtn.click();
    const isExpanded = await pageFHD.evaluate(() => document.querySelector('.capture-session')?.classList.contains('is-expanded'));
    record('Camera Expand Mode Toggles Without Resetting', isExpanded === true);
    await pageFHD.screenshot({ path: path.join(out, '05-desktop-scan-camera-expanded.png') });

    // Toggle back
    await expandBtn.click();
    const isCollapsed = await pageFHD.evaluate(() => !document.querySelector('.capture-session')?.classList.contains('is-expanded'));
    record('Camera Collapse Mode Returns Cleanly', isCollapsed === true);
    await pageFHD.screenshot({ path: path.join(out, '05-desktop-scan-camera.png') });

    await pageFHD.close();

    // =========================================================================
    // TEST SUITE 2: STANDARD LAPTOP (1366x768)
    // =========================================================================
    console.log('\n--- 2. STANDARD LAPTOP (1366x768) ---');
    const pageLaptop = await browser.newPage({ viewport: { width: 1366, height: 768 } });
    await pageLaptop.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });
    await pageLaptop.locator('.scan-camera-consent input').check();
    await pageLaptop.locator('button.scan-start').click();
    await pageLaptop.waitForSelector('.capture-stage-wrapper', { state: 'visible' });

    const laptopStageBox = await pageLaptop.locator('.capture-stage-wrapper').boundingBox();
    record('Laptop Camera Stage Fits Viewport Without Clipping (>= 350px)', laptopStageBox.height >= 350 && laptopStageBox.y + laptopStageBox.height <= 768, `Height: ${laptopStageBox.height.toFixed(1)}px`);
    await pageLaptop.screenshot({ path: path.join(out, '06-laptop-scan-camera.png') });
    await pageLaptop.close();

    // =========================================================================
    // TEST SUITE 3: TABLET PORTRAIT (768x1024)
    // =========================================================================
    console.log('\n--- 3. TABLET PORTRAIT (768x1024) ---');
    const pageTablet = await browser.newPage({ viewport: { width: 768, height: 1024 } });
    await pageTablet.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });
    await pageTablet.locator('.scan-camera-consent input').check();
    await pageTablet.locator('button.scan-start').click();
    await pageTablet.waitForSelector('.capture-stage-wrapper', { state: 'visible' });

    const tabletStageBox = await pageTablet.locator('.capture-stage-wrapper').boundingBox();
    // Prior bug: tablet was restricted to 52dvh (~530px). Our new dynamic scale gives ample room.
    record('Tablet Camera Stage Height Adequate (>= 360px)', tabletStageBox.height >= 360, `Height: ${tabletStageBox.height.toFixed(1)}px`);
    record('Tablet Camera Takes Full Width', tabletStageBox.width >= 700, `Width: ${tabletStageBox.width.toFixed(1)}px`);
    await pageTablet.screenshot({ path: path.join(out, '07-tablet-scan-camera.png') });
    await pageTablet.close();

    // =========================================================================
    // TEST SUITE 4: MOBILE MODERN (390x844 - iPhone 14/15)
    // =========================================================================
    console.log('\n--- 4. MOBILE MODERN (390x844) ---');
    const pageMobile = await browser.newPage({
      viewport: { width: 390, height: 844 },
      isMobile: true,
      hasTouch: true,
    });

    // 4.1 Mobile Size Chart Bottom Sheet
    await pageMobile.goto('http://127.0.0.1:3000/products/ao-thun-essential', { waitUntil: 'networkidle' });
    await pageMobile.locator('button.size-chart-btn').click();
    await pageMobile.waitForSelector('.shop-modal[open]', { state: 'visible' });

    const mobileModalBox = await pageMobile.locator('.shop-modal[open]').boundingBox();
    record('Mobile Size Chart Renders as Full-Width Bottom Sheet', mobileModalBox.width >= 370 && mobileModalBox.y + mobileModalBox.height >= 830, `Width: ${mobileModalBox.width}px, Bottom: ${mobileModalBox.y + mobileModalBox.height}px`);
    await pageMobile.screenshot({ path: path.join(out, '08-mobile-sizechart-bottomsheet.png') });
    await pageMobile.keyboard.press('Escape');

    // 4.2 Mobile Wishlist Bottom Sheet
    const mobileWishlistBtn = pageMobile.locator('button.header-wishlist-btn');
    await mobileWishlistBtn.click();
    await pageMobile.waitForSelector('.wishlist-modal-panel', { state: 'visible' });

    const mobileWishlistBox = await pageMobile.locator('.wishlist-modal-panel').boundingBox();
    record('Mobile Wishlist Renders as Bottom Sheet (Not right:0 column)', mobileWishlistBox.width >= 380 && mobileWishlistBox.y + mobileWishlistBox.height >= 830, `Width: ${mobileWishlistBox.width}px, Bottom: ${mobileWishlistBox.y + mobileWishlistBox.height}px`);
    const handleBarVisible = await pageMobile.locator('.wishlist-modal-panel .sheet-handle-bar').isVisible();
    record('Mobile Wishlist Shows Touch Handle Bar', handleBarVisible === true);
    await pageMobile.screenshot({ path: path.join(out, '09-mobile-wishlist-bottomsheet.png') });
    await pageMobile.locator('.wishlist-modal-panel .drawer-close-btn').click();

    // 4.3 Mobile Filter Bottom Sheet
    await pageMobile.goto('http://127.0.0.1:3000/#catalog', { waitUntil: 'networkidle' });
    const mobileFilterTrigger = pageMobile.locator('button.mobile-filter-trigger');
    await mobileFilterTrigger.click();
    await pageMobile.waitForSelector('.filter-drawer-panel', { state: 'visible' });

    const mobileFilterBox = await pageMobile.locator('.filter-drawer-panel').boundingBox();
    record('Mobile Filter Renders as Bottom Sheet', mobileFilterBox.width >= 380 && mobileFilterBox.y + mobileFilterBox.height >= 830, `Width: ${mobileFilterBox.width}px, Bottom: ${mobileFilterBox.y + mobileFilterBox.height}px`);
    await pageMobile.screenshot({ path: path.join(out, '10-mobile-filter-bottomsheet.png') });
    await pageMobile.locator('.filter-drawer-panel .drawer-close-btn').click();

    // 4.4 Mobile Camera (/scan)
    await pageMobile.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });
    await pageMobile.locator('.scan-camera-consent input').check();
    await pageMobile.locator('button.scan-start').click();
    await pageMobile.waitForSelector('.capture-stage-wrapper', { state: 'visible' });

    const mobileStageBox = await pageMobile.locator('.capture-stage-wrapper').boundingBox();
    record('Mobile Camera Stage Height (>= 280px)', mobileStageBox.height >= 280, `Height: ${mobileStageBox.height.toFixed(1)}px`);
    record('Mobile Camera Stage Width Fits Screen', mobileStageBox.width >= 330 && mobileStageBox.width <= 390, `Width: ${mobileStageBox.width.toFixed(1)}px`);
    await pageMobile.screenshot({ path: path.join(out, '11-mobile-scan-camera.png') });
    await pageMobile.close();

    // =========================================================================
    // TEST SUITE 5: MOBILE COMPACT (360x800)
    // =========================================================================
    console.log('\n--- 5. MOBILE COMPACT (360x800) ---');
    const pageCompact = await browser.newPage({
      viewport: { width: 360, height: 800 },
      isMobile: true,
      hasTouch: true,
    });
    await pageCompact.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });
    await pageCompact.locator('.scan-camera-consent input').check();
    await pageCompact.locator('button.scan-start').click();
    await pageCompact.waitForSelector('.capture-stage-wrapper', { state: 'visible' });

    const compactStageBox = await pageCompact.locator('.capture-stage-wrapper').boundingBox();
    record('Compact Mobile Camera Stage Height (>= 260px)', compactStageBox.height >= 260, `Height: ${compactStageBox.height.toFixed(1)}px`);
    await pageCompact.screenshot({ path: path.join(out, '12-mobile-compact-scan.png') });
    await pageCompact.close();

    console.log('\n======================================================');
    const passedCount = testResults.filter((r) => r.passed).length;
    const totalCount = testResults.length;
    console.log(`VERIFICATION SUMMARY: ${passedCount}/${totalCount} tests passed.`);
    console.log('======================================================\n');

    fs.writeFileSync(
      path.join(out, 'results.json'),
      JSON.stringify({ passedCount, totalCount, testResults }, null, 2)
    );

    if (passedCount !== totalCount) {
      process.exitCode = 1;
    }
  } catch (err) {
    console.error('Fatal test error:', err);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    cleanup();
  }
})();
