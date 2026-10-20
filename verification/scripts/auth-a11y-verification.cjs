const { chromium } = require('./playwright-runtime.cjs');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const outDir = path.join(root, 'output/playwright/auth-a11y');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  console.log('=== STARTING AUTH & ACCESSIBILITY VERIFICATION ===');

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
    login_initial_copy_honest: false,
    login_no_cookie_jargon: false,
    login_toggle_accessible: false,
    login_tab_reaches_toggle: false,
    login_submit_empty_shows_all_errors: false,
    login_aria_attributes_valid: false,
    login_first_invalid_focused: false,
    login_independent_error_clearing: false,
    register_initial_copy_honest: false,
    register_no_cookie_jargon: false,
    register_toggles_accessible: false,
    register_submit_empty_shows_all_errors: false,
    register_aria_attributes_valid: false,
    register_first_invalid_focused: false,
    register_password_mismatch_error: false,
  };

  try {
    // -------------------------------------------------------------
    // PART 1: LOGIN PAGE VERIFICATION
    // -------------------------------------------------------------
    console.log('\n--- 1. Testing /auth/login ---');
    await page.goto('http://127.0.0.1:3000/auth/login', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    // 1.1 Copywriting Check
    const loginSidePanelText = await page.locator('.auth-side-panel').innerText();
    const hasHonestHeading = loginSidePanelText.includes('Tư vấn kích cỡ trang phục theo vóc dáng');
    const hasHonestLead = loginSidePanelText.includes('Công nghệ ước lượng thông số hình thể 3D trực quan');
    const hasPersonalDataProtection = loginSidePanelText.includes('Bảo vệ thông tin cá nhân');
    const hasNoTailoringJargon = !loginSidePanelText.includes('may đo thế hệ mới') && !loginSidePanelText.includes('chuẩn xác tuyệt đối');
    const hasNoCookieJargon = !loginSidePanelText.includes('HttpOnly') && !loginSidePanelText.includes('Cookie');

    console.log('Login honest copy:', hasHonestHeading && hasHonestLead && hasPersonalDataProtection && hasNoTailoringJargon);
    console.log('Login no cookie jargon:', hasNoCookieJargon);
    if (hasHonestHeading && hasHonestLead && hasPersonalDataProtection && hasNoTailoringJargon) {
      results.login_initial_copy_honest = true;
    }
    if (hasNoCookieJargon) {
      results.login_no_cookie_jargon = true;
    }

    // 1.2 Password toggle accessibility
    const loginToggle = page.locator('.auth-password-toggle').first();
    const loginToggleTabIndex = await loginToggle.getAttribute('tabindex');
    const loginToggleType = await loginToggle.getAttribute('type');
    const loginToggleLabel = await loginToggle.getAttribute('aria-label');

    console.log('Login toggle tabIndex (should be null):', loginToggleTabIndex);
    console.log('Login toggle type:', loginToggleType);
    console.log('Login toggle initial aria-label:', loginToggleLabel);

    if (loginToggleTabIndex === null && loginToggleType === 'button' && loginToggleLabel === 'Hiện mật khẩu') {
      results.login_toggle_accessible = true;
    }

    // Test Tab order reaching password toggle
    await page.locator('#login-password').focus();
    await page.keyboard.press('Tab');
    const focusedAfterPass = await page.evaluate(() => document.activeElement?.className);
    console.log('Focused element after Tab from password:', focusedAfterPass);
    if (focusedAfterPass?.includes('auth-password-toggle')) {
      results.login_tab_reaches_toggle = true;
    }

    // Test clicking toggle button changes password input type and aria-label
    await loginToggle.click();
    const passTypeAfterToggle = await page.locator('#login-password').getAttribute('type');
    const toggleLabelAfter = await loginToggle.getAttribute('aria-label');
    console.log('Password input type after toggle click:', passTypeAfterToggle, 'label:', toggleLabelAfter);

    // 1.3 Form validation on empty submit
    const submitBtn = page.locator('button.auth-submit-btn');
    await submitBtn.click();
    await page.waitForTimeout(300);

    const emailError = page.locator('#login-email-error');
    const passwordError = page.locator('#login-password-error');
    const emailErrorVisible = await emailError.isVisible();
    const passwordErrorVisible = await passwordError.isVisible();
    const emailErrorText = await emailError.innerText();
    const passwordErrorText = await passwordError.innerText();

    console.log('Email error visible:', emailErrorVisible, `"${emailErrorText}"`);
    console.log('Password error visible:', passwordErrorVisible, `"${passwordErrorText}"`);

    if (emailErrorVisible && passwordErrorVisible) {
      results.login_submit_empty_shows_all_errors = true;
    }

    // 1.4 ARIA attributes check
    const emailAriaInvalid = await page.locator('#login-email').getAttribute('aria-invalid');
    const emailAriaDescribedby = await page.locator('#login-email').getAttribute('aria-describedby');
    const passAriaInvalid = await page.locator('#login-password').getAttribute('aria-invalid');
    const passAriaDescribedby = await page.locator('#login-password').getAttribute('aria-describedby');

    console.log('Email aria-invalid:', emailAriaInvalid, 'aria-describedby:', emailAriaDescribedby);
    console.log('Password aria-invalid:', passAriaInvalid, 'aria-describedby:', passAriaDescribedby);

    if (
      emailAriaInvalid === 'true' &&
      emailAriaDescribedby === 'login-email-error' &&
      passAriaInvalid === 'true' &&
      passAriaDescribedby === 'login-password-error'
    ) {
      results.login_aria_attributes_valid = true;
    }

    // 1.5 First invalid element focus check
    const activeElementId = await page.evaluate(() => document.activeElement?.id);
    console.log('Active element ID after submit empty login:', activeElementId);
    if (activeElementId === 'login-email') {
      results.login_first_invalid_focused = true;
    }

    // 1.6 Independent error clearing
    await page.locator('#login-email').fill('user@example.com');
    await page.waitForTimeout(200);
    const emailErrorVisibleAfterType = await emailError.isVisible();
    const passwordErrorStillVisible = await passwordError.isVisible();
    console.log('Email error visible after typing in email:', emailErrorVisibleAfterType);
    console.log('Password error still visible:', passwordErrorStillVisible);

    if (!emailErrorVisibleAfterType && passwordErrorStillVisible) {
      results.login_independent_error_clearing = true;
    }

    await page.screenshot({ path: path.join(outDir, '01-login-validation-a11y.png'), fullPage: false });

    // -------------------------------------------------------------
    // PART 2: REGISTER PAGE VERIFICATION
    // -------------------------------------------------------------
    console.log('\n--- 2. Testing /auth/register ---');
    await page.goto('http://127.0.0.1:3000/auth/register', { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);

    // 2.1 Copywriting Check
    const regSidePanelText = await page.locator('.auth-side-panel').innerText();
    const regHasHonestHeading = regSidePanelText.includes('Tư vấn kích cỡ trang phục theo vóc dáng');
    const regHasHonestLead = regSidePanelText.includes('Công nghệ ước lượng thông số hình thể 3D trực quan');
    const regHasNoCookieJargon = !regSidePanelText.includes('HttpOnly') && !regSidePanelText.includes('Cookie');

    console.log('Register honest copy:', regHasHonestHeading && regHasHonestLead);
    console.log('Register no cookie jargon:', regHasNoCookieJargon);
    if (regHasHonestHeading && regHasHonestLead) {
      results.register_initial_copy_honest = true;
    }
    if (regHasNoCookieJargon) {
      results.register_no_cookie_jargon = true;
    }

    // 2.2 Toggles accessibility
    const regToggles = page.locator('.auth-password-toggle');
    const toggleCount = await regToggles.count();
    console.log('Register password toggle count:', toggleCount);

    let allTogglesAccessible = toggleCount === 2;
    for (let i = 0; i < toggleCount; i++) {
      const toggle = regToggles.nth(i);
      const tabIdx = await toggle.getAttribute('tabindex');
      const btnType = await toggle.getAttribute('type');
      const btnLabel = await toggle.getAttribute('aria-label');
      if (tabIdx !== null || btnType !== 'button' || btnLabel !== 'Hiện mật khẩu') {
        allTogglesAccessible = false;
      }
    }
    console.log('All register toggles accessible (no tabIndex, button type, dynamic label):', allTogglesAccessible);
    if (allTogglesAccessible) {
      results.register_toggles_accessible = true;
    }

    // 2.3 Form validation on empty submit
    const regSubmitBtn = page.locator('button.auth-submit-btn');
    await regSubmitBtn.click();
    await page.waitForTimeout(300);

    const nameError = page.locator('#register-displayName-error');
    const regEmailError = page.locator('#register-email-error');
    const regPassError = page.locator('#register-password-error');
    const regConfirmError = page.locator('#register-confirmPassword-error');

    const allErrorsVisible =
      (await nameError.isVisible()) &&
      (await regEmailError.isVisible()) &&
      (await regPassError.isVisible()) &&
      (await regConfirmError.isVisible());

    console.log('All 4 register errors visible simultaneously:', allErrorsVisible);
    if (allErrorsVisible) {
      results.register_submit_empty_shows_all_errors = true;
    }

    // 2.4 ARIA attributes check
    const nameAriaInvalid = await page.locator('#register-displayName').getAttribute('aria-invalid');
    const nameAriaDescribedby = await page.locator('#register-displayName').getAttribute('aria-describedby');
    const regEmailAriaInvalid = await page.locator('#register-email').getAttribute('aria-invalid');
    const regEmailAriaDescribedby = await page.locator('#register-email').getAttribute('aria-describedby');
    const regPassAriaInvalid = await page.locator('#register-password').getAttribute('aria-invalid');
    const regPassAriaDescribedby = await page.locator('#register-password').getAttribute('aria-describedby');
    const regConfirmAriaInvalid = await page.locator('#register-confirmPassword').getAttribute('aria-invalid');
    const regConfirmAriaDescribedby = await page.locator('#register-confirmPassword').getAttribute('aria-describedby');

    const allAriaValid =
      nameAriaInvalid === 'true' &&
      nameAriaDescribedby === 'register-displayName-error' &&
      regEmailAriaInvalid === 'true' &&
      regEmailAriaDescribedby === 'register-email-error' &&
      regPassAriaInvalid === 'true' &&
      regPassAriaDescribedby === 'register-password-error' &&
      regConfirmAriaInvalid === 'true' &&
      regConfirmAriaDescribedby === 'register-confirmPassword-error';

    console.log('All register aria-invalid and aria-describedby valid:', allAriaValid);
    if (allAriaValid) {
      results.register_aria_attributes_valid = true;
    }

    // 2.5 First invalid element focus check
    const regActiveElementId = await page.evaluate(() => document.activeElement?.id);
    console.log('Active element ID after submit empty register (should be register-displayName):', regActiveElementId);
    if (regActiveElementId === 'register-displayName') {
      results.register_first_invalid_focused = true;
    }

    // 2.6 Password mismatch test
    await page.locator('#register-displayName').fill('Hoàng Nam');
    await page.locator('#register-email').fill('hoangnam@example.com');
    await page.locator('#register-password').fill('pass1234');
    await page.locator('#register-confirmPassword').fill('mismatch99');
    await regSubmitBtn.click();
    await page.waitForTimeout(300);

    const mismatchErrorText = await regConfirmError.innerText();
    console.log('Mismatch confirm error text:', mismatchErrorText);
    if (mismatchErrorText.includes('không khớp')) {
      results.register_password_mismatch_error = true;
    }

    await page.screenshot({ path: path.join(outDir, '02-register-validation-a11y.png'), fullPage: false });

    console.log('\n=== FINAL VERIFICATION RESULTS ===');
    console.log(JSON.stringify(results, null, 2));

    const allPassed = Object.values(results).every(Boolean);
    console.log('\nAll checks passed:', allPassed ? '✅ YES' : '❌ NO');

  } catch (err) {
    console.error('Test execution failed:', err);
  } finally {
    await browser.close();
  }
})();
