
const { chromium } = require("C:/Users/Phan Trinh Tien Dat/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("node:fs");

(async () => {
  const baseUrl = "http://127.0.0.1:8019";
  const modelUrls = ["/api/scans/c5c14d0bf05d417a84040f72034d9e47/model?guest_token=xxh5xC_hUu1-r52KE-6-4-5MbJ63gFCU", "/api/scans/c5c14d0bf05d417a84040f72034d9e47/model?guest_token=xxh5xC_hUu1-r52KE-6-4-5MbJ63gFCU", "/api/scans/1212f392281a485a979b53ee59cd1a90/model?guest_token=yAtcogn6hN2I976FVNcJKcgSucSPrvQ0", "/api/scans/b3fa1a594ea84dbd81764154c47643b3/model?guest_token=ZdWFPIwTvEEP-kubRdHoTve-PxdgXssG", "/api/scans/716ec2433d80479888d196114b5f8c32/model?guest_token=AlobSgsItb_PzO0UwjX0pzjyID4OMR9i", "/api/scans/52154e4bde074fb2817bc7d825e98daf/model?guest_token=IXJNt7OcARa6rgojpLgykDiYZxXa0XP6", "/api/scans/f8ecba79fe5649a0a390afd9899a4fa7/model?guest_token=a7paZIl452-QAIVD4bNegh_LPPnCMBOW", "/api/scans/7abbd62d2f05468fa80a2222769c1fd5/model?guest_token=n4K8nh9R8z6-X0t1xetP2FN7MbP6inQd", "/api/scans/262bf155cc1d4917baf908d0179f2960/model?guest_token=_0zSls_Qd9b_tly0es9vgmYFXBiVEJB0"];
  const outPath = "D:\\MORPH-AI\\.cache\\bench_api_load\\webgl_bench_results.json";

  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true,
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=angle"]
  });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1024 } });
    const page = await context.newPage();
    const pageErrors = [];
    page.on("pageerror", (err) => pageErrors.push(err.message));

    const tPage0 = performance.now();
    await page.goto(baseUrl + "/_bench_viewer", { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForFunction(() => window.__benchViewerReady === true, null, { timeout: 15000 });
    const viewerInitMs = Math.round((performance.now() - tPage0) * 100) / 100;

    // Warm up WebGL shader compilation on first URL, then record Cold Shader vs Warm Shader runs
    const runs = [];
    for (let i = 0; i < modelUrls.length; i++) {
      const fullUrl = baseUrl + modelUrls[i];
      const res = await page.evaluate(async (u) => {
        return await window.__benchmarkGlbParseAndRender(u, 1.75);
      }, fullUrl);
      res.run_index = i;
      res.is_first_shader_compile = (i === 0);
      runs.push(res);
    }

    fs.writeFileSync(outPath, JSON.stringify({
      viewer_page_init_ms: viewerInitMs,
      page_errors: pageErrors,
      runs
    }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
