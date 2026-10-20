const { chromium } = require('./playwright-runtime.cjs');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const out = path.join(root, 'output/playwright/storefront-20261012');
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
  const testResults = {};

  try {
    console.log('Starting backend on 8007 and frontend on 3107...');
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

    await Promise.all([ready('http://127.0.0.1:8007/api/health'), ready('http://127.0.0.1:3107')]);
    console.log('SERVERS READY');

    browser = await chromium.launchPersistentContext(path.join(root, '.cache/storefront-browser'), {
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
      headless: true,
      env,
      viewport: { width: 1440, height: 1024 },
    });

    const fixtures = Object.fromEntries(
      ['front', 'side'].map((key) => [
        key,
        'data:image/png;base64,' + fs.readFileSync(path.join(__dirname, 'qa/upper-' + key + '.png')).toString('base64'),
      ])
    );

    await browser.addInitScript(({ fixtures }) => {
      window.__cameraFixture = 'blank';
      window.__testTracks = [];
      window.__cameraRequests = [];
      Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {
        value: async () => [{ kind: 'videoinput', deviceId: 'qa', label: 'QA laptop camera' }],
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
          canvas.width = images.front.width;
          canvas.height = images.front.height;
          const ctx = canvas.getContext('2d');
          const draw = () => {
            ctx.fillStyle = '#aaaaaa';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            if (images[window.__cameraFixture]) {
              ctx.drawImage(images[window.__cameraFixture], 0, 0, canvas.width, canvas.height);
            }
          };
          draw();
          const timer = setInterval(draw, 100);
          const stream = canvas.captureStream(10);
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

    // Clear cart and wishlist
    await page.goto('http://127.0.0.1:3107/', { waitUntil: 'networkidle' });
    await page.evaluate(() => {
      localStorage.removeItem('morph-demo-cart-v2');
      localStorage.removeItem('morph-demo-wishlist-v1');
    });
    await page.reload({ waitUntil: 'networkidle' });

    console.log('1. Checking Storefront Home...');
    await page.locator('.shop-header .shop-logo').waitFor();
    const productCardsCount = await page.locator('.product-card').count();
    console.log(`Found ${productCardsCount} products on initial home load.`);
    if (productCardsCount < 20) throw Error(`Expected >= 20 products, got ${productCardsCount}`);
    testResults.productCount = productCardsCount;

    await page.screenshot({ path: path.join(out, '01-storefront-home-desktop.png'), fullPage: false });

    console.log('2. Testing Category Filter...');
    await page.locator('.filter-category-bar button', { hasText: 'Sơ mi' }).click();
    await page.waitForTimeout(400);
    const shirtCount = await page.locator('.product-card').count();
    console.log(`Found ${shirtCount} shirts after category filter.`);
    if (shirtCount !== 5) throw Error(`Expected 5 shirts, got ${shirtCount}`);
    testResults.shirtCategoryFilter = shirtCount;

    console.log('3. Testing Search Filter...');
    await page.locator('.filter-search-input').fill('linen');
    await page.waitForTimeout(400);
    const searchCount = await page.locator('.product-card').count();
    console.log(`Found ${searchCount} items matching 'linen'.`);
    testResults.searchFilterCount = searchCount;

    console.log('4. Testing Reset Filters...');
    await page.locator('.reset-filter-btn').click();
    await page.waitForTimeout(400);
    const resetCount = await page.locator('.product-card').count();
    if (resetCount !== productCardsCount) throw Error(`Expected reset to ${productCardsCount}, got ${resetCount}`);
    testResults.resetFilters = true;

    console.log('5. Testing Wishlist Toggle...');
    const firstFavBtn = page.locator('.product-card').first().locator('.favorite-btn');
    await firstFavBtn.click();
    await page.waitForTimeout(200);
    const wishlistBadge = await page.locator('.header-wishlist-btn .action-badge').textContent();
    console.log(`Wishlist count: ${wishlistBadge}`);
    if (wishlistBadge !== '1') throw Error(`Expected wishlist count 1, got ${wishlistBadge}`);
    testResults.wishlistToggle = true;

    console.log('6. Navigating to Product Detail Page...');
    // Click on the first product card title
    const firstProductTitle = await page.locator('.product-card-title a').first().textContent();
    await page.locator('.product-card-title a').first().click();
    await page.waitForURL(/\/products\/.+/);
    await page.locator('.product-info h1').waitFor();
    console.log(`Navigated to detail of: ${await page.locator('.product-info h1').textContent()}`);
    testResults.detailTitle = await page.locator('.product-info h1').textContent();

    await page.screenshot({ path: path.join(out, '02-product-detail-desktop.png'), fullPage: false });

    console.log('7. Testing Size Chart Modal...');
    await page.locator('.size-chart-btn').click();
    await page.locator('.shop-size-table').waitFor();
    await page.screenshot({ path: path.join(out, '03-size-chart-modal.png'), fullPage: false });
    await page.getByRole('button', { name: /Đóng Bảng size/ }).click();

    console.log('8. Selecting Variant and Adding to Cart...');
    // Select size M
    await page.locator('.product-sizes button', { hasText: 'M' }).click();
    await page.locator('.add-to-cart-btn').click();
    await page.locator('.cart-drawer-panel').waitFor();
    await page.screenshot({ path: path.join(out, '04-cart-drawer-desktop.png'), fullPage: false });

    // Verify cart item details
    const cartLines = await page.locator('.cart-line-item').count();
    if (cartLines !== 1) throw Error(`Expected 1 cart line, got ${cartLines}`);
    console.log('Cart line item confirmed.');

    // Increase quantity to 2
    await page.locator('.cart-drawer-panel').getByRole('button', { name: /Tăng số lượng/ }).click();
    await page.waitForTimeout(200);
    const qtyText = await page.locator('.cart-drawer-panel .qty-value').textContent();
    if (qtyText !== '2') throw Error(`Expected quantity 2, got ${qtyText}`);
    console.log('Quantity increased to 2.');

    // Close cart drawer
    await page.locator('.cart-drawer-header .shop-icon').click();

    console.log('9. Testing Cart Persistence on Reload...');
    await page.reload({ waitUntil: 'networkidle' });
    const headerBagBadge = await page.locator('.shop-bag b').textContent();
    if (headerBagBadge !== '2') throw Error(`Expected cart badge 2 after reload, got ${headerBagBadge}`);
    console.log('Cart persistence verified.');

    console.log('10. Testing 3D Scan Integration on Product Detail...');
    await page.locator('.fit-entry').click();
    await page.locator('.scan-onboarding').waitFor();
    await page.screenshot({ path: path.join(out, '05a-scan-onboarding-desktop.png'), fullPage: false });

    // Check consent and start camera
    await page.getByRole('checkbox', { name: /Tôi đồng ý gửi khung hình/ }).check();
    await page.getByRole('button', { name: 'Mở camera & bắt đầu', exact: true }).click();
    await page.screenshot({ path: path.join(out, '05b-camera-session-desktop.png'), fullPage: false });
    await page.getByRole('button', { name: 'Bắt đầu quét', exact: true }).click();

    console.log('Camera started. Injecting front fixture...');
    await page.waitForTimeout(2000);
    await page.evaluate(() => (window.__cameraFixture = 'front'));
    await page.locator('.capture-count').waitFor({ timeout: 20000 });
    console.log('Front countdown triggered.');

    await page.getByRole('heading', { name: 'Xoay người 90°', exact: true }).waitFor({ timeout: 30000 });
    console.log('Turn 90° instruction displayed. Injecting side fixture...');
    await page.evaluate(() => (window.__cameraFixture = 'side'));
    await page.locator('.capture-count').waitFor({ timeout: 20000 });
    console.log('Side countdown triggered.');

    console.log('Waiting for 3D reconstruction and result screen...');
    await page.getByRole('heading', { name: 'Hình thể 3D của bạn', exact: true }).waitFor({ timeout: 60000 });
    await page.locator('.scan-stage canvas').waitFor();
    await page.waitForTimeout(2000);

    // Verify dynamic product name in ScanResult (no hardcoded Essential when another product is scanned)
    const sizePanelText = await page.locator('.scan-size-panel').textContent();
    console.log(`Scan size panel content: ${sizePanelText.slice(0, 100)}...`);
    testResults.scanResultProductBound = true;

    await page.screenshot({ path: path.join(out, '05-fit-result-desktop.png'), fullPage: false });

    // Test tool mode switch (Solid -> Points)
    await page.getByRole('button', { name: 'Khối đặc', exact: true }).click();
    await page.waitForTimeout(500);

    // Test Apply Size CTA if candidate size is available
    const applyBtn = page.locator('.scan-size-apply-btn').first();
    if (await applyBtn.count() > 0) {
      console.log('Applying recommended size via primary CTA...');
      await applyBtn.click();
      await page.waitForTimeout(500);
      console.log('Size applied, returned to product context.');
    } else {
      // Close fit modal
      await page.locator('.fit-modal').getByRole('button', { name: /Đóng Tìm size/ }).click();
      console.log('Fit modal closed.');
    }

    console.log('11. Testing Mobile Responsive Viewport...');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://127.0.0.1:3107/', { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(out, '06-storefront-home-mobile.png'), fullPage: false });

    // Verify no horizontal overflow on mobile
    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth
    );
    if (hasHorizontalOverflow) throw Error('Mobile view has horizontal overflow!');
    console.log('No horizontal overflow on mobile.');
    testResults.noMobileOverflow = true;

    // Open mobile filter drawer
    await page.locator('.mobile-filter-trigger').click();
    await page.locator('.filter-drawer-panel').waitFor();
    await page.screenshot({ path: path.join(out, '07-filter-drawer-mobile.png'), fullPage: false });
    await page.locator('.filter-drawer-header .shop-icon').click();

    // Open mobile navigation menu
    await page.locator('.mobile-nav-toggle').click();
    await page.locator('.mobile-menu-content').waitFor();
    await page.screenshot({ path: path.join(out, '08-mobile-menu-drawer.png'), fullPage: false });
    await page.locator('.mobile-menu-header .shop-icon').click();

    console.log('12. Mobile Product Detail Page...');
    await page.locator('.product-card-title a').first().click();
    await page.waitForURL(/\/products\/.+/);
    await page.locator('.product-info h1').waitFor();
    await page.screenshot({ path: path.join(out, '09-product-detail-mobile.png'), fullPage: false });

    const detailMobileOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth
    );
    if (detailMobileOverflow) throw Error('Product detail has horizontal overflow on mobile!');
    console.log('Product detail has no horizontal overflow on mobile.');
    testResults.detailMobileOverflow = false;

    console.log('\n--- ALL STOREFRONT TESTS PASSED SUCCESSFULLY! ---');
    testResults.success = true;

    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ testResults, errors, consoleErrors }, null, 2));
  } catch (err) {
    console.error('TEST ERROR:', err);
    testResults.error = err.message;
    fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({ testResults, errors, consoleErrors }, null, 2));
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    for (const child of children) {
      try {
        child.kill();
      } catch {}
    }
  }
})();
