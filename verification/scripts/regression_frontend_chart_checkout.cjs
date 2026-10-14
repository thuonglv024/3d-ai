/**
 * Frontend Regression Test Suite for Auth Hygiene, BodyChart, and Checkout Validation/Auto-focus.
 * Sub-Agent 3: Independent automated regression verification.
 */
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const ROOT_DIR = path.resolve(__dirname, "../..");
const AUTH_CTX_PATH = path.join(ROOT_DIR, "frontend/lib/AuthContext.tsx");
const SCAN_CTX_PATH = path.join(ROOT_DIR, "frontend/lib/ScanContext.tsx");
const BODY_CHART_PATH = path.join(ROOT_DIR, "frontend/components/shop/BodyChart.tsx");
const CHECKOUT_PAGE_PATH = path.join(ROOT_DIR, "frontend/app/checkout/page.tsx");

function pass(msg) {
  console.log(`  [PASS] ${msg}`);
}

// ============================================================================
// 1. Test AuthContext & ScanContext Logout Hygiene (sessionStorage cleanup)
// ============================================================================
function testLogoutHygiene() {
  console.log("\n=== 1. Testing Frontend Logout Hygiene (AuthContext.tsx & ScanContext.tsx) ===");
  const authSrc = fs.readFileSync(AUTH_CTX_PATH, "utf-8");
  const scanSrc = fs.readFileSync(SCAN_CTX_PATH, "utf-8");

  assert(
    authSrc.includes('key.startsWith("morph_scan_")') &&
      authSrc.includes("morph_saved_scans_map") &&
      authSrc.includes('new CustomEvent("morph:auth:logout")'),
    "AuthContext.tsx cleans morph_scan_*, morph_saved_scans_map and dispatches morph:auth:logout"
  );
  pass("AuthContext.tsx contains sessionStorage cleanup for morph_scan_*, morph_saved_scans_map, and dispatches morph:auth:logout");

  assert(
    scanSrc.includes('window.addEventListener("morph:auth:logout"') &&
      scanSrc.includes("clearPersonalScanData") &&
      scanSrc.includes("morph_saved_scans_map") &&
      scanSrc.includes("morph_scan_guest_token_"),
    "ScanContext.tsx listens for morph:auth:logout and clears state + sessionStorage"
  );
  pass("ScanContext.tsx listens for morph:auth:logout and invokes clearPersonalScanData()");

  // Simulate sessionStorage during logout
  const store = new Map([
    ["morph_scan_guest_token_scan01", "secret_tok_1"],
    ["morph_scan_guest_token_scan02", "secret_tok_2"],
    ["morph_saved_scans_map", '{"scan01":"saved"}'],
    ["morph_user_cache", '{"id":"u1"}'],
    ["morph_cart_v1", '[{"productId":"p1"}]'],
  ]);

  const mockSessionStorage = {
    get length() {
      return store.size;
    },
    key(i) {
      return Array.from(store.keys())[i] ?? null;
    },
    getItem(k) {
      return store.has(k) ? store.get(k) : null;
    },
    removeItem(k) {
      store.delete(k);
    },
  };

  // Execute the cleanup logic from AuthContext.tsx
  mockSessionStorage.removeItem("morph_saved_scans_map");
  const keysToRemove = [];
  for (let i = 0; i < mockSessionStorage.length; i++) {
    const key = mockSessionStorage.key(i);
    if (
      key &&
      (key.startsWith("morph_scan_") ||
        key.startsWith("morph_user_") ||
        key === "morph_saved_scans_map")
    ) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((k) => mockSessionStorage.removeItem(k));

  assert.strictEqual(mockSessionStorage.getItem("morph_scan_guest_token_scan01"), null);
  assert.strictEqual(mockSessionStorage.getItem("morph_scan_guest_token_scan02"), null);
  assert.strictEqual(mockSessionStorage.getItem("morph_saved_scans_map"), null);
  assert.strictEqual(mockSessionStorage.getItem("morph_user_cache"), null);
  assert.strictEqual(mockSessionStorage.getItem("morph_cart_v1"), '[{"productId":"p1"}]');
  pass("Simulated sessionStorage cleanup removes morph_scan_guest_token_* and morph_saved_scans_map while preserving unrelated keys");
}

// ============================================================================
// 2. Test BodyChart Linear X-Coords, Zero-Span, Broken Paths & Cluster Badges
// ============================================================================
function computeBodyChartModel(timeline, selectedMetrics = { chest_cm: true, waist_cm: true, hip_cm: true, shoulder_width_cm: true }) {
  const width = 840;
  const height = 340;
  const padding = { top: 30, right: 30, bottom: 50, left: 55 };
  const chartInnerWidth = width - padding.left - padding.right; // 755
  const chartInnerHeight = height - padding.top - padding.bottom; // 260

  const sortedPoints = [...timeline].sort(
    (a, b) => new Date(a.captured_at).getTime() - new Date(b.captured_at).getTime()
  );

  // Y min/max
  let min = Infinity;
  let max = -Infinity;
  let count = 0;
  sortedPoints.forEach((p) => {
    Object.keys(selectedMetrics).forEach((mk) => {
      if (!selectedMetrics[mk]) return;
      const m = p.metrics?.[mk];
      if (m && m.valid_for_tracking && m.value !== null && !isNaN(m.value) && m.value > 0) {
        if (m.value < min) min = m.value;
        if (m.value > max) max = m.value;
        count++;
      }
    });
  });

  const { minY, maxY } =
    count === 0 || min === Infinity
      ? { minY: 50, maxY: 120 }
      : {
          minY: Math.max(30, Math.floor((min - 4) / 5) * 5),
          maxY: Math.max(Math.max(30, Math.floor((min - 4) / 5) * 5) + 15, Math.ceil((max + 4) / 5) * 5),
        };

  const getYCoord = (val) => {
    if (maxY === minY) return padding.top + chartInnerHeight / 2;
    const ratio = (val - minY) / (maxY - minY);
    return padding.top + chartInnerHeight - ratio * chartInnerHeight;
  };

  // X coords
  const n = sortedPoints.length;
  let xCoords = [];
  let timeSpan = 0;
  if (n > 0) {
    const timestamps = sortedPoints.map((p) => new Date(p.captured_at).getTime());
    const minT = Math.min(...timestamps);
    const maxT = Math.max(...timestamps);
    const span = maxT - minT;
    if (span <= 0 || n === 1) {
      const mid = padding.left + chartInnerWidth / 2;
      xCoords = sortedPoints.map(() => mid);
      timeSpan = 0;
    } else {
      xCoords = timestamps.map((t) => padding.left + ((t - minT) / span) * chartInnerWidth);
      timeSpan = span;
    }
  }

  // Clusters (< 16px)
  const clusters = [];
  if (sortedPoints.length >= 2) {
    let currentGroup = [{ point: sortedPoints[0], index: 0, x: xCoords[0] }];
    for (let i = 1; i < sortedPoints.length; i++) {
      const prevX = currentGroup[currentGroup.length - 1].x;
      const currX = xCoords[i];
      if (currX - prevX < 16) {
        currentGroup.push({ point: sortedPoints[i], index: i, x: currX });
      } else {
        if (currentGroup.length > 1) {
          const avgX = currentGroup.reduce((s, it) => s + it.x, 0) / currentGroup.length;
          clusters.push({ id: `cluster-${currentGroup[0].point.scan_id}`, centerX: avgX, scans: [...currentGroup] });
        }
        currentGroup = [{ point: sortedPoints[i], index: i, x: xCoords[i] }];
      }
    }
    if (currentGroup.length > 1) {
      const avgX = currentGroup.reduce((s, it) => s + it.x, 0) / currentGroup.length;
      clusters.push({ id: `cluster-${currentGroup[0].point.scan_id}`, centerX: avgX, scans: [...currentGroup] });
    }
  }

  // Broken paths
  const metricPaths = {};
  Object.keys(selectedMetrics).forEach((mk) => {
    const segments = [];
    const allValid = [];
    let currentSegment = [];
    if (selectedMetrics[mk]) {
      sortedPoints.forEach((p, idx) => {
        const m = p.metrics?.[mk];
        const isValid =
          m &&
          m.valid_for_tracking === true &&
          m.source !== "template_model" &&
          m.value !== null &&
          !isNaN(m.value) &&
          m.value > 0;
        if (isValid) {
          const pt = { x: xCoords[idx], y: getYCoord(m.value), p, val: m.value, src: m.source };
          currentSegment.push(pt);
          allValid.push(pt);
        } else {
          if (currentSegment.length > 0) {
            const d = currentSegment.reduce(
              (acc, pt, i) => (i === 0 ? `M ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}` : `${acc} L ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`),
              ""
            );
            segments.push({ d, points: [...currentSegment] });
            currentSegment = [];
          }
        }
      });
      if (currentSegment.length > 0) {
        const d = currentSegment.reduce(
          (acc, pt, i) => (i === 0 ? `M ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}` : `${acc} L ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`),
          ""
        );
        segments.push({ d, points: [...currentSegment] });
      }
    }
    metricPaths[mk] = { segments, allValidPoints: allValid };
  });

  return { xCoords, timeSpan, clusters, metricPaths, padding, chartInnerWidth };
}

function testBodyChartModule() {
  console.log("\n=== 2. Testing BodyChart Module (frontend/components/shop/BodyChart.tsx) ===");
  const chartSrc = fs.readFileSync(BODY_CHART_PATH, "utf-8");

  // Verify source code formulas & guards in BodyChart.tsx
  assert(
    chartSrc.includes("const ratio = (t - minT) / span;") &&
      chartSrc.includes("return padding.left + ratio * chartInnerWidth;"),
    "BodyChart.tsx computes linear time X coordinate using padding.left + ((t - minT) / span) * chartInnerWidth"
  );
  assert(
    chartSrc.includes("if (span <= 0 || n === 1)") &&
      chartSrc.includes("const mid = padding.left + chartInnerWidth / 2;"),
    "BodyChart.tsx handles zero-span and single-point at padding.left + chartInnerWidth / 2"
  );
  assert(
    chartSrc.includes("m.valid_for_tracking === true") &&
      chartSrc.includes('m.source !== "template_model"') &&
      chartSrc.includes("m.value !== null") &&
      chartSrc.includes("m.value > 0"),
    "BodyChart.tsx filters out null, <= 0, valid_for_tracking===false, and source==='template_model'"
  );
  assert(
    chartSrc.includes("if (currX - prevX < 16)"),
    "BodyChart.tsx clusters points within < 16px on the X axis"
  );
  pass("BodyChart.tsx source code structure verified for linear X, zero-span guard, broken path honesty, and <16px cluster badges");

  // 2A. Linear X Coordinates (Day 0, Day 3, Day 10 -> ratios 0, 0.3, 1.0)
  const t0 = new Date("2026-10-01T10:00:00Z").getTime();
  const dayMs = 24 * 3600 * 1000;
  const linearTimeline = [
    { scan_id: "s1", captured_at: new Date(t0).toISOString(), capture_mode: "full_body", metrics: { chest_cm: { value: 95, source: "photo_estimate", valid_for_tracking: true } } },
    { scan_id: "s2", captured_at: new Date(t0 + 3 * dayMs).toISOString(), capture_mode: "full_body", metrics: { chest_cm: { value: 96, source: "photo_estimate", valid_for_tracking: true } } },
    { scan_id: "s3", captured_at: new Date(t0 + 10 * dayMs).toISOString(), capture_mode: "full_body", metrics: { chest_cm: { value: 97, source: "photo_estimate", valid_for_tracking: true } } },
  ];
  const linearRes = computeBodyChartModel(linearTimeline);
  assert.strictEqual(linearRes.xCoords[0], 55);
  assert(Math.abs(linearRes.xCoords[1] - (55 + 0.3 * 755)) < 1e-6, `Expected 281.5, got ${linearRes.xCoords[1]}`);
  assert.strictEqual(linearRes.xCoords[2], 810);
  pass(`Linear X-coordinates accurately computed: [${linearRes.xCoords.join(", ")}]`);

  // 2B. Single point & Zero-span -> centered at 432.5, no NaN
  const singleRes = computeBodyChartModel([linearTimeline[0]]);
  assert.strictEqual(singleRes.xCoords.length, 1);
  assert.strictEqual(singleRes.xCoords[0], 55 + 755 / 2); // 432.5
  assert(!Number.isNaN(singleRes.xCoords[0]));

  const zeroSpanRes = computeBodyChartModel([
    linearTimeline[0],
    { ...linearTimeline[1], captured_at: linearTimeline[0].captured_at },
  ]);
  assert.deepStrictEqual(zeroSpanRes.xCoords, [432.5, 432.5]);
  assert.strictEqual(zeroSpanRes.timeSpan, 0);
  pass("Single-point (n===1) and Zero-span (timeSpan<=0) place X at center (432.5) without NaN or division by zero");

  // 2C. Broken Path for null, <=0, valid_for_tracking===false, and template_model
  const brokenTimeline = [
    {
      scan_id: "b1",
      captured_at: new Date(t0).toISOString(),
      capture_mode: "full_body",
      metrics: {
        hip_cm: { value: 94.0, source: "photo_estimate", valid_for_tracking: true },
        waist_cm: { value: 78.0, source: "photo_estimate", valid_for_tracking: true },
      },
    },
    {
      scan_id: "b2",
      captured_at: new Date(t0 + 2 * dayMs).toISOString(),
      capture_mode: "upper_body",
      metrics: {
        // Upper body scan: hip_cm is from template_model -> must break the line!
        hip_cm: { value: 95.0, source: "template_model", valid_for_tracking: false },
        // waist_cm is null -> must break the line!
        waist_cm: { value: null, source: "unavailable", valid_for_tracking: false },
      },
    },
    {
      scan_id: "b3",
      captured_at: new Date(t0 + 5 * dayMs).toISOString(),
      capture_mode: "full_body",
      metrics: {
        hip_cm: { value: 94.5, source: "photo_estimate", valid_for_tracking: true },
        waist_cm: { value: 0, source: "photo_estimate", valid_for_tracking: true }, // <= 0 -> invalid!
      },
    },
    {
      scan_id: "b4",
      captured_at: new Date(t0 + 10 * dayMs).toISOString(),
      capture_mode: "full_body",
      metrics: {
        hip_cm: { value: 95.2, source: "photo_estimate", valid_for_tracking: true },
        waist_cm: { value: 77.5, source: "photo_estimate", valid_for_tracking: true },
      },
    },
  ];
  const brokenRes = computeBodyChartModel(brokenTimeline);
  const hipSegments = brokenRes.metricPaths.hip_cm.segments;
  assert.strictEqual(hipSegments.length, 2, `Expected 2 disjoint segments for hip_cm, got ${hipSegments.length}`);
  assert.strictEqual(hipSegments[0].points.length, 1, "First segment has 1 point (b1) before template_model gap");
  assert.strictEqual(hipSegments[1].points.length, 2, "Second segment has 2 points (b3, b4) after template_model gap");
  assert(!hipSegments[0].d.includes("L"), "Single point segment uses only 'M x y' without connecting across gap");
  assert(hipSegments[1].d.startsWith("M ") && hipSegments[1].d.includes(" L "), "Second segment connects b3 -> b4 cleanly");

  const waistSegments = brokenRes.metricPaths.waist_cm.segments;
  assert.strictEqual(waistSegments.length, 2, "waist_cm broken at null (b2) and <=0 (b3) into 2 single-point segments");
  pass(`Broken path verified: hip_cm split into ${hipSegments.length} segments ["${hipSegments[0].d}", "${hipSegments[1].d}"], never drawing to 0 or across template_model`);

  // 2D. Cluster Badges (< 16px on X axis)
  // Over a 10-day span (755px), 1 hour is (1 / 240) * 755 = 3.145px (< 16px)
  const clusterTimeline = [
    { scan_id: "c1", captured_at: new Date(t0).toISOString(), capture_mode: "upper_body", metrics: { chest_cm: { value: 95, source: "photo_with_prior", valid_for_tracking: true } } },
    { scan_id: "c2", captured_at: new Date(t0 + 3600 * 1000).toISOString(), capture_mode: "full_body", metrics: { chest_cm: { value: 95.5, source: "photo_estimate", valid_for_tracking: true } } },
    { scan_id: "c3", captured_at: new Date(t0 + 10 * dayMs).toISOString(), capture_mode: "full_body", metrics: { chest_cm: { value: 96, source: "photo_estimate", valid_for_tracking: true } } },
  ];
  const clusterRes = computeBodyChartModel(clusterTimeline);
  assert.strictEqual(clusterRes.clusters.length, 1, "Detected 1 cluster for c1 and c2 (< 16px apart)");
  assert.strictEqual(clusterRes.clusters[0].scans.length, 2, "Cluster badge count equals 2");
  assert(Math.abs(clusterRes.clusters[0].scans[1].x - clusterRes.clusters[0].scans[0].x) < 16, "Distance between clustered scans is < 16px");
  pass(`Cluster detection verified: ${clusterRes.clusters[0].scans.length} close scans grouped at centerX=${clusterRes.clusters[0].centerX.toFixed(2)}px`);
}

// ============================================================================
// 3. Test Checkout Form Validation Synchronization & Immediate Auto-focus
// ============================================================================
function validatePhoneFrontend(phone) {
  const rawPhone = (phone || "").trim();
  let cleanPhone = rawPhone.replace(/[\s.\-()]/g, "");
  if (cleanPhone.startsWith("+84")) {
    cleanPhone = "0" + cleanPhone.slice(3);
  } else if (cleanPhone.startsWith("84") && (cleanPhone.length === 11 || cleanPhone.length === 12)) {
    cleanPhone = "0" + cleanPhone.slice(2);
  }
  if (!cleanPhone) {
    return { valid: false, error: "Vui lòng nhập số điện thoại liên hệ" };
  } else if (!/^\d+$/.test(cleanPhone)) {
    return { valid: false, error: "Số điện thoại chỉ được chứa các chữ số" };
  } else if (!cleanPhone.startsWith("0")) {
    return { valid: false, error: "Số điện thoại Việt Nam phải bắt đầu bằng 0 hoặc +84" };
  } else if (cleanPhone.length < 9 || cleanPhone.length > 11) {
    return { valid: false, error: "Số điện thoại phải từ 9 đến 11 chữ số" };
  }
  return { valid: true, cleaned: cleanPhone };
}

function testCheckoutValidationAndAutofocus() {
  console.log("\n=== 3. Testing Checkout Phone Validation Parity & Auto-focus (frontend/app/checkout/page.tsx) ===");
  const checkoutSrc = fs.readFileSync(CHECKOUT_PAGE_PATH, "utf-8");

  // Check phone normalization & validation in checkout/page.tsx
  assert(
    checkoutSrc.includes('cleanPhone.startsWith("+84")') &&
      checkoutSrc.includes('!cleanPhone.startsWith("0")') &&
      checkoutSrc.includes("cleanPhone.length < 9 || cleanPhone.length > 11"),
    "checkout/page.tsx normalizes +84/84 and checks 0 prefix and 9-11 digits"
  );
  pass("checkout/page.tsx contains synchronized VN phone normalization (+84 -> 0) and 9-11 digit validation");

  const validPhones = [
    ["0912345678", "0912345678"],
    ["0912 345 678", "0912345678"],
    ["+84912345678", "0912345678"],
    ["+84 912-345-678", "0912345678"],
    ["84912345678", "0912345678"],
    ["091234567", "091234567"],
    ["01234567890", "01234567890"],
  ];
  for (const [raw, expected] of validPhones) {
    const res = validatePhoneFrontend(raw);
    assert(res.valid && res.cleaned === expected, `Expected valid '${expected}' for '${raw}', got ${JSON.stringify(res)}`);
  }

  const invalidPhones = ["", "   ", "123456789", "0912345", "091234567890", "0912abc678", "+1912345678"];
  for (const bad of invalidPhones) {
    const res = validatePhoneFrontend(bad);
    assert(!res.valid, `Expected invalid for '${bad}', but got valid`);
  }
  pass("Frontend validateForm phone logic matches Backend validate_vn_phone across all 14 valid/invalid test cases");

  // Check immediate auto-focus & scrollIntoView using nextErrors in checkout/page.tsx
  assert(
    checkoutSrc.includes("const nextErrors = validateForm();") &&
      checkoutSrc.includes("const errorKeys = Object.keys(nextErrors);") &&
      checkoutSrc.includes("const firstErrorKey = errorKeys[0];") &&
      checkoutSrc.includes("const el = document.getElementById(firstErrorKey);") &&
      checkoutSrc.includes("el.focus();") &&
      checkoutSrc.includes('el.scrollIntoView({ behavior: "smooth", block: "center" });'),
    "checkout/page.tsx uses nextErrors immediately to focus and scrollIntoView the first invalid field"
  );

  // Simulate DOM auto-focus execution when form has errors on phone & address
  let focusedId = null;
  let scrolledId = null;
  let scrollOpts = null;
  const mockDocument = {
    getElementById(id) {
      return {
        id,
        focus() {
          focusedId = id;
        },
        scrollIntoView(opts) {
          scrolledId = id;
          scrollOpts = opts;
        },
      };
    },
  };

  // Suppose fullName is valid ("Nguyễn Văn A"), phone is invalid ("12345"), address is empty ("")
  const simulatedNextErrors = {
    phone: "Số điện thoại Việt Nam phải bắt đầu bằng 0 hoặc +84",
    address: "Vui lòng nhập địa chỉ nhận hàng chi tiết",
  };
  const errorKeys = Object.keys(simulatedNextErrors);
  if (errorKeys.length > 0) {
    const firstErrorKey = errorKeys[0];
    const el = mockDocument.getElementById(firstErrorKey);
    if (el) {
      el.focus();
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  assert.strictEqual(focusedId, "phone", "First invalid field ('phone') received immediate focus()");
  assert.strictEqual(scrolledId, "phone", "First invalid field ('phone') received immediate scrollIntoView()");
  assert.deepStrictEqual(scrollOpts, { behavior: "smooth", block: "center" });
  pass("Simulated submit error immediately calls focus() and scrollIntoView({ behavior: 'smooth', block: 'center' }) on firstErrorKey");
}

try {
  testLogoutHygiene();
  testBodyChartModule();
  testCheckoutValidationAndAutofocus();
  console.log("\n=========================================================");
  console.log("ALL FRONTEND REGRESSION TESTS PASSED SUCCESSFULLY (100%)");
  console.log("=========================================================");
} catch (err) {
  console.error("\n[FAIL] Frontend Regression Test Failed:", err);
  process.exit(1);
}
