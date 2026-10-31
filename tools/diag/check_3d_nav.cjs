// Diagnostic only: log the AI-result -> "Dựng mô hình 3D" chain without touching production code.
// Usage: node tools/diag/check_3d_nav.cjs [--abort-scan]
const path = require("path");
const { chromium } = require(path.join(__dirname, "..", "..", "frontend", "node_modules", "playwright"));
const abortScan = process.argv.includes("--abort-scan");
const failJob = process.argv.includes("--fail-job");
const QA = path.join(__dirname, "..", "..", "verification", "scripts", "qa");

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  const events = [], errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });
  page.on("pageerror", (e) => errors.push("pageerror: " + String(e)));
  page.on("request", (r) => { if (r.url().includes("/api/")) events.push(`>> ${r.method()} ${r.url()}`); });
  page.on("response", (r) => { if (r.url().includes("/api/")) events.push(`<< ${r.status()} ${r.request().method()} ${r.url()}`); });
  if (abortScan) await page.route("**/api/scans", (r) => r.request().method() === "POST" ? r.abort() : r.continue());
  if (failJob) await page.route("**/api/scans/*", async (r) => {
    if (r.request().method() !== "GET") return r.continue();
    await r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "simulated", status: "failed", stage: "failed", error: "Simulated 3D reconstruction failure", measurements: {}, body_profile: {} }),
    });
  });

  await page.goto("http://127.0.0.1:3000/products/ao-thun-heavy-cotton-regular", { waitUntil: "networkidle", timeout: 90000 });
  await page.locator(".fit-entry").first().click();
  await page.waitForTimeout(300);
  const tab = page.getByText("AI Vision", { exact: false }).first();
  if (await tab.count()) { await tab.click(); await page.waitForTimeout(200); }
  await page.getByText("Tôi đồng ý gửi hai ảnh chụp tới dịch vụ AI", { exact: false }).click();
  await page.locator("#ai-upload-front").setInputFiles(path.join(QA, "rendered-front.png"));
  await page.locator("#ai-upload-side").setInputFiles(path.join(QA, "rendered-side.png"));
  await page.getByText("Dựng mô hình 3D từ hai ảnh này").waitFor({ timeout: 120000 });
  await page.getByText("Dựng mô hình 3D từ hai ảnh này").click();

  let state = "initial";
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1000);
    const modal = await page.locator(".fit-experience").innerText().catch(() => "");
    if (modal.includes("Hình thể 3D của bạn")) { state = "3d-result"; break; }
    if (modal.includes("Mở camera & bắt đầu") || modal.includes("Chụp đủ hai góc")) { state = "initial-scan-form"; break; }
    if (/Failed to fetch|Không kết nối|Không gửi|Chưa dựng|Simulated/.test(modal)) { state = "error"; break; }
    if (i === 29) state = "timeout";
  }
  const modal = await page.locator(".fit-experience").innerText().catch(() => "");
  console.log(JSON.stringify({
    url: page.url(),
    abortScan,
    state,
    has3DResult: modal.includes("Hình thể 3D của bạn"),
    hasInitialScanForm: modal.includes("Mở camera & bắt đầu") || modal.includes("Chụp đủ hai góc"),
    hasAiResult: modal.includes("Dựng mô hình 3D từ hai ảnh này"),
    errorVisible: /Failed to fetch|Không kết nối|Không gửi|Chưa dựng/.test(modal),
    events,
    errors,
  }, null, 2));
  await browser.close();
})();
