const { chromium } = require('./playwright-runtime.cjs');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const outDir = path.join(root, 'output/playwright/wishlist-escape-cart');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== WISHLIST ESCAPE & CART QUANTITY SYNC VERIFICATION ===\n');

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

    // Seed localStorage with a wishlist item and an empty cart
    await page.goto('http://127.0.0.1:3000', { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      localStorage.setItem(
        'morph-demo-wishlist-v1',
        JSON.stringify(['ao-blazer-dang-rong-2-hang-khuy'])
      );
      localStorage.setItem('morph-demo-cart-v2', JSON.stringify([]));
    });

    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(600);

    // =========================================================================
    // TEST 1 & 2: ESCAPE KEY ISOLATION IN WISHLIST CUSTOM SELECT vs DRAWER
    // =========================================================================
    console.log('\n--- 1. Testing Escape Key on CustomSelect inside WishlistDrawer ---');

    const wishlistHeaderBtn = page.locator('button[aria-label*="yêu thích"]').first();
    await wishlistHeaderBtn.click();
    await page.waitForSelector('.wishlist-modal-panel', { timeout: 10000 });
    await page.waitForSelector('.wishlist-modal-panel .cart-line-name', { timeout: 10000 });
    await page.waitForTimeout(300);

    // Open color dropdown inside WishlistDrawer
    const colorTrigger = page
      .locator('#wish-color-ao-blazer-dang-rong-2-hang-khuy, .wishlist-modal-panel .morph-custom-select-trigger')
      .first();
    await colorTrigger.click();
    await page.waitForTimeout(250);

    const stateWhenOpen = await page.evaluate(() => {
      const drawer = document.querySelector('.wishlist-modal-panel');
      const openTrigger = document.querySelector('.wishlist-modal-panel .morph-custom-select-trigger.is-open');
      const openMenu = document.querySelector('.wishlist-modal-panel .morph-custom-select-menu');
      return {
        drawerOpen: !!drawer,
        dropdownTriggerOpen: !!openTrigger,
        dropdownMenuVisible: !!openMenu,
      };
    });

    logTest(
      'Color dropdown opens inside WishlistDrawer',
      stateWhenOpen.drawerOpen && stateWhenOpen.dropdownTriggerOpen && stateWhenOpen.dropdownMenuVisible,
      stateWhenOpen
    );

    await page.screenshot({ path: path.join(outDir, '01-wishlist-color-dropdown-open.png') });

    // Press Escape ONCE -> Dropdown must close, WishlistDrawer must stay OPEN
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    const stateAfterFirstEscape = await page.evaluate(() => {
      const drawer = document.querySelector('.wishlist-modal-panel');
      const openTrigger = document.querySelector('.wishlist-modal-panel .morph-custom-select-trigger.is-open');
      const openMenu = document.querySelector('.wishlist-modal-panel .morph-custom-select-menu');
      const activeId = document.activeElement ? document.activeElement.id : null;
      return {
        drawerOpen: !!drawer,
        dropdownTriggerOpen: !!openTrigger,
        dropdownMenuVisible: !!openMenu,
        activeId,
      };
    });

    logTest(
      'First Escape closes Color Dropdown ONLY while keeping WishlistDrawer open',
      stateAfterFirstEscape.drawerOpen === true &&
        stateAfterFirstEscape.dropdownTriggerOpen === false &&
        stateAfterFirstEscape.dropdownMenuVisible === false,
      stateAfterFirstEscape
    );

    await page.screenshot({ path: path.join(outDir, '02-after-first-escape-drawer-still-open.png') });

    // Press Escape a SECOND time -> WishlistDrawer must close
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    const stateAfterSecondEscape = await page.evaluate(() => {
      const drawer = document.querySelector('.wishlist-modal-panel');
      return {
        drawerOpen: !!drawer,
      };
    });

    logTest(
      'Second Escape (when dropdown is closed) closes WishlistDrawer normally',
      stateAfterSecondEscape.drawerOpen === false,
      stateAfterSecondEscape
    );

    await page.screenshot({ path: path.join(outDir, '03-after-second-escape-drawer-closed.png') });

    // =========================================================================
    // TEST 3: ADD TO CART THEN CONTINUE TO CHECKOUT DOES NOT DOUBLE QUANTITY
    // =========================================================================
    console.log('\n--- 2. Testing Wishlist Add-to-Cart + Continue-to-Checkout Quantity Sync ---');

    // Reopen WishlistDrawer
    await wishlistHeaderBtn.click();
    await page.waitForSelector('.wishlist-modal-panel', { timeout: 10000 });
    await page.waitForSelector('.wishlist-modal-panel .cart-line-name', { timeout: 10000 });
    await page.waitForTimeout(300);

    // Select color "Be sáng"
    const colorTrigger2 = page
      .locator('#wish-color-ao-blazer-dang-rong-2-hang-khuy, .wishlist-modal-panel .morph-custom-select-trigger')
      .first();
    await colorTrigger2.click();
    await page.waitForTimeout(200);
    await page.locator('.morph-select-option:has-text("Be sáng")').first().click();
    await page.waitForTimeout(200);

    // Select size "M"
    const sizeTrigger = page
      .locator('#wish-size-ao-blazer-dang-rong-2-hang-khuy')
      .first();
    await sizeTrigger.click();
    await page.waitForTimeout(200);
    await page.locator('.morph-select-option:has-text("M")').first().click();
    await page.waitForTimeout(200);

    // Step A: Click single "Thêm giỏ" button (quantity = 1)
    const addSingleBtn = page.locator('.wishlist-modal-panel .cart-line-item button.shop-primary').first();
    await addSingleBtn.click();
    await page.waitForTimeout(300);

    const cartAfterSingleAdd = await page.evaluate(() => {
      return JSON.parse(localStorage.getItem('morph-demo-cart-v2') || '[]');
    });

    logTest(
      'After clicking single "Thêm giỏ" (qty=1), cart has 1 item with quantity=1',
      cartAfterSingleAdd.length === 1 && cartAfterSingleAdd[0].quantity === 1,
      { cartAfterSingleAdd }
    );

    // Step B: Also click batch "Thêm vào giỏ hàng" button (quantity still = 1)
    const batchAddBtn = page.locator('.wishlist-modal-panel .cart-drawer-footer button.shop-secondary').first();
    await batchAddBtn.click();
    await page.waitForTimeout(300);

    const cartAfterBatchAdd = await page.evaluate(() => {
      return JSON.parse(localStorage.getItem('morph-demo-cart-v2') || '[]');
    });

    logTest(
      'After clicking batch "Thêm vào giỏ hàng" (qty=1), cart quantity remains 1 (not 2)',
      cartAfterBatchAdd.length === 1 && cartAfterBatchAdd[0].quantity === 1,
      { cartAfterBatchAdd }
    );

    // Step C: Click "Tiếp tục đặt hàng" -> navigates to /checkout, quantity must still be 1!
    const continueCheckoutBtn = page.locator('.wishlist-modal-panel .cart-drawer-footer button.shop-primary').first();
    await continueCheckoutBtn.click();
    await page.waitForFunction(() => window.location.pathname.includes('/checkout'), { timeout: 10000 });
    await page.waitForTimeout(500);

    const cartAtCheckout = await page.evaluate(() => {
      return JSON.parse(localStorage.getItem('morph-demo-cart-v2') || '[]');
    });

    logTest(
      'After clicking "Tiếp tục đặt hàng", cart quantity in /checkout is exactly 1 (never doubled to 2)',
      cartAtCheckout.length === 1 && cartAtCheckout[0].quantity === 1,
      { cartAtCheckout }
    );

    await page.screenshot({ path: path.join(outDir, '04-checkout-quantity-exact-1.png') });

    // =========================================================================
    // TEST 4: QUANTITY UPDATE SYNC WHEN USER CHANGES QUANTITY BEFORE CHECKOUT
    // =========================================================================
    console.log('\n--- 3. Testing Quantity Update Sync in Wishlist (Add qty=1, change to qty=3, Continue) ---');

    await page.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
    await page.evaluate(() => {
      localStorage.setItem('morph-demo-cart-v2', JSON.stringify([]));
    });
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(400);

    await wishlistHeaderBtn.click();
    await page.waitForSelector('.wishlist-modal-panel .cart-line-name', { timeout: 10000 });
    await page.waitForTimeout(300);

    // Select color "Be sáng" and size "M"
    await page.locator('#wish-color-ao-blazer-dang-rong-2-hang-khuy').first().click();
    await page.waitForTimeout(200);
    await page.locator('.morph-select-option:has-text("Be sáng")').first().click();
    await page.waitForTimeout(200);

    await page.locator('#wish-size-ao-blazer-dang-rong-2-hang-khuy').first().click();
    await page.waitForTimeout(200);
    await page.locator('.morph-select-option:has-text("M")').first().click();
    await page.waitForTimeout(200);

    // Click "Thêm vào giỏ hàng" with qty = 1
    await page.locator('.wishlist-modal-panel .cart-drawer-footer button.shop-secondary').first().click();
    await page.waitForTimeout(300);

    // Increase quantity to 3 (+ twice)
    const plusBtn = page.locator('.wishlist-modal-panel button[aria-label*="Tăng số lượng"]').first();
    await plusBtn.click();
    await plusBtn.click();
    await page.waitForTimeout(200);

    // Click "Tiếp tục đặt hàng"
    await page.locator('.wishlist-modal-panel .cart-drawer-footer button.shop-primary').first().click();
    await page.waitForFunction(() => window.location.pathname.includes('/checkout'), { timeout: 10000 });
    await page.waitForTimeout(400);

    const cartAfterQtyChange = await page.evaluate(() => {
      return JSON.parse(localStorage.getItem('morph-demo-cart-v2') || '[]');
    });

    logTest(
      'Changing Wishlist quantity to 3 after adding qty=1 syncs cart quantity to 3 (not 1+3=4)',
      cartAfterQtyChange.length === 1 && cartAfterQtyChange[0].quantity === 3,
      { cartAfterQtyChange }
    );

    fs.writeFileSync(path.join(outDir, 'results.json'), JSON.stringify(testReport, null, 2));
  } catch (err) {
    console.error('Error during verification:', err);
    process.exit(1);
  } finally {
    await browser.close();
  }

  const allPassed = testReport.tests.length > 0 && testReport.tests.every((t) => t.passed);
  console.log('\n======================================================');
  console.log(`SUMMARY: ${testReport.tests.filter((t) => t.passed).length}/${testReport.tests.length} TESTS PASSED`);
  console.log('======================================================');

  if (!allPassed) {
    process.exit(1);
  }
})();
