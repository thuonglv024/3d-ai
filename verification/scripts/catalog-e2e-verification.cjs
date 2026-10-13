const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const out = path.join(root, 'output/playwright/catalog-upgrade');
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

    console.log('Waiting for backend and frontend to be ready...');
    await ready('http://127.0.0.1:8000/api/health');
    console.log('Backend ready on 8000.');
    await ready('http://127.0.0.1:3000');
    console.log('Frontend ready on 3000.');

    browser = await chromium.launch({
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    });
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();

    // 1. Verify Backend Catalog API Directly
    console.log('1. Verifying Backend Catalog Endpoints...');
    const catRes = await page.request.get('http://127.0.0.1:8000/api/products/categories');
    const categories = await catRes.json();
    record('Backend categories count', categories.length === 5, `Got ${categories.length} categories`);

    const prodRes = await page.request.get('http://127.0.0.1:8000/api/products?page=1&limit=24');
    const paginatedProds = await prodRes.json();
    record('Backend total products >= 150', paginatedProds.total >= 150, `Total: ${paginatedProds.total}`);
    record('Backend page size is 24', paginatedProds.items.length === 24, `Page 1 count: ${paginatedProds.items.length}`);
    const totalPages = paginatedProds.totalPages || paginatedProds.total_pages || 0;
    record('Backend total pages >= 7', totalPages >= 7, `Total pages: ${totalPages}`);

    // 2. Test Storefront Homepage & Pagination
    console.log('2. Testing Storefront UI...');
    await page.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
    await page.waitForSelector('.product-card');

    const cardCount = await page.locator('.product-card').count();
    record('Storefront initial card count is 24', cardCount === 24, `Rendered ${cardCount} cards`);

    await page.screenshot({ path: path.join(out, '01_storefront_page1.png'), fullPage: false });

    // Verify pagination controls
    const pagination = page.locator('.catalog-pagination-wrap, .catalog-pagination');
    const hasPagination = (await pagination.count()) > 0;
    record('Pagination controls exist', hasPagination);

    const statusText = (await page.locator('.pagination-status').textContent()) || '';
    record(
      'Pagination status shows 160 items',
      statusText.includes('24') && statusText.includes('160'),
      `Status: ${statusText.trim()}`
    );

    // Click Page 2
    console.log('Navigating to Page 2...');
    const page2Btn = page.locator('.pagination-controls button, .pagination-btn').filter({ hasText: /^2$/ });
    if ((await page2Btn.count()) > 0) {
      await page2Btn.click();
      await page.waitForTimeout(600);
      const url = page.url();
      record('URL synced to page 2', url.includes('page=2'), `URL: ${url}`);
      await page.screenshot({ path: path.join(out, '02_storefront_page2.png'), fullPage: false });
    }

    // 3. Test Category Filtering
    console.log('3. Testing Category Filtering...');
    const shirtTab = page.locator('.category-tab, .filter-category-btn, button').filter({ hasText: 'Sơ mi' }).first();
    if ((await shirtTab.count()) > 0) {
      await shirtTab.click();
      await page.waitForTimeout(600);
      const url = page.url();
      record('Category filter URL updated to so-mi', url.includes('so-mi'), `URL: ${url}`);
      await page.screenshot({ path: path.join(out, '03_category_so_mi.png'), fullPage: false });
    }

    // 4. Test Product Detail Page
    console.log('4. Testing Product Detail Page...');
    await page.goto('http://127.0.0.1:3000/products/ao-thun-essential', { waitUntil: 'networkidle' });
    await page.waitForSelector('.product-detail, .product-detail-view, main');

    const heading = (await page.locator('h1').textContent()) || '';
    record('Product detail title', heading.includes('Essential'), `Heading: ${heading.trim()}`);

    // Check stock badge
    const stockBadge = (await page.locator('.product-stock-badge').textContent()) || '';
    record('Stock badge displayed', stockBadge.includes('Còn hàng'), `Stock badge: ${stockBadge.trim()}`);

    await page.screenshot({ path: path.join(out, '04_product_detail.png'), fullPage: false });

    // 5. Test Add to Cart & Checkout Flow
    console.log('5. Testing Add to Cart and Checkout...');
    // Select size M
    const sizeBtn = page.locator('.product-sizes button, button').filter({ hasText: /^M$/ }).first();
    if ((await sizeBtn.count()) > 0) {
      await sizeBtn.click();
      await page.waitForTimeout(200);
    }

    // Click Add to cart
    const addCartBtn = page.locator('.add-to-cart-btn, button').filter({ hasText: /Thêm vào giỏ/i }).first();
    await addCartBtn.click();
    await page.waitForTimeout(800);

    await page.screenshot({ path: path.join(out, '05_cart_drawer.png'), fullPage: false });

    // Navigate to checkout
    console.log('Proceeding to checkout...');
    await page.goto('http://127.0.0.1:3000/checkout', { waitUntil: 'networkidle' });
    await page.waitForSelector('#fullName');

    // Fill checkout form
    const nameInput = page.locator('#fullName');
    const phoneInput = page.locator('#phone');
    const addressInput = page.locator('#address');

    await nameInput.fill('Nguyễn Văn An');
    await phoneInput.fill('0901234567');
    await addressInput.fill('123 Đường Đồng Khởi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh');

    await page.screenshot({ path: path.join(out, '06_checkout_form.png'), fullPage: false });

    // Submit order
    const submitBtn = page.locator('button[type="submit"], button').filter({ hasText: /Đặt hàng|Hoàn tất/i }).first();
    await submitBtn.click();
    await page.waitForTimeout(2500);

    const orderUrl = page.url();
    const orderCreated = orderUrl.includes('/orders/');
    record('Order creation redirected to order success page', orderCreated, `URL: ${orderUrl}`);

    await page.screenshot({ path: path.join(out, '07_order_success.png'), fullPage: false });

    // 6. Test Scan Searchable Product Picker
    console.log('6. Testing /scan searchable product picker...');
    await page.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });
    await page.waitForSelector('.product-picker-trigger');

    // Click product picker button to open popover
    const pickerTrigger = page.locator('.product-picker-trigger').first();
    await pickerTrigger.click();
    await page.waitForTimeout(500);

    const popoverExists = (await page.locator('.product-picker-popover').count()) > 0;
    record('Product picker popover opened', popoverExists);

    // Search in popover
    const searchInput = page.locator('.picker-search-input');
    if ((await searchInput.count()) > 0) {
      await searchInput.fill('Linen');
      await page.waitForTimeout(400);
      const filteredCount = await page.locator('.picker-product-item').count();
      record('Picker search filtered products', filteredCount > 0, `Matching items: ${filteredCount}`);
    }

    await page.screenshot({ path: path.join(out, '08_scan_product_picker.png'), fullPage: false });

    console.log('\n--- VERIFICATION SUMMARY ---');
    console.table(testResults);

    const allPassed = testResults.every((t) => t.passed);
    fs.writeFileSync(
      path.join(out, 'verification_summary.json'),
      JSON.stringify({ passed: allPassed, tests: testResults }, null, 2),
      'utf-8'
    );

    if (!allPassed) {
      process.exitCode = 1;
    }
  } catch (err) {
    console.error('Test execution failed:', err);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    for (const c of children) {
      try {
        c.kill();
      } catch {}
    }
  }
})();
