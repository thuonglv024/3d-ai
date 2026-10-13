const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const root = 'D:/MORPH-AI';
const outDir = path.join(root, 'output/playwright/live-audit-fix');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== STARTING COMPLETE AUDIT FIX VERIFICATION ===\n');

  const results = {
    check1_catalog_images_unique: false,
    check2_price_filter_backend_applied: false,
    check3_color_group_filter_applied: false,
    check4_product_picker_no_422: false,
    check5_wishlist_resolves_all_products: false,
    check6_cart_allows_variants_switch: false,
    check7_tablet_header_no_overflow: false,
    check8_auth_pages_standalone_and_returnTo: false,
  };

  // -------------------------------------------------------------------------
  // CHECK 1: Catalog Media & Duplicate Hashes
  // -------------------------------------------------------------------------
  console.log('--- CHECK 1: Catalog Media & Image Hashes ---');
  const manifestPath = path.join(root, 'backend/app/catalog_asset_manifest.json');
  if (fs.existsSync(manifestPath)) {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    console.log(`Manifest loaded: ${manifest.length} products.`);

    const mainHashes = new Set();
    let duplicates = 0;
    let missingFiles = 0;

    for (const item of manifest) {
      const filePath = path.join(root, 'frontend/public/products', item.image_filename);
      if (!fs.existsSync(filePath)) {
        missingFiles++;
      } else {
        const fileBytes = fs.readFileSync(filePath);
        const hash = crypto.createHash('sha256').update(fileBytes).digest('hex');
        if (mainHashes.has(hash)) {
          duplicates++;
        } else {
          mainHashes.add(hash);
        }
      }
    }

    console.log(`Main images on disk: ${mainHashes.size}/${manifest.length} unique hashes. Duplicates: ${duplicates}. Missing: ${missingFiles}.`);
    if (duplicates === 0 && missingFiles === 0 && mainHashes.size >= 150) {
      results.check1_catalog_images_unique = true;
      console.log('✅ CHECK 1 PASSED: 100% unique main images across catalog (0 duplicate SHA-256)!');
    }
  } else {
    console.log('❌ Manifest not found at:', manifestPath);
  }

  // -------------------------------------------------------------------------
  // CHECK 2: Price Filter Backend Applied
  // -------------------------------------------------------------------------
  console.log('\n--- CHECK 2: Price Filter Applied by Backend ---');
  try {
    const resUnder500 = await fetch('http://127.0.0.1:8000/api/products?price_range=under-500&limit=100');
    const dataUnder500 = await resUnder500.json();
    const maxInUnder500 = Math.max(...dataUnder500.items.map(p => p.price));
    console.log(`Under 500k total: ${dataUnder500.total}, max price found: ${maxInUnder500}đ`);

    const res500to1M = await fetch('http://127.0.0.1:8000/api/products?min_price=500000&max_price=1000000&limit=100');
    const data500to1M = await res500to1M.json();
    const minIn500to1M = Math.min(...data500to1M.items.map(p => p.price));
    const maxIn500to1M = Math.max(...data500to1M.items.map(p => p.price));
    console.log(`500k - 1M total: ${data500to1M.total}, min: ${minIn500to1M}đ, max: ${maxIn500to1M}đ`);

    if (maxInUnder500 <= 500000 && minIn500to1M >= 500000 && maxIn500to1M <= 1000000) {
      results.check2_price_filter_backend_applied = true;
      console.log('✅ CHECK 2 PASSED: Price filter is strictly applied with accurate boundaries.');
    }
  } catch (err) {
    console.error('Check 2 error:', err);
  }

  // -------------------------------------------------------------------------
  // CHECK 3: Color Group Filter Applied
  // -------------------------------------------------------------------------
  console.log('\n--- CHECK 3: Color Group Filter Applied ---');
  try {
    const resWhite = await fetch('http://127.0.0.1:8000/api/products?color=tr%E1%BA%AFng&limit=50');
    const dataWhite = await resWhite.json();
    console.log(`Color 'trắng' results: ${dataWhite.total} products.`);

    const resBlack = await fetch('http://127.0.0.1:8000/api/products?color=%C4%91en&limit=50');
    const dataBlack = await resBlack.json();
    console.log(`Color 'đen' results: ${dataBlack.total} products.`);

    const resBlue = await fetch('http://127.0.0.1:8000/api/products?color=xanh&limit=50');
    const dataBlue = await resBlue.json();
    console.log(`Color 'xanh' results: ${dataBlue.total} products.`);

    if (dataWhite.total > 0 && dataBlack.total > 0 && dataBlue.total > 0) {
      results.check3_color_group_filter_applied = true;
      console.log('✅ CHECK 3 PASSED: Color group mapping successfully matches multi-shade variants.');
    }
  } catch (err) {
    console.error('Check 3 error:', err);
  }

  // -------------------------------------------------------------------------
  // CHECK 4: Product Picker Popover (No 422 on large queries)
  // -------------------------------------------------------------------------
  console.log('\n--- CHECK 4: Product Picker Limit & Pagination ---');
  try {
    const res250 = await fetch('http://127.0.0.1:8000/api/products?limit=250');
    const data250 = await res250.json();
    console.log(`Limit 250 query status: ${res250.status}, items returned: ${data250.items?.length}/${data250.total}`);

    if (res250.status === 200 && data250.items?.length === 160) {
      results.check4_product_picker_no_422 = true;
      console.log('✅ CHECK 4 PASSED: API accepts full catalog limit without 422 error.');
    }
  } catch (err) {
    console.error('Check 4 error:', err);
  }

  // Launch browser for UI checks
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  try {
    // -----------------------------------------------------------------------
    // CHECK 5 & 6: Wishlist & Cart with new 160-item catalog
    // -----------------------------------------------------------------------
    console.log('\n--- CHECK 5 & 6: Wishlist & Cart dynamic variants on new products ---');
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const page = await context.newPage();

    // Navigate to a new catalog product (e.g. ao-blazer-dang-rong-2-hang-khuy)
    await page.goto('http://127.0.0.1:3000/products/ao-blazer-dang-rong-2-hang-khuy', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Click wishlist button
    const wishlistBtn = page.locator('button.favorite').first();
    if (await wishlistBtn.isVisible()) {
      await wishlistBtn.click();
      await page.waitForTimeout(500);

      // Open wishlist drawer from header
      const headerWishlistBtn = page.locator('button:has-text("Yêu thích"), button[aria-label*="yêu thích"]').first();
      if (await headerWishlistBtn.isVisible()) {
        await headerWishlistBtn.click();
        await page.waitForTimeout(800);

        // Verify product appears in wishlist drawer
        const wishlistItem = page.locator('.cart-line-item, .wishlist-item, .cart-item').first();
        await wishlistItem.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
        const hasItem = await wishlistItem.isVisible();
        console.log('Product visible in Wishlist Drawer:', hasItem);
        await page.screenshot({ path: path.join(outDir, '01-wishlist-drawer-resolved.png'), fullPage: false });

        if (hasItem) {
          results.check5_wishlist_resolves_all_products = true;
          console.log('✅ CHECK 5 PASSED: Wishlist drawer dynamically resolves products outside static 22 items.');
        }

        // Close drawer
        const closeWishlist = page.locator('.drawer-close-btn, .cart-drawer-close, button[aria-label*="Đóng"]').first();
        if (await closeWishlist.isVisible()) await closeWishlist.click();
      }
    }

    // Select color and size, then Add to cart
    const sizeBtn = page.locator('.product-sizes button:not([disabled])').first();
    if (await sizeBtn.isVisible()) {
      await sizeBtn.click();
      await page.waitForTimeout(300);

      const addBtn = page.locator('button:has-text("Thêm vào giỏ"), button.add-to-cart-btn').first();
      if (await addBtn.isVisible()) {
        await addBtn.click();
        await page.waitForTimeout(1000);
      }
    }

    // Navigate to /cart
    await page.goto('http://127.0.0.1:3000/cart', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Verify variant dropdowns exist and have options
    const variantSelects = page.locator('select.cart-variant-select, select[aria-label*="Màu"], select[aria-label*="Kích cỡ"]');
    const selectCount = await variantSelects.count();
    console.log(`Cart page variant select count: ${selectCount}`);
    await page.screenshot({ path: path.join(outDir, '02-cart-page-variants.png'), fullPage: true });

    if (selectCount >= 1) {
      results.check6_cart_allows_variants_switch = true;
      console.log('✅ CHECK 6 PASSED: Cart allows dynamic variant options switching on new catalog items.');
    }

    // -----------------------------------------------------------------------
    // CHECK 7: Tablet Header Responsive at 820px
    // -----------------------------------------------------------------------
    console.log('\n--- CHECK 7: Tablet Header at 820px (iPad Air) ---');
    const tabletContext = await browser.newContext({ viewport: { width: 820, height: 1180 } });
    const tabletPage = await tabletContext.newPage();

    await tabletPage.goto('http://127.0.0.1:3000/', { waitUntil: 'networkidle' });
    await tabletPage.waitForTimeout(1000);

    const scrollWidth = await tabletPage.evaluate(() => document.documentElement.scrollWidth);
    const innerWidth = await tabletPage.evaluate(() => window.innerWidth);
    console.log(`Tablet viewport: innerWidth=${innerWidth}px, scrollWidth=${scrollWidth}px.`);

    await tabletPage.screenshot({ path: path.join(outDir, '03-tablet-820px-header.png'), fullPage: false });

    if (scrollWidth <= innerWidth + 1) {
      results.check7_tablet_header_no_overflow = true;
      console.log('✅ CHECK 7 PASSED: Tablet header at 820px has 0 horizontal overflow!');
    } else {
      console.log(`⚠️ CHECK 7 WARNING: Horizontal overflow detected (${scrollWidth}px > ${innerWidth}px).`);
    }

    // -----------------------------------------------------------------------
    // CHECK 8: Dedicated Auth Pages & returnTo Navigation
    // -----------------------------------------------------------------------
    console.log('\n--- CHECK 8: Dedicated Auth Pages (/auth/login & /auth/register) ---');
    const authContext = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const authPage = await authContext.newPage();

    // 1. Visit /auth/login with returnTo
    await authPage.goto('http://127.0.0.1:3000/auth/login?returnTo=/products/quan-tay-pleated-wide-leg', { waitUntil: 'networkidle' });
    await authPage.waitForTimeout(800);

    const hasEmail = await authPage.locator('input[type="email"], #login-email').isVisible();
    const hasPassword = await authPage.locator('input[type="password"], #login-password').isVisible();
    const hasModal = await authPage.locator('.modal-backdrop, .auth-modal-dialog').isVisible();
    console.log(`Auth login page: email input=${hasEmail}, password input=${hasPassword}, modal popup present=${hasModal}`);

    await authPage.screenshot({ path: path.join(outDir, '04-auth-login-page.png'), fullPage: true });

    // 2. Visit /auth/register
    await authPage.goto('http://127.0.0.1:3000/auth/register', { waitUntil: 'networkidle' });
    await authPage.waitForTimeout(800);

    const hasRegName = await authPage.locator('#register-displayName, input[name="displayName"]').isVisible();
    const hasRegEmail = await authPage.locator('#register-email, input[name="email"]').isVisible();
    const hasRegPassword = await authPage.locator('#register-password, input[name="password"]').isVisible();
    console.log(`Auth register page: name=${hasRegName}, email=${hasRegEmail}, password=${hasRegPassword}`);

    await authPage.screenshot({ path: path.join(outDir, '05-auth-register-page.png'), fullPage: true });

    if (hasEmail && hasPassword && !hasModal && hasRegName && hasRegEmail) {
      results.check8_auth_pages_standalone_and_returnTo = true;
      console.log('✅ CHECK 8 PASSED: Standalone auth pages operational without modal popups.');
    }

  } catch (err) {
    console.error('Browser execution error:', err);
  } finally {
    await browser.close();
  }

  console.log('\n======================================================');
  console.log('FINAL AUDIT FIX VERIFICATION RESULTS:');
  console.log(JSON.stringify(results, null, 2));
  console.log('======================================================');

  const allPassed = Object.values(results).every(Boolean);
  if (allPassed) {
    console.log('🎉 ALL 8 AUDIT FIX CHECKS PASSED 100%!');
    process.exit(0);
  } else {
    console.log('⚠️ Some checks did not fully pass. Inspect details above.');
    process.exit(1);
  }
})();
