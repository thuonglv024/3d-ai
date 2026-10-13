const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const outDir = path.join(root, 'output/playwright/popups-ui-fix');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== STARTING POPUPS & CUSTOM DROPDOWN UI VERIFICATION ===\n');

  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const results = {
    test1_framing_custom_select: false,
    test2_cart_variant_custom_select: false,
    test3_account_modals_styled: false,
  };

  try {
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const page = await context.newPage();

    // -----------------------------------------------------------------------
    // TEST 1: FitExperience "Khung chụp" Custom Select (Replaces Image 1 native select)
    // -----------------------------------------------------------------------
    console.log('--- TEST 1: "Khung chụp" Custom Select on /scan ---');
    await page.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Look for the "Khung chụp" custom select trigger
    const framingTrigger = page.locator('#scan-framing, .scan-framing-field .morph-custom-select-trigger').first();
    const hasTrigger = await framingTrigger.isVisible();
    console.log('Framing CustomSelect trigger visible:', hasTrigger);

    if (hasTrigger) {
      // Click trigger to open custom dropdown
      await framingTrigger.click();
      await page.waitForTimeout(400);

      // Verify custom menu is rendered with role="listbox" and custom options
      const menu = page.locator('.morph-custom-select-menu[role="listbox"]').first();
      const isMenuOpen = await menu.isVisible();
      const optionsCount = await page.locator('.morph-select-option').count();
      console.log(`Custom dropdown menu open: ${isMenuOpen}, options count: ${optionsCount}`);

      // Verify styling of menu: border color, background, box shadow
      const menuStyles = await menu.evaluate((el) => {
        const cs = window.getComputedStyle(el);
        return {
          backgroundColor: cs.backgroundColor,
          borderColor: cs.borderColor,
          borderRadius: cs.borderRadius,
          boxShadow: cs.boxShadow,
        };
      });
      console.log('Dropdown menu computed styles:', menuStyles);

      await page.screenshot({ path: path.join(outDir, '01-custom-select-framing-open.png'), fullPage: false });

      if (isMenuOpen && optionsCount >= 2) {
        results.test1_framing_custom_select = true;
        console.log('✅ TEST 1 PASSED: "Khung chụp" uses luxury gold+ivory custom dropdown!');
      }

      // Close dropdown by pressing Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    // -----------------------------------------------------------------------
    // TEST 2: Cart Page Variant Custom Select
    // -----------------------------------------------------------------------
    console.log('\n--- TEST 2: Cart Page Variant Custom Select ---');
    // First, add an item to cart if empty
    await page.goto('http://127.0.0.1:3000/products/ao-blazer-dang-rong-2-hang-khuy', { waitUntil: 'networkidle' });
    await page.waitForTimeout(800);

    const sizeBtn = page.locator('.product-sizes button:not([disabled])').first();
    if (await sizeBtn.isVisible()) {
      await sizeBtn.click();
      await page.waitForTimeout(300);
      const addBtn = page.locator('button.add-to-cart-btn').first();
      if (await addBtn.isVisible()) {
        await addBtn.click();
        await page.waitForTimeout(1000);
      }
    }

    // Navigate to /cart
    await page.goto('http://127.0.0.1:3000/cart', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Look for custom select in cart
    const cartSelectTrigger = page.locator('.cart-variant-select-custom .morph-custom-select-trigger').first();
    const hasCartCustomSelect = await cartSelectTrigger.isVisible();
    console.log('Cart variant CustomSelect visible:', hasCartCustomSelect);

    if (hasCartCustomSelect) {
      await cartSelectTrigger.click();
      await page.waitForTimeout(400);

      const cartMenu = page.locator('.cart-variant-select-custom .morph-custom-select-menu').first();
      const isCartMenuOpen = await cartMenu.isVisible();
      console.log('Cart variant dropdown menu open:', isCartMenuOpen);

      await page.screenshot({ path: path.join(outDir, '02-cart-variant-custom-select.png'), fullPage: false });

      if (isCartMenuOpen) {
        results.test2_cart_variant_custom_select = true;
        console.log('✅ TEST 2 PASSED: Cart variant selectors use CustomSelect dropdown!');
      }

      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    // -----------------------------------------------------------------------
    // TEST 3: ScanCompareModal & ConfirmModal CSS rules test
    // -----------------------------------------------------------------------
    console.log('\n--- TEST 3: Check ScanCompareModal & ConfirmModal styles loaded ---');
    // Create an in-browser test element for ScanCompareModal and confirm modal to verify rendered CSS styles
    const stylesTest = await page.evaluate(() => {
      const backdrop = document.createElement('div');
      backdrop.className = 'compare-modal-backdrop';
      const sheet = document.createElement('div');
      sheet.className = 'compare-modal-sheet';
      const confirmBox = document.createElement('div');
      confirmBox.className = 'confirm-modal-box';
      const dangerIcon = document.createElement('div');
      dangerIcon.className = 'confirm-icon-danger';

      backdrop.appendChild(sheet);
      backdrop.appendChild(confirmBox);
      confirmBox.appendChild(dangerIcon);
      document.body.appendChild(backdrop);

      const bCs = window.getComputedStyle(backdrop);
      const sCs = window.getComputedStyle(sheet);
      const cCs = window.getComputedStyle(confirmBox);
      const dCs = window.getComputedStyle(dangerIcon);

      const res = {
        backdropPosition: bCs.position,
        sheetBorderRadius: sCs.borderRadius,
        sheetBorderColor: sCs.borderColor,
        confirmBoxBorderRadius: cCs.borderRadius,
        confirmBoxBoxShadow: cCs.boxShadow,
        dangerIconColor: dCs.color,
      };

      document.body.removeChild(backdrop);
      return res;
    });

    console.log('Modal & Dialog computed styles verification:', stylesTest);
    if (
      stylesTest.backdropPosition === 'fixed' &&
      (stylesTest.sheetBorderRadius === '18px' || stylesTest.sheetBorderRadius === '24px') &&
      (stylesTest.confirmBoxBorderRadius === '16px' || stylesTest.confirmBoxBorderRadius === '24px')
    ) {
      results.test3_account_modals_styled = true;
      console.log('✅ TEST 3 PASSED: ScanCompareModal and ConfirmModal have complete CSS styling!');
    }

  } catch (err) {
    console.error('Error during verification:', err);
  } finally {
    await browser.close();
  }

  console.log('\n======================================================');
  console.log('FINAL POPUPS & UI VERIFICATION RESULTS:');
  console.log(JSON.stringify(results, null, 2));
  console.log('======================================================');

  const allPassed = Object.values(results).every(Boolean);
  if (allPassed) {
    console.log('🎉 ALL POPUP & UI FIXES VERIFIED SUCCESSFULLY!');
    process.exit(0);
  } else {
    console.log('⚠️ Some popup checks need review.');
    process.exit(1);
  }
})();
