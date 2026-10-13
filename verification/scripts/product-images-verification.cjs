const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const out = path.join(root, 'output/playwright/product-images-verification');
fs.mkdirSync(out, { recursive: true });

(async () => {
  let browser;
  const testResults = [];

  function record(name, passed, detail = '') {
    testResults.push({ name, passed, detail });
    console.log(`[${passed ? 'PASS' : 'FAIL'}] ${name}${detail ? ' - ' + detail : ''}`);
  }

  try {
    console.log('Launching browser to verify product images...');
    browser = await chromium.launch({
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
      headless: true,
      args: ['--no-sandbox', '--disable-gpu'],
    });

    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
    });
    const page = await context.newPage();

    // 1. Visit Storefront
    console.log('Visiting Storefront http://127.0.0.1:3000/#catalog...');
    await page.goto('http://127.0.0.1:3000/', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('.product-card', { timeout: 10000 });

    // Wait a brief moment for images to load
    await page.waitForTimeout(1500);

    // Scroll through the catalog to trigger lazy loading for all cards
    await page.evaluate(async () => {
      const el = document.getElementById('catalog') || document.querySelector('.storefront-catalog');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
      // Scroll to bottom of catalog
      for (let i = 0; i < 4; i++) {
        window.scrollBy(0, 600);
        await new Promise((r) => setTimeout(r, 200));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(1500);

    // 2. Check all visible product images on Storefront
    const imageStatusList = await page.evaluate(() => {
      const cards = Array.from(document.querySelectorAll('.product-card'));
      return cards.map((card) => {
        const titleEl = card.querySelector('.product-card-title');
        const title = titleEl ? titleEl.textContent.trim() : 'Unknown';
        const img = card.querySelector('.product-card-img');
        if (!img) return { title, hasImg: false, naturalWidth: 0, naturalHeight: 0, src: '' };
        return {
          title,
          hasImg: true,
          naturalWidth: img.naturalWidth,
          naturalHeight: img.naturalHeight,
          src: img.src,
          isLoaded: img.naturalWidth > 0 && img.naturalHeight > 0,
        };
      });
    });

    console.log(`Examined ${imageStatusList.length} product cards.`);
    const brokenImages = imageStatusList.filter((item) => !item.isLoaded);

    record(
      'All Storefront Product Images Loaded Cleanly',
      brokenImages.length === 0,
      brokenImages.length === 0
        ? `${imageStatusList.length}/${imageStatusList.length} images loaded (naturalWidth > 0)`
        : `${brokenImages.length} broken images found: ${brokenImages.map((b) => b.title).join(', ')}`
    );

    // Specifically check the products from user's report
    const targets = [
      'Áo thun In Chữ Tối Giản Studio',
      'Chân Váy Xẻ Tà Đùi Quyến Rũ Slit Skirt',
      'Quần Jeans Đen Rửa Tối Giản Slim',
      'Quần Short Chino Màu Pastel Tươi Sáng',
      'Quần Tây Dáng Lửng Cropped Ankle',
    ];

    for (const target of targets) {
      const found = imageStatusList.find((item) => item.title.includes(target) || target.includes(item.title));
      if (found) {
        record(
          `Target Product Image Loaded: "${target}"`,
          found.isLoaded,
          `Dimensions: ${found.naturalWidth}x${found.naturalHeight}, src: ${found.src.split('/').pop()}`
        );
      }
    }

    // 3. Take screenshot of storefront grid
    await page.screenshot({
      path: path.join(out, '01-storefront-products-grid.png'),
      fullPage: false,
    });
    console.log('Saved 01-storefront-products-grid.png');

    // 4. Test Product Detail Page for "chan-vay-xe-ta-dui-quyen-ru-slit-skirt"
    console.log('Navigating to product detail: chan-vay-xe-ta-dui-quyen-ru-slit-skirt...');
    await page.goto('http://127.0.0.1:3000/products/chan-vay-xe-ta-dui-quyen-ru-slit-skirt', {
      waitUntil: 'networkidle',
      timeout: 30000,
    });
    await page.waitForSelector('.main-detail-img', { timeout: 10000 });
    await page.waitForTimeout(1000);

    const pdpImageStatus = await page.evaluate(() => {
      const main = document.querySelector('.main-detail-img');
      const thumbs = Array.from(document.querySelectorAll('.gallery-thumbnails img'));
      return {
        mainLoaded: main ? main.naturalWidth > 0 && main.naturalHeight > 0 : false,
        mainDimensions: main ? `${main.naturalWidth}x${main.naturalHeight}` : 'none',
        thumbsCount: thumbs.length,
        allThumbsLoaded: thumbs.every((t) => t.naturalWidth > 0 && t.naturalHeight > 0),
      };
    });

    record(
      'PDP Main Product Image Loaded',
      pdpImageStatus.mainLoaded,
      `Dimensions: ${pdpImageStatus.mainDimensions}`
    );

    record(
      'PDP Gallery Thumbnails Loaded',
      pdpImageStatus.allThumbsLoaded,
      `${pdpImageStatus.thumbsCount} thumbnails loaded`
    );

    await page.screenshot({
      path: path.join(out, '02-product-detail-images.png'),
    });
    console.log('Saved 02-product-detail-images.png');

    // 5. Test Mobile viewport
    console.log('Testing mobile viewport 390x844...');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://127.0.0.1:3000/#catalog', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: path.join(out, '03-mobile-storefront-images.png'),
    });
    console.log('Saved 03-mobile-storefront-images.png');

    const totalPassed = testResults.filter((t) => t.passed).length;
    console.log(`\nVerification complete: ${totalPassed}/${testResults.length} PASSED.`);

    fs.writeFileSync(
      path.join(out, 'results.json'),
      JSON.stringify({ passedCount: totalPassed, totalCount: testResults.length, testResults }, null, 2)
    );
  } catch (err) {
    console.error('Test error:', err);
  } finally {
    if (browser) await browser.close();
  }
})();
