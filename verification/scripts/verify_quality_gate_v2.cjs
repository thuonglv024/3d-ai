const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const QUALITY_GATE_SLUGS = [
  'ao-blazer-dang-rong-2-hang-khuy',
  'ao-choang-len-det-poncho-phong-khoang',
  'ao-khoac-varsity-bong-chay-phoi-da',
  'so-mi-oxford-classic',
  'so-mi-co-tru-minimal',
  'so-mi-cuban-collar',
  'ao-thun-essential',
  'ao-thun-oversized-heavyweight',
  'ao-thun-striped-relaxed',
  'quan-tay-pleated-wide-leg',
  'quan-khaki-chino-straight',
  'quan-linen-cap-chun',
  'chan-vay-pleated-midi',
  'chan-vay-chu-a-linen',
  'dam-suong-linen-minimal'
];

async function runQualityGate() {
  console.log('=== STARTING QUALITY GATE E2E BROWSER AUDIT ===');
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const page = await context.newPage();

  const report = [];

  for (const slug of QUALITY_GATE_SLUGS) {
    const url = `http://127.0.0.1:3000/products/${slug}`;
    console.log(`\nNavigating to ${url}...`);
    try {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(1000);

      // Inspect main PDP image
      const imgInfo = await page.evaluate(() => {
        // Find main image
        const img = document.querySelector('img[src*="/products/v2/"]') || document.querySelector('.product-gallery img') || document.querySelector('main img');
        if (!img) return { found: false };
        return {
          found: true,
          src: img.src,
          currentSrc: img.currentSrc,
          naturalWidth: img.naturalWidth,
          naturalHeight: img.naturalHeight,
          complete: img.complete
        };
      });

      const title = await page.title();
      console.log(`  Title: ${title}`);
      console.log(`  Image Found: ${imgInfo.found}`);
      console.log(`  Image Src: ${imgInfo.src}`);
      console.log(`  Dimensions: ${imgInfo.naturalWidth} x ${imgInfo.naturalHeight}`);

      const pass = imgInfo.found && imgInfo.src.includes('/products/v2/') && imgInfo.naturalWidth >= 600 && imgInfo.naturalHeight >= 800;
      report.push({
        slug,
        title,
        imgSrc: imgInfo.src,
        dimensions: `${imgInfo.naturalWidth}x${imgInfo.naturalHeight}`,
        pass
      });

      // Capture screenshot for visual review
      const outDir = path.join(__dirname, '..', 'quality_gate_screenshots');
      if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
      await page.screenshot({ path: path.join(outDir, `${slug}.png`), fullPage: false });

    } catch (err) {
      console.error(`  ERROR inspecting ${slug}:`, err.message);
      report.push({ slug, error: err.message, pass: false });
    }
  }

  // Also check Storefront grid
  console.log('\nNavigating to Storefront http://127.0.0.1:3000...');
  await page.goto('http://127.0.0.1:3000', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);

  const storefrontV2Count = await page.evaluate(() => {
    const imgs = Array.from(document.querySelectorAll('img'));
    return imgs.filter(img => img.src.includes('/products/v2/')).length;
  });
  console.log(`Storefront currently displaying ${storefrontV2Count} v2 product images in grid.`);

  await browser.close();

  console.log('\n=== QUALITY GATE SUMMARY ===');
  let allPass = true;
  for (const r of report) {
    const status = r.pass ? 'PASS [OK]' : 'FAIL [X]';
    console.log(`${status} - ${r.slug}: ${r.dimensions} | ${r.imgSrc}`);
    if (!r.pass) allPass = false;
  }

  console.log(`\nOVERALL QUALITY GATE RESULT: ${allPass ? 'PASSED (15/15)' : 'FAILED'}`);
  return allPass;
}

runQualityGate().catch(console.error);
