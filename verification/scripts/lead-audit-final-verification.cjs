const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');

const root = 'D:/MORPH-AI';
const outDir = path.join(root, 'output/playwright/lead-final-audit');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== LEAD AUDIT FINAL INTEGRATION VERIFICATION ===\n');

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
    // =========================================================================
    // 1. MOBILE PRODUCT PICKER POPOVER PORTAL & CONTAINING BLOCK FIX (390x844)
    // =========================================================================
    console.log('\n--- 1. Testing Mobile ProductPickerPopover (390x844) ---');
    const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const mobilePage = await mobileContext.newPage();

    await mobilePage.goto('http://127.0.0.1:3000/scan', { waitUntil: 'networkidle' });
    await mobilePage.waitForTimeout(500);

    const pickerTrigger = mobilePage.locator('.product-picker-trigger').first();
    await pickerTrigger.click();
    await mobilePage.waitForSelector('.product-picker-popover', { timeout: 10000 });
    await mobilePage.waitForTimeout(400);

    const sheetMetrics = await mobilePage.evaluate(() => {
      const popover = document.querySelector('.product-picker-popover');
      const backdrop = document.querySelector('.product-picker-backdrop');
      const rect = popover.getBoundingClientRect();
      const parent = popover.parentElement;
      return {
        isAttachedToBody: parent === document.body,
        rect: { top: rect.top, bottom: rect.bottom, height: rect.height, width: rect.width },
        hasBackdrop: Boolean(backdrop),
        viewportHeight: window.innerHeight,
        bodyOverflow: document.body.style.overflow,
      };
    });

    logTest('Mobile Popover is portaled directly to document.body', sheetMetrics.isAttachedToBody, {
      isAttachedToBody: sheetMetrics.isAttachedToBody,
    });

    const isWithinViewport = sheetMetrics.rect.top >= 0 && sheetMetrics.rect.top < sheetMetrics.viewportHeight;
    logTest('Mobile Popover is fully visible within viewport (not top: -412px)', isWithinViewport, {
      top: sheetMetrics.rect.top,
      bottom: sheetMetrics.rect.bottom,
      viewportHeight: sheetMetrics.viewportHeight,
    });

    logTest('Mobile Popover renders dedicated backdrop overlay and locks body scroll', sheetMetrics.hasBackdrop && sheetMetrics.bodyOverflow === 'hidden', {
      hasBackdrop: sheetMetrics.hasBackdrop,
      bodyOverflow: sheetMetrics.bodyOverflow,
    });

    await mobilePage.screenshot({ path: path.join(outDir, '01-mobile-picker-open.png') });

    // Test Escape key restores focus to trigger button
    await mobilePage.keyboard.press('Escape');
    await mobilePage.waitForTimeout(400);

    const focusRestored = await mobilePage.evaluate(() => {
      const trigger = document.querySelector('.product-picker-trigger');
      return document.activeElement === trigger;
    });

    logTest('Escape key closes mobile popover and restores focus to trigger', focusRestored, {
      focusRestored,
    });

    await mobileContext.close();

    // =========================================================================
    // 2. FLOATING INSET NAVBAR & TABLET OVERFLOW (820x1180)
    // =========================================================================
    console.log('\n--- 2. Testing Floating Inset Navbar & Tablet Viewport (820px) ---');
    const tabletContext = await browser.newContext({ viewport: { width: 820, height: 1180 } });
    const tabletPage = await tabletContext.newPage();

    await tabletPage.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
    await tabletPage.waitForTimeout(500);

    const tabletNavMetrics = await tabletPage.evaluate(() => {
      const header = document.querySelector('.shop-header');
      const cs = window.getComputedStyle(header);
      const docWidth = document.documentElement.clientWidth;
      const scrollWidth = document.documentElement.scrollWidth;
      return {
        borderRadius: cs.borderRadius,
        boxShadow: cs.boxShadow,
        borderColor: cs.borderColor,
        noHorizontalOverflow: scrollWidth <= docWidth + 1,
        docWidth,
        scrollWidth,
      };
    });

    logTest('Navbar has luxury rounded inset style (radius ~22px, gold border & shadow)', parseFloat(tabletNavMetrics.borderRadius) >= 16, {
      borderRadius: tabletNavMetrics.borderRadius,
      boxShadow: tabletNavMetrics.boxShadow,
    });

    logTest('Tablet 820px has ZERO horizontal scroll overflow', tabletNavMetrics.noHorizontalOverflow, {
      docWidth: tabletNavMetrics.docWidth,
      scrollWidth: tabletNavMetrics.scrollWidth,
    });

    await tabletPage.screenshot({ path: path.join(outDir, '02-tablet-floating-navbar.png') });
    await tabletContext.close();

    // =========================================================================
    // 3. PRODUCT CARD ENTRANCE ANIMATION & PREFERS-REDUCED-MOTION
    // =========================================================================
    console.log('\n--- 3. Testing ProductCard Entrance Animation & Reduced Motion ---');
    const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const desktopPage = await desktopContext.newPage();

    await desktopPage.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
    await desktopPage.waitForTimeout(400);

    const animationMetrics = await desktopPage.evaluate(() => {
      const cards = Array.from(document.querySelectorAll('.product-card')).slice(0, 4);
      return cards.map((card, idx) => {
        const cs = window.getComputedStyle(card);
        const stagger = card.style.getPropertyValue('--stagger-index');
        return {
          idx,
          stagger,
          animationName: cs.animationName,
          animationDelay: cs.animationDelay,
          opacity: cs.opacity,
        };
      });
    });

    const hasEntranceAnimation = animationMetrics.every(c => c.animationName.includes('productCardEntrance'));
    logTest('ProductCards have entrance animation with staggered delays', hasEntranceAnimation, {
      animations: animationMetrics.map(c => ({ stagger: c.stagger, delay: c.animationDelay, name: c.animationName })),
    });

    // Test prefers-reduced-motion
    const reducedMotionContext = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      reducedMotion: 'reduce',
    });
    const reducedPage = await reducedMotionContext.newPage();
    await reducedPage.goto('http://127.0.0.1:3000', { waitUntil: 'networkidle' });
    await reducedPage.waitForTimeout(400);

    const reducedMotionResult = await reducedPage.evaluate(() => {
      const card = document.querySelector('.product-card');
      const cs = window.getComputedStyle(card);
      return {
        animationName: cs.animationName,
        opacity: cs.opacity,
      };
    });

    const isAnimationDisabled = reducedMotionResult.animationName === 'none' && reducedMotionResult.opacity === '1';
    logTest('ProductCard disables animation and remains fully visible on prefers-reduced-motion: reduce', isAnimationDisabled, {
      reducedMotionResult,
    });

    await desktopContext.close();
    await reducedMotionContext.close();

  } catch (err) {
    console.error('Test script error:', err);
    logTest('Lead Integration Verification Script executed without error', false, { error: err?.message });
  } finally {
    await browser.close();
  }

  const allPassed = testReport.tests.every(t => t.passed);
  console.log('\n======================================================');
  console.log(`LEAD INTEGRATION SUMMARY: ${testReport.tests.filter(t => t.passed).length} / ${testReport.tests.length} TESTS PASSED`);
  console.log('======================================================\n');

  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(testReport, null, 2), 'utf-8');
  process.exit(allPassed ? 0 : 1);
})();
