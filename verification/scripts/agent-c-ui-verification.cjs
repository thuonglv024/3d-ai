const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const outDir = path.join(root, 'output/playwright/agent-c-verification');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== STARTING AGENT C FRONTEND UI & INTERACTION VERIFICATION ===\n');

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
    // 1. PRODUCT CARD VERIFICATION (aspect-ratio 3:4 portrait, hover effect on warm ivory)
    // =========================================================================
    console.log('\n--- 1. Testing ProductCard Aspect Ratio & Hover on Storefront ---');
    await page.goto('http://127.0.0.1:3000/#catalog', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('.product-card', { timeout: 10000 });
    await page.waitForTimeout(1000);

    const cardInfo = await page.evaluate(() => {
      const media = document.querySelector('.product-card .product-card-media');
      const card = media ? media.closest('.product-card') : document.querySelector('.product-card');
      const img = media ? media.querySelector('img') : null;
      if (!card || !media || !img) {
        return { error: 'Card, media or img not found', cardFound: !!card, mediaFound: !!media, imgFound: !!img };
      }
      const rect = media.getBoundingClientRect();
      const cardStyle = window.getComputedStyle(card);
      const mediaStyle = window.getComputedStyle(media);
      const imgStyle = window.getComputedStyle(img);

      return {
        cardBg: cardStyle.backgroundColor,
        cardBorder: cardStyle.borderColor,
        cardRadius: cardStyle.borderRadius,
        mediaWidth: rect.width,
        mediaHeight: rect.height,
        ratio: rect.width / rect.height,
        aspectRatioCss: mediaStyle.aspectRatio,
        objectFit: imgStyle.objectFit,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        imgSrc: img.src,
      };
    });

    const isRatio34 = Math.abs(cardInfo.ratio - 0.75) < 0.03;
    logTest('ProductCard Media Aspect Ratio is 3:4 Portrait', isRatio34, {
      width: cardInfo.mediaWidth,
      height: cardInfo.mediaHeight,
      ratio: cardInfo.ratio.toFixed(3),
      expected: '0.750 (3:4)',
      aspectRatioCss: cardInfo.aspectRatioCss,
      objectFit: cardInfo.objectFit,
    });

    // Test Hover on ProductCard
    const firstCard = page.locator('.product-card').first();
    await firstCard.hover();
    await page.waitForTimeout(400);

    const hoverStyle = await firstCard.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      const img = el.querySelector('.product-card-img');
      const imgCs = img ? window.getComputedStyle(img) : null;
      return {
        transform: cs.transform,
        boxShadow: cs.boxShadow,
        borderColor: cs.borderColor,
        imgTransform: imgCs ? imgCs.transform : '',
      };
    });

    logTest('ProductCard Hover Effect Smooth on Warm Ivory', hoverStyle.borderColor.includes('198, 161, 91') || hoverStyle.boxShadow !== 'none', {
      transform: hoverStyle.transform,
      borderColor: hoverStyle.borderColor,
      boxShadow: hoverStyle.boxShadow,
      imgTransform: hoverStyle.imgTransform,
    });

    await page.screenshot({ path: path.join(outDir, '01-product-card-hover.png') });

    // =========================================================================
    // 2. PRODUCT DETAIL PAGE (PDP) - 3:4 Main Image & Detail Thumbnail Click
    // =========================================================================
    console.log('\n--- 2. Testing ProductDetailPage (PDP) & Detail Thumbnail Switching ---');
    await page.goto('http://127.0.0.1:3000/products/so-mi-oxford-classic', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('.main-detail-img', { timeout: 10000 });
    await page.waitForTimeout(800);

    const pdpImgInfo = await page.evaluate(() => {
      const photo = document.querySelector('.product-photo');
      const img = document.querySelector('.main-detail-img');
      const photoRect = photo.getBoundingClientRect();
      const thumbs = Array.from(document.querySelectorAll('.thumb-btn'));

      return {
        photoWidth: photoRect.width,
        photoHeight: photoRect.height,
        photoRatio: photoRect.width / photoRect.height,
        imgNaturalWidth: img.naturalWidth,
        imgNaturalHeight: img.naturalHeight,
        currentSrc: img.src,
        thumbsCount: thumbs.length,
        thumbLabels: thumbs.map((t) => t.getAttribute('aria-label') || t.title),
      };
    });

    const isPdpRatio34 = Math.abs(pdpImgInfo.photoRatio - 0.75) < 0.03;
    logTest('PDP Main Photo Aspect Ratio is 3:4 Portrait', isPdpRatio34, {
      width: pdpImgInfo.photoWidth,
      height: pdpImgInfo.photoHeight,
      ratio: pdpImgInfo.photoRatio.toFixed(3),
      expected: '0.750 (3:4)',
      naturalDimensions: `${pdpImgInfo.imgNaturalWidth}x${pdpImgInfo.imgNaturalHeight}`,
    });

    logTest('PDP Detail Thumbnail Exists', pdpImgInfo.thumbsCount >= 2 && pdpImgInfo.thumbLabels.some((l) => l.includes('phóng to chi tiết')), {
      thumbsCount: pdpImgInfo.thumbsCount,
      labels: pdpImgInfo.thumbLabels,
    });

    await page.screenshot({ path: path.join(outDir, '02-pdp-main-photo.png') });

    // Click "Ảnh phóng to chi tiết" thumbnail
    const detailThumb = page.locator('.thumb-btn[aria-label="Ảnh phóng to chi tiết"], .thumb-btn:nth-child(2)').first();
    await detailThumb.click();
    await page.waitForTimeout(500);

    const switchedImgInfo = await page.evaluate(() => {
      const img = document.querySelector('.main-detail-img');
      const activeThumb = document.querySelector('.thumb-btn.active');
      return {
        src: img.src,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        activeThumbLabel: activeThumb ? activeThumb.getAttribute('aria-label') : null,
      };
    });

    const isDetailActive = switchedImgInfo.src.includes('-detail.jpg');
    logTest('Clicking Detail Thumbnail Switches Main Image to Detail Photo', isDetailActive, {
      newSrc: switchedImgInfo.src,
      activeThumb: switchedImgInfo.activeThumbLabel,
      naturalWidth: switchedImgInfo.naturalWidth,
      naturalHeight: switchedImgInfo.naturalHeight,
    });

    await page.screenshot({ path: path.join(outDir, '03-pdp-switched-to-detail-image.png') });

    // Click back to main thumbnail
    const mainThumb = page.locator('.thumb-btn:first-child').first();
    await mainThumb.click();
    await page.waitForTimeout(400);

    const revertedSrc = await page.locator('.main-detail-img').getAttribute('src');
    logTest('Clicking Main Thumbnail Switches Back', !revertedSrc.includes('-detail.jpg'), {
      revertedSrc,
    });

    // =========================================================================
    // 3. CUSTOMSELECT IN FITEXPERIENCE ("Khung chụp")
    // =========================================================================
    console.log('\n--- 3. Testing CustomSelect for "Khung chụp" on /scan ---');
    await page.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);

    const framingTrigger = page.locator('#scan-framing, .scan-framing-field .morph-custom-select-trigger').first();
    await framingTrigger.click();
    await page.waitForTimeout(400);

    const menuData = await page.evaluate(() => {
      const menu = document.querySelector('.morph-custom-select-menu[role="listbox"]');
      if (!menu) return null;
      const cs = window.getComputedStyle(menu);
      const options = Array.from(menu.querySelectorAll('.morph-select-option'));
      const selectedOption = menu.querySelector('.morph-select-option.is-selected');
      const hasCheckmark = selectedOption ? !!selectedOption.querySelector('.morph-option-check') : false;

      return {
        visible: true,
        borderRadius: cs.borderRadius,
        borderColor: cs.borderColor,
        backgroundColor: cs.backgroundColor,
        optionsCount: options.length,
        hasCheckmark,
        optionsText: options.map((o) => o.textContent.trim().replace(/\s+/g, ' ')),
      };
    });

    logTest('"Khung chụp" CustomSelect Opens Gold + Ivory Dropdown with 12px Radius & Checkmark', !!menuData && menuData.borderRadius === '12px' && menuData.hasCheckmark, {
      menuData,
    });

    await page.screenshot({ path: path.join(outDir, '04-fitexperience-framing-custom-select.png') });

    // Select "Camera · toàn thân"
    const fullBodyOption = page.locator('.morph-select-option:has-text("Camera · toàn thân")').first();
    await fullBodyOption.click();
    await page.waitForTimeout(300);

    const updatedTriggerText = await framingTrigger.textContent();
    logTest('"Khung chụp" Select Updates Value Smoothly', updatedTriggerText.includes('toàn thân'), {
      updatedTriggerText: updatedTriggerText.trim().replace(/\s+/g, ' '),
    });

    // =========================================================================
    // 4. CUSTOMSELECT IN CART (/cart - Color & Size Variant Selectors)
    // =========================================================================
    console.log('\n--- 4. Testing CustomSelect for Color/Size in /cart ---');
    // Ensure an item is in cart
    await page.goto('http://127.0.0.1:3000/products/so-mi-oxford-classic', { waitUntil: 'networkidle' });
    await page.waitForSelector('.product-sizes button', { timeout: 10000 });
    await page.locator('.product-sizes button').first().click();
    await page.waitForTimeout(300);
    await page.locator('button.add-to-cart-btn').click();
    await page.waitForTimeout(800);

    await page.goto('http://127.0.0.1:3000/cart', { waitUntil: 'networkidle' });
    await page.waitForSelector('.cart-table-card', { timeout: 10000 });
    await page.waitForTimeout(600);

    const cartSelects = await page.evaluate(() => {
      const selects = Array.from(document.querySelectorAll('.cart-variant-select-custom .morph-custom-select-trigger'));
      return {
        count: selects.length,
        texts: selects.map((s) => s.textContent.trim().replace(/\s+/g, ' ')),
      };
    });

    logTest('Cart Displays CustomSelect for Color & Size Variants', cartSelects.count >= 2, {
      customSelectsFound: cartSelects.count,
      values: cartSelects.texts,
    });

    // Click Size CustomSelect in Cart
    const sizeSelectTrigger = page.locator('.cart-variant-select-custom .morph-custom-select-trigger').nth(1);
    await sizeSelectTrigger.click();
    await page.waitForTimeout(400);

    const cartMenuData = await page.evaluate(() => {
      const menu = document.querySelector('.morph-custom-select-menu[role="listbox"]');
      if (!menu) return null;
      const cs = window.getComputedStyle(menu);
      const options = Array.from(menu.querySelectorAll('.morph-select-option'));
      return {
        visible: true,
        borderRadius: cs.borderRadius,
        options: options.map((o) => o.textContent.trim().replace(/\s+/g, ' ')),
      };
    });

    logTest('Cart Size CustomSelect Menu Opens Elegantly', !!cartMenuData && cartMenuData.options.length >= 2, {
      cartMenuData,
    });

    await page.screenshot({ path: path.join(outDir, '05-cart-size-custom-select.png') });

    // Close select
    await page.keyboard.press('Escape');

    // =========================================================================
    // 5. CSS VALIDATION FOR ScanCompareModal & Delete Confirmation Modal
    // =========================================================================
    console.log('\n--- 5. Checking CSS Styles for ScanCompareModal & Delete Confirmation Modal ---');
    const cssContent = fs.readFileSync('D:/MORPH-AI/frontend/app/commerce.css', 'utf8');

    const expectedClasses = [
      '.compare-modal-backdrop',
      '.compare-modal-sheet',
      '.compare-modal-header',
      '.compare-modal-body',
      '.compare-sessions-grid',
      '.compare-metrics-table',
      '.delta-badge',
      '.delta-positive',
      '.delta-negative',
      '.compare-disclaimer-note',
      '.confirm-modal-box',
      '.confirm-icon-danger',
      '.confirm-actions-row',
      '.btn-danger',
    ];

    const missingClasses = expectedClasses.filter((cls) => !cssContent.includes(cls));
    logTest('ScanCompareModal & Delete Confirmation Modals Have Full CSS in commerce.css', missingClasses.length === 0, {
      totalChecked: expectedClasses.length,
      missing: missingClasses,
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
