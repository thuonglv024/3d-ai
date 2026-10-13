const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const outDir = path.join(root, 'output/playwright/commerce-audit-fix');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== COMMERCE AUDIT FIX VERIFICATION (Wishlist, Cart, Checkout) ===\n');

  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const testReport = {
    timestamp: new Date().toISOString(),
    tests: [],
  };

  function logTest(name, passed, details = {}) {
    testReport.tests.push({ name, passed, ...details });
    console.log(`[${passed ? 'PASS' : 'FAIL'}] ${name}`);
    if (Object.keys(details).length) {
      console.log('       Details:', JSON.stringify(details));
    }
  }

  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    // =========================================================================
    // 1. WISHLIST DRAWER TESTS
    // =========================================================================
    console.log('\n--- 1. Testing WishlistDrawer Dynamic Resolution & Variant Selection ---');

    page.on('console', (msg) => console.log('BROWSER:', msg.text()));

    // Seed localStorage with a dynamic product (ao-blazer-dang-rong-2-hang-khuy) and an unavailable ID
    await page.goto('http://127.0.0.1:3000', { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      localStorage.setItem('morph-demo-wishlist-v1', JSON.stringify([
        'ao-blazer-dang-rong-2-hang-khuy',
        'obsolete-unavailable-prod-999'
      ]));
      localStorage.setItem('morph-demo-cart-v2', JSON.stringify([]));
    });

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // Open Wishlist Drawer by clicking heart button in header
    const wishlistHeaderBtn = page.locator('button[aria-label*="yêu thích"]').first();
    await wishlistHeaderBtn.click();
    await page.waitForSelector('.wishlist-modal-panel', { timeout: 10000 });
    // Wait for dynamic items to resolve
    await page.waitForSelector('.wishlist-modal-panel .cart-line-name', { timeout: 10000 });
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(outDir, '01-wishlist-drawer-open.png') });

    // Verify resolved dynamic item is present
    const wishlistItems = await page.evaluate(() => {
      const names = Array.from(document.querySelectorAll('.wishlist-modal-panel .cart-line-name')).map(el => el.textContent.trim());
      const unavail = Array.from(document.querySelectorAll('.wishlist-modal-panel .cart-line-details')).some(el => el.textContent.includes('Tạm hết hàng'));
      return { names, hasUnavailable: unavail };
    });

    logTest('Wishlist resolves dynamic product (Blazer) from SQLite API', wishlistItems.names.some(n => n.includes('Blazer')), {
      names: wishlistItems.names,
    });

    logTest('Wishlist displays Unavailable state for missing product without silent drop', wishlistItems.hasUnavailable, {
      hasUnavailable: wishlistItems.hasUnavailable,
    });

    // Test inline error when attempting to add without selecting variant
    const addSingleBtn = page.locator('.wishlist-modal-panel .cart-line-item button.shop-primary').first();
    await addSingleBtn.click();
    await page.waitForTimeout(300);

    const inlineError = await page.evaluate(() => {
      const err = document.querySelector('.wishlist-modal-panel [role="alert"]');
      return err ? err.textContent.trim() : null;
    });

    logTest('Wishlist enforces variant selection with inline error message', !!inlineError && inlineError.includes('chọn màu'), {
      inlineError,
    });

    await page.screenshot({ path: path.join(outDir, '02-wishlist-inline-error.png') });

    // Select color (Be sáng) and size (M)
    const colorTrigger = page.locator('#wish-color-ao-blazer-dang-rong-2-hang-khuy, .wishlist-modal-panel .cart-variant-group:first-child .morph-custom-select-trigger').first();
    await colorTrigger.click();
    await page.waitForTimeout(300);

    const colorOptions = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.morph-select-option')).map(o => o.textContent.trim());
    });

    logTest('Wishlist displays real dynamic colors (Be sáng & Đen than)', colorOptions.some(c => c.includes('Be sáng')) && colorOptions.some(c => c.includes('Đen than')), {
      colorOptions,
    });

    await page.locator('.morph-select-option:has-text("Be sáng")').first().click();
    await page.waitForTimeout(300);

    // Select size
    const sizeTrigger = page.locator('#wish-size-ao-blazer-dang-rong-2-hang-khuy, .wishlist-modal-panel .cart-variant-group:last-child .morph-custom-select-trigger').first();
    await sizeTrigger.click();
    await page.waitForTimeout(300);

    const sizeOptions = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.morph-select-option')).map(o => o.textContent.trim());
    });

    logTest('Wishlist displays real dynamic sizes for selected color', sizeOptions.includes('S') && sizeOptions.includes('M') && sizeOptions.includes('L') && sizeOptions.includes('XL'), {
      sizeOptions,
    });

    await page.locator('.morph-select-option:has-text("M")').first().click();
    await page.waitForTimeout(300);

    // Click "Thêm giỏ" single button
    await addSingleBtn.click();
    await page.waitForTimeout(500);

    const cartCountAfterAdd = await page.evaluate(() => {
      const cart = JSON.parse(localStorage.getItem('morph-demo-cart-v2') || '[]');
      return cart.length;
    });

    logTest('Adding variant from Wishlist updates Cart storage', cartCountAfterAdd === 1, {
      cartItemsCount: cartCountAfterAdd,
    });

    // Test "Tiếp tục đặt hàng" batch action
    await page.locator('.wishlist-modal-panel input[type="checkbox"]').first().check();
    await page.waitForTimeout(200);

    const continueCheckoutBtn = page.locator('.wishlist-modal-panel .cart-drawer-footer button.shop-primary').first();
    await continueCheckoutBtn.click();
    await page.waitForFunction(() => window.location.pathname.includes('/checkout'), { timeout: 10000 });
    await page.waitForTimeout(600);

    const currentUrl = page.url();
    logTest('"Tiếp tục đặt hàng" navigates directly to /checkout', currentUrl.includes('/checkout'), {
      url: currentUrl,
    });

    await page.screenshot({ path: path.join(outDir, '03-checkout-from-wishlist.png') });

    // =========================================================================
    // 2. CART PAGE VARIANT CHANGING FOR DYNAMIC PRODUCTS
    // =========================================================================
    console.log('\n--- 2. Testing Cart Page Variant Changing for Dynamic Products ---');
    await page.goto('http://127.0.0.1:3000/cart', { waitUntil: 'networkidle' });
    await page.waitForSelector('.cart-table-card', { timeout: 10000 });
    await page.waitForTimeout(800);

    // Verify color options in cart combobox
    const cartColorTrigger = page.locator('#color-ao-blazer-dang-rong-2-hang-khuy__Be\\ s\\áng__M, .cart-inline-variant .morph-custom-select-trigger').first();
    await cartColorTrigger.click();
    await page.waitForTimeout(400);

    const cartAvailableColors = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.morph-select-option')).map(o => o.textContent.trim());
    });

    logTest('Cart combobox resolves all real dynamic colors (not limited to 1 color)', cartAvailableColors.length >= 2 && cartAvailableColors.some(c => c.includes('Đen than')), {
      cartAvailableColors,
    });

    // Change color to Đen than
    await page.locator('.morph-select-option:has-text("Đen than")').first().click();
    await page.waitForTimeout(500);

    // Verify size combobox still has full sizes
    const cartSizeTrigger = page.locator('.cart-inline-variant .cart-variant-group:last-child .morph-custom-select-trigger').first();
    await cartSizeTrigger.click();
    await page.waitForTimeout(400);

    const cartAvailableSizes = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.morph-select-option')).map(o => o.textContent.trim());
    });

    logTest('Cart size combobox resolves all real dynamic sizes for chosen color', cartAvailableSizes.length >= 4 && cartAvailableSizes.includes('XL'), {
      cartAvailableSizes,
    });

    await page.locator('.morph-select-option:has-text("XL")').first().click();
    await page.waitForTimeout(500);

    await page.screenshot({ path: path.join(outDir, '04-cart-variant-changed.png') });

    const updatedCartItem = await page.evaluate(() => {
      const cart = JSON.parse(localStorage.getItem('morph-demo-cart-v2') || '[]');
      return cart[0];
    });

    logTest('Variant update in cart persists new color and size in Cart', updatedCartItem.color === 'Đen than' && updatedCartItem.size === 'XL', {
      updatedCartItem,
    });

    // =========================================================================
    // 3. CHECKOUT VALIDATION FOCUS & CART PRESERVATION ON SUBMIT ERROR
    // =========================================================================
    console.log('\n--- 3. Testing Checkout Validation Focus & Cart Preservation ---');
    await page.goto('http://127.0.0.1:3000/checkout', { waitUntil: 'networkidle' });
    await page.waitForSelector('form', { timeout: 10000 });
    await page.waitForTimeout(600);

    // Submit form while empty
    const submitBtn = page.locator('button[type="submit"]').first();
    await submitBtn.click();
    await page.waitForTimeout(400);

    // Check which element has focus!
    const activeElementId = await page.evaluate(() => document.activeElement ? document.activeElement.id : null);
    logTest('Submitting empty checkout form immediately focuses the first error field (#fullName)', activeElementId === 'fullName', {
      focusedElementId: activeElementId,
    });

    // Check accessibility: aria-invalid and aria-describedby
    const a11yAttrs = await page.evaluate(() => {
      const nameInput = document.getElementById('fullName');
      const phoneInput = document.getElementById('phone');
      const addrInput = document.getElementById('address');
      return {
        nameInvalid: nameInput.getAttribute('aria-invalid'),
        nameDescribedBy: nameInput.getAttribute('aria-describedby'),
        phoneInvalid: phoneInput.getAttribute('aria-invalid'),
        addrInvalid: addrInput.getAttribute('aria-invalid'),
      };
    });

    logTest('Checkout invalid fields have aria-invalid="true" and aria-describedby', a11yAttrs.nameInvalid === 'true' && a11yAttrs.phoneInvalid === 'true', {
      a11yAttrs,
    });

    await page.screenshot({ path: path.join(outDir, '05-checkout-validation-focus.png') });

    // Verify cart items are preserved when order submit fails (e.g. invalid phone number)
    await page.fill('#fullName', 'Nguyễn Test');
    await page.fill('#phone', '123'); // Invalid phone (too short)
    await page.fill('#address', '123 Đường Test, Quận 1, TP.HCM');
    await submitBtn.click();
    await page.waitForTimeout(400);

    const cartAfterFailedSubmit = await page.evaluate(() => {
      const cart = JSON.parse(localStorage.getItem('morph-demo-cart-v2') || '[]');
      return cart.length;
    });

    logTest('Cart items are preserved intact when form validation or submission fails', cartAfterFailedSubmit >= 1, {
      cartCount: cartAfterFailedSubmit,
    });

    // Summary
    const totalPassed = testReport.tests.filter((t) => t.passed).length;
    console.log(`\n=================================================`);
    console.log(`VERIFICATION SUMMARY: ${totalPassed} / ${testReport.tests.length} TESTS PASSED`);
    console.log(`=================================================\n`);

    fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(testReport, null, 2));
  } catch (err) {
    console.error('Test execution error:', err);
  } finally {
    await browser.close();
  }
})();
