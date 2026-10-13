const { chromium } = require('C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  try {
    const browser = await chromium.launch({
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
      headless: true,
      args: ['--no-sandbox', '--disable-gpu', '--disable-blink-features=AutomationControlled'],
    });
    const context = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    });
    const page = await context.newPage();
    await page.goto('https://unsplash.com/s/photos/t-shirt', { waitUntil: 'domcontentloaded', timeout: 15000 });
    console.log('Title:', await page.title());
    const imgs = await page.$$eval('img', els => els.map(e => e.src).filter(s => s.includes('images.unsplash.com/photo-')));
    console.log('Found photos:', imgs.length);
    if (imgs.length > 0) {
      console.log('Sample:', imgs[0]);
    }
    await browser.close();
  } catch (e) {
    console.error('Error:', e.message);
  }
})();
