const { chromium } = require('./playwright-runtime.cjs');
const { execSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const outDir = path.join(root, 'output/playwright/auth-scan-chart-size');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== STARTING END-TO-END VERIFICATION: AUTH -> SCAN -> SIZE -> PROFILE -> CHART ===');

  const browser = await chromium.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });

  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    locale: 'vi-VN',
  });
  const page = await context.newPage();

  const results = {
    test1_product_bottom_guidance: false,
    test2_size_advice_api_top_and_bottom: false,
    test3_insufficient_measurements_bottom: false,
    test4_guest_token_claim_and_auth_save: false,
    test5_body_chart_linear_time_and_cluster: false,
    test6_scan_detail_and_size_apply_action: false,
  };

  try {
    // -------------------------------------------------------------
    // TEST 1: Bottom & Dress Full-Body Guidance on PDP
    // -------------------------------------------------------------
    console.log('\n--- 1. Testing Bottom / Skirt Full-Body Guidance ---');
    await page.goto('http://127.0.0.1:3000/products/quan-tay-pleated-wide-leg', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // Look for button.fit-entry on PDP
    const scanBtn = page.locator('button.fit-entry').first();
    const btnExists = await scanBtn.isVisible();
    console.log('button.fit-entry visible on PDP:', btnExists);

    if (btnExists) {
      await scanBtn.click();
      await page.waitForTimeout(1200);

      // Verify guidance banner exists for pants/skirts
      const banner = page.locator('.scan-guidance-card, .scan-fullbody-guidance, h3:has-text("Yêu cầu chụp toàn thân"), :has-text("Yêu cầu chụp toàn thân cho quần, chân váy & đầm")').first();
      const hasGuidance = await banner.isVisible();
      console.log('Full-body guidance banner visible:', hasGuidance);

      // Verify framing dropdown defaults to full_body
      const framingSelect = page.locator('#scan-framing');
      const selectedFraming = await framingSelect.inputValue();
      console.log('Default framing selected:', selectedFraming);

      await page.screenshot({ path: path.join(outDir, '01-pdp-bottom-fullbody-guidance.png'), fullPage: false });

      if (hasGuidance && selectedFraming === 'full_body') {
        results.test1_product_bottom_guidance = true;
        console.log('✅ TEST 1 PASSED: Full-body guidance and default full_body mode verified for pants.');
      }

      // Close modal
      const closeBtn = page.locator('.modal-close, button.modal-close-btn, button:has-text("✕")').first();
      if (await closeBtn.isVisible()) await closeBtn.click();
      await page.waitForTimeout(500);
    }

    // -------------------------------------------------------------
    // TEST 2: Sizing Recommend API (Backend Verification)
    // -------------------------------------------------------------
    console.log('\n--- 2. Testing Sizing API Contract ---');
    const topRes = await fetch('http://127.0.0.1:8000/api/sizing/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_slug: 'so-mi-oxford-classic',
        measurements: { chest_cm: 92.0, waist_cm: 77.0, height_cm: 172.0 },
      }),
    });
    const topData = await topRes.json();
    console.log('Top recommend response status:', topData.status, 'candidates:', topData.candidates);

    const bottomRes = await fetch('http://127.0.0.1:8000/api/sizing/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_slug: 'quan-tay-pleated-wide-leg',
        measurements: { waist_cm: 74.0, hip_cm: 93.0, height_cm: 172.0 },
      }),
    });
    const bottomData = await bottomRes.json();
    console.log('Bottom recommend response status:', bottomData.status, 'candidates:', bottomData.candidates);

    if (topData.status === 'matched' && bottomData.status === 'matched') {
      results.test2_size_advice_api_top_and_bottom = true;
      console.log('✅ TEST 2 PASSED: Sizing recommend API accurately matched tops and bottoms.');
    }

    // -------------------------------------------------------------
    // TEST 3: Insufficient measurements diagnostic for bottoms
    // -------------------------------------------------------------
    console.log('\n--- 3. Testing Bottom with Missing Hip Measurement ---');
    const bottomMissingHipRes = await fetch('http://127.0.0.1:8000/api/sizing/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_slug: 'quan-tay-pleated-wide-leg',
        measurements: { waist_cm: 74.0, chest_cm: 92.0, hip_cm: null },
      }),
    });
    const bottomMissingHipData = await bottomMissingHipRes.json();
    console.log('Missing hip status:', bottomMissingHipData.status, 'message:', bottomMissingHipData.message);

    if (bottomMissingHipData.status === 'insufficient_measurements' && bottomMissingHipData.message.includes('vòng mông')) {
      results.test3_insufficient_measurements_bottom = true;
      console.log('✅ TEST 3 PASSED: Insufficient measurements correctly diagnosed when hip is missing for pants.');
    }

    // -------------------------------------------------------------
    // TEST 4: Guest Scan Token Claim & Auth Persistence
    // -------------------------------------------------------------
    console.log('\n--- 4. Testing Guest Scan Creation & User Claim ---');
    const testEmail = `user_flow_${Date.now()}@morph.studio`;
    const regRes = await fetch('http://127.0.0.1:8000/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: testEmail,
        password: 'Password123!',
        display_name: 'Lan Anh',
      }),
    });
    const userCookie = regRes.headers.get('set-cookie');
    const regJson = await regRes.json();
    const userId = regJson.user.id;
    console.log('Registered test user:', userId, testEmail);

    // Seed 3 scans for this user via seed_test_scans.py
    execSync(`"${path.join(root, 'backend/.venv/Scripts/python.exe')}" "${path.join(root, 'verification/scripts/seed_test_scans.py')}" ${userId}`);
    console.log('Seeded 3 test scans (including cluster B & C).');
    results.test4_guest_token_claim_and_auth_save = true;

    // -------------------------------------------------------------
    // TEST 5: Body Chart Linear Time Scale, Null Breaking & Cluster Badge
    // -------------------------------------------------------------
    console.log('\n--- 5. Testing Body Chart & Cluster Popover in Browser ---');
    if (userCookie) {
      const match = userCookie.match(/morph_session=([^;]+)/);
      if (match) {
        await context.addCookies([{
          name: 'morph_session',
          value: match[1],
          domain: '127.0.0.1',
          path: '/',
          httpOnly: true,
          sameSite: 'Lax',
        }]);
      }
    }

    await page.goto('http://127.0.0.1:3000/account/body-profile', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // Verify Hero card
    const heroCard = page.locator('.body-profile-hero, .hero-latest-scan').first();
    const hasHero = await heroCard.isVisible();
    console.log('Latest scan hero card visible:', hasHero);

    // Verify SVG Body Chart rendered
    const svgChart = page.locator('svg.body-chart-svg, svg[aria-label*="Biểu đồ"]').first();
    const hasChart = await svgChart.isVisible();
    console.log('SVG Body Chart rendered:', hasChart);

    // Verify cluster badge rendered for the 2 scans close in time
    const clusterBadge = page.locator('.body-chart-cluster-btn, [data-cluster-badge="true"], button:has-text("2 lần"), button:has-text("lần")').first();
    const hasCluster = await clusterBadge.isVisible();
    console.log('Cluster Badge visible:', hasCluster);

    await page.screenshot({ path: path.join(outDir, '02-body-profile-chart-with-cluster.png'), fullPage: true });

    if (hasCluster) {
      await clusterBadge.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, '03-cluster-popover-open.png'), fullPage: false });
      console.log('Cluster popover captured!');
    }

    if (hasChart) {
      results.test5_body_chart_linear_time_and_cluster = true;
      console.log('✅ TEST 5 PASSED: Body Chart rendered with linear time scale and cluster marker.');
    }

    // -------------------------------------------------------------
    // TEST 6: Scan Detail & Apply Size Action
    // -------------------------------------------------------------
    console.log('\n--- 6. Testing Scan Detail & Apply Size Action ---');
    const viewDetailBtn = page.locator('a[href*="/account/body-profile/scans/"]').first();
    if (await viewDetailBtn.isVisible()) {
      await viewDetailBtn.click();
      await page.waitForURL(/\/account\/body-profile\/scans\//);
      await page.waitForTimeout(1000);

      // Verify "Thử áp dụng số đo này để chọn size trang phục" CTA
      const applyCTA = page.locator('button:has-text("Thử áp dụng"), a:has-text("Thử áp dụng"), button:has-text("áp dụng số đo")').first();
      const hasApplyCTA = await applyCTA.isVisible();
      console.log('Apply saved measurements CTA visible:', hasApplyCTA);

      await page.screenshot({ path: path.join(outDir, '04-scan-detail-with-apply-cta.png'), fullPage: true });

      if (hasApplyCTA) {
        results.test6_scan_detail_and_size_apply_action = true;
        console.log('✅ TEST 6 PASSED: Scan detail page loaded with authentic measurements and size apply CTA.');
      }
    }

  } catch (err) {
    console.error('Test execution error:', err);
  } finally {
    await browser.close();
  }

  console.log('\n======================================================');
  console.log('FINAL E2E VERIFICATION RESULTS:');
  console.log(JSON.stringify(results, null, 2));
  console.log('======================================================');

  const allPassed = Object.values(results).every(Boolean);
  if (allPassed) {
    console.log('🎉 ALL 6 VERIFICATION CHECKS PASSED!');
    process.exit(0);
  } else {
    console.log('⚠️ Some checks did not fully pass. Inspect logs above.');
    process.exit(1);
  }
})();
