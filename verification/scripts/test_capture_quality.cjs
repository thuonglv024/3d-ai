/**
 * Automated Verification Suite for Camera Capture & Input Quality (Agent 1)
 *
 * Verifies:
 * 1. Configurable `CAMERA_QUALITY_THRESHOLDS` & rejection of dark, overexposed/backlit,
 *    blurry (low Laplacian variance), high-motion, and cross-view scale/shoulder-drifted frames.
 * 2. `selectBestFrameFromWindow` & `pushCandidateFrame` picking the sharpest, stillest frame
 *    in the final `bestFrameWindowMs` (1600ms) instead of a shaky frame at `t = 0`.
 * 3. Immediate countdown cancellation (`deadline = 0`, `count = null`, `candidateBuffer = []`)
 *    whenever any single frame violates quality/pose/motion/cross-view conditions.
 * 4. Preview vs captured frame geometry preservation (`aspectRatioDelta < 0.002`, uncropped, unmirrored).
 * 5. Camera hardware/permission error mapping & `CaptureSession.tsx` / `FitExperience.tsx` integration.
 */

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const Module = require("module");

const ROOT_DIR = path.resolve(__dirname, "../..");
const CAPTURE_QUALITY_TS = path.join(ROOT_DIR, "frontend/lib/captureQuality.ts");
const CAPTURE_SESSION_TSX = path.join(ROOT_DIR, "frontend/components/shop/CaptureSession.tsx");
const FIT_EXPERIENCE_TSX = path.join(ROOT_DIR, "frontend/components/shop/FitExperience.tsx");
const ts = require(path.join(ROOT_DIR, "frontend/node_modules/typescript"));

function loadTypeScriptModule(filePath) {
  const source = fs.readFileSync(filePath, "utf-8");
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      strict: true,
    },
    fileName: filePath,
  });
  const mod = new Module(filePath, module);
  mod.filename = filePath;
  mod.paths = Module._nodeModulePaths(path.dirname(filePath));
  mod._compile(transpiled.outputText, filePath);
  return mod.exports;
}

const cq = loadTypeScriptModule(CAPTURE_QUALITY_TS);

let passedCount = 0;
function pass(name) {
  passedCount++;
  console.log(`  [PASS] ${name}`);
}

/**
 * Helper to synthesize an RGBA ImageData buffer with controllable mean luminance and edge sharpness.
 */
function createSyntheticImageData(width, height, { baseLum = 128, edgeContrast = 45 } = {}) {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      // High-frequency checkerboard/grid pattern in center ROI to control Laplacian variance
      const sign = (x + y) % 2 === 0 ? 1 : -1;
      const val = Math.max(0, Math.min(255, Math.round(baseLum + sign * edgeContrast)));
      const idx = (y * width + x) * 4;
      data[idx] = val;
      data[idx + 1] = val;
      data[idx + 2] = val;
      data[idx + 3] = 255;
    }
  }
  return { data, width, height };
}

/**
 * Helper to create 33 MediaPipe normalized landmarks `[x, y, visibility]`.
 */
function createLandmarks({
  shoulderY = 0.28,
  hipY = 0.58,
  offsetX = 0,
  offsetY = 0,
  visibility = 0.92,
  rightSideVisibility = null,
} = {}) {
  const lms = Array.from({ length: 33 }, () => [0.5 + offsetX, 0.5 + offsetY, visibility]);
  const rVis = rightSideVisibility !== null ? rightSideVisibility : visibility;
  // Nose (0)
  lms[0] = [0.5 + offsetX, shoulderY - 0.12 + offsetY, visibility];
  // Shoulders (11 = left, 12 = right)
  lms[11] = [0.42 + offsetX, shoulderY + offsetY, visibility];
  lms[12] = [0.58 + offsetX, shoulderY + offsetY, rVis];
  // Hips (23 = left, 24 = right)
  lms[23] = [0.44 + offsetX, hipY + offsetY, visibility];
  lms[24] = [0.56 + offsetX, hipY + offsetY, rVis];
  // Knees (25, 26) & Ankles (27, 28)
  lms[25] = [0.45 + offsetX, 0.76 + offsetY, visibility];
  lms[26] = [0.55 + offsetX, 0.76 + offsetY, rVis];
  lms[27] = [0.45 + offsetX, 0.92 + offsetY, visibility];
  lms[28] = [0.55 + offsetX, 0.92 + offsetY, rVis];
  return lms;
}

// ============================================================================
// 1. Test Thresholds & Client Frame Quality Gates
// ============================================================================
function testThresholdsAndQualityGates() {
  console.log("\n=== 1. Testing CAMERA_QUALITY_THRESHOLDS & Quality Gates ===");

  const t = cq.CAMERA_QUALITY_THRESHOLDS;
  assert.strictEqual(t.minBrightness, 45, "minBrightness must be 45");
  assert.strictEqual(t.maxBrightness, 235, "maxBrightness must be 235");
  assert.strictEqual(t.minSharpnessLaplacian, 14.0, "minSharpnessLaplacian must be 14.0");
  assert.strictEqual(t.maxLandmarkMotion, 0.018, "maxLandmarkMotion must be 0.018");
  assert.strictEqual(t.minLandmarkVisibility, 0.55, "minLandmarkVisibility must be 0.55");
  assert.strictEqual(t.minStableFramesBeforeCountdown, 3, "minStableFramesBeforeCountdown must be 3");
  assert.strictEqual(t.countdownDurationMs, 2000, "countdownDurationMs must be 2000");
  assert.strictEqual(t.bestFrameWindowMs, 1600, "bestFrameWindowMs must be 1600");
  assert.strictEqual(t.maxCrossViewScaleDrift, 0.18, "maxCrossViewScaleDrift must be 0.18");
  pass("CAMERA_QUALITY_THRESHOLDS matches all required numerical specifications");

  // Verify threshold overrides work
  const custom = cq.resolveThresholds({ minBrightness: 60, maxCrossViewScaleDrift: 0.12 });
  assert.strictEqual(custom.minBrightness, 60);
  assert.strictEqual(custom.maxCrossViewScaleDrift, 0.12);
  assert.strictEqual(custom.countdownDurationMs, 2000);
  pass("resolveThresholds supports overriding individual thresholds for testing & configuration");

  const baseLms = createLandmarks();
  const readyFeedback = {
    ready: true,
    message: "Đã thấy vai, eo và hông trên.",
    landmarks: baseLms,
  };

  // 1a. Reject dark frame
  const darkImg = createSyntheticImageData(80, 60, { baseLum: 25, edgeContrast: 10 });
  const darkEval = cq.evaluateClientFrameQuality({
    imageData: darkImg,
    feedback: readyFeedback,
    previousLandmarks: baseLms,
    mode: "upper_body",
    view: "front",
  });
  assert.strictEqual(darkEval.ok, false);
  assert.strictEqual(darkEval.issue, "too_dark");
  assert.strictEqual(
    darkEval.message,
    "Khung hình hơi tối. Hãy bật thêm đèn hoặc đứng hướng về nguồn sáng."
  );
  pass("Rejects underexposed/dark frame (< 45) with exact Vietnamese guidance");

  // 1b. Reject overexposed / backlit frame
  const brightImg = createSyntheticImageData(80, 60, { baseLum: 248, edgeContrast: 4 });
  const brightEval = cq.evaluateClientFrameQuality({
    imageData: brightImg,
    feedback: readyFeedback,
    previousLandmarks: baseLms,
    mode: "upper_body",
    view: "front",
  });
  assert.strictEqual(brightEval.ok, false);
  assert.strictEqual(brightEval.issue, "too_bright");
  assert.strictEqual(
    brightEval.message,
    "Ánh sáng phía sau quá gắt. Hãy tránh đứng ngược sáng trực tiếp."
  );
  pass("Rejects overexposed/backlit frame (> 235) with exact Vietnamese guidance");

  // 1c. Reject blurry frame (Laplacian variance < 14.0)
  const blurryImg = createSyntheticImageData(80, 60, { baseLum: 130, edgeContrast: 0 });
  const blurryEval = cq.evaluateClientFrameQuality({
    imageData: blurryImg,
    feedback: readyFeedback,
    previousLandmarks: baseLms,
    mode: "upper_body",
    view: "front",
  });
  assert.strictEqual(blurryEval.ok, false);
  assert.strictEqual(blurryEval.issue, "too_blurry");
  assert.strictEqual(
    blurryEval.message,
    "Hình ảnh đang bị nhòe do chuyển động. Hãy đứng yên hơn."
  );
  pass("Rejects blurry frame (Laplacian variance < 14.0) with exact Vietnamese guidance");

  // 1d. Reject excessive landmark motion (>= 0.018)
  const sharpGoodImg = createSyntheticImageData(80, 60, { baseLum: 135, edgeContrast: 18 });
  const movedLms = createLandmarks({ offsetX: 0.025, offsetY: 0.015 });
  const motionEval = cq.evaluateClientFrameQuality({
    imageData: sharpGoodImg,
    feedback: { ...readyFeedback, landmarks: movedLms },
    previousLandmarks: baseLms,
    mode: "upper_body",
    view: "front",
  });
  assert.strictEqual(motionEval.ok, false);
  assert.strictEqual(motionEval.issue, "excessive_motion");
  assert(motionEval.motion >= t.maxLandmarkMotion);
  assert.strictEqual(
    motionEval.message,
    "Hình ảnh đang bị nhòe do chuyển động. Hãy đứng yên hơn."
  );
  pass("Rejects frame with excessive landmark motion (>= 0.018)");

  // 1e. Reject cross-view scale drift (> 18% torso length change between front and side)
  const frontLms = createLandmarks({ shoulderY: 0.28, hipY: 0.58 }); // torsoLength = 0.30
  const sideSteppedCloserLms = createLandmarks({
    shoulderY: 0.25,
    hipY: 0.64, // torsoLength = 0.39 (+30% scale drift > 18%)
    rightSideVisibility: 0.25,
  });
  const driftEval = cq.evaluateClientFrameQuality({
    imageData: sharpGoodImg,
    feedback: { ready: true, message: "OK", landmarks: sideSteppedCloserLms },
    previousLandmarks: sideSteppedCloserLms,
    frontLandmarks: frontLms,
    mode: "upper_body",
    view: "side",
  });
  assert.strictEqual(driftEval.ok, false);
  assert.strictEqual(driftEval.issue, "cross_view_drift");
  assert.strictEqual(driftEval.crossViewCompatible, false);
  assert(driftEval.scaleDrift > 0.18);
  assert.strictEqual(
    driftEval.message,
    "Khoảng cách đứng đã thay đổi so với góc chính diện. Hãy đứng đúng vị trí cũ và xoay 90°."
  );
  pass("Rejects side-view frame when standing distance / torso scale drifts > 18% from front view");

  // 1f. Reject cross-view vertical shoulder drift (|shoulder_y_side - shoulder_y_front| > 0.12)
  const sideTiltedCameraLms = createLandmarks({
    shoulderY: 0.43, // |0.43 - 0.28| = 0.15 > 0.12
    hipY: 0.73, // torsoLength = 0.30 (same scale, but camera tilted)
  });
  const shoulderDriftEval = cq.evaluateClientFrameQuality({
    imageData: sharpGoodImg,
    feedback: { ready: true, message: "OK", landmarks: sideTiltedCameraLms },
    previousLandmarks: sideTiltedCameraLms,
    frontLandmarks: frontLms,
    mode: "upper_body",
    view: "side",
  });
  assert.strictEqual(shoulderDriftEval.ok, false);
  assert.strictEqual(shoulderDriftEval.issue, "cross_view_drift");
  assert(shoulderDriftEval.shoulderYDrift > 0.12);
  pass("Rejects side-view frame when vertical shoulder center drifts > 0.12 of frame height");

  // 1g. Accept valid side-view frame with occluded back side when standing at same distance
  const validSideLms = createLandmarks({
    shoulderY: 0.29,
    hipY: 0.585,
    rightSideVisibility: 0.18, // occluded far shoulder/hip in 90-deg profile
  });
  const validSideEval = cq.evaluateClientFrameQuality({
    imageData: sharpGoodImg,
    feedback: { ready: true, message: "OK", landmarks: validSideLms },
    previousLandmarks: validSideLms,
    frontLandmarks: frontLms,
    mode: "upper_body",
    view: "side",
  });
  assert.strictEqual(validSideEval.ok, true);
  assert.strictEqual(validSideEval.crossViewCompatible, true);
  assert(validSideEval.frameQualityScore > 0.7);
  pass("Accepts valid 90° side-view frame with occluded far-side landmarks when distance is preserved");
}

// ============================================================================
// 2. Test Best-Frame Selection in Final Countdown Window
// ============================================================================
function testBestFrameSelection() {
  console.log("\n=== 2. Testing Best-Frame Selection in Countdown Window (bestFrameWindowMs = 1600ms) ===");

  const deadlineMs = 10_000;
  let buffer = [];

  const candidates = [
    // Outside window (t = 7800ms, 2200ms before deadline -> should be ignored)
    {
      timestampMs: 7800,
      motion: 0.0,
      sharpness: 95,
      meanVisibility: 0.99,
      payload: "early_outside_window",
    },
    // Inside window #1 (t = 8600ms, 1400ms before deadline): moderate quality
    {
      timestampMs: 8600,
      motion: 0.009,
      sharpness: 24,
      meanVisibility: 0.82,
      payload: "window_frame_1",
    },
    // Inside window #2 (t = 9150ms, 850ms before deadline): SHARPEST & STILLEST (optimal)
    {
      timestampMs: 9150,
      motion: 0.0012,
      sharpness: 68,
      meanVisibility: 0.96,
      payload: "window_frame_2_best",
    },
    // Inside window #3 (t = 9600ms, 400ms before deadline): good but slightly more motion
    {
      timestampMs: 9600,
      motion: 0.0055,
      sharpness: 38,
      meanVisibility: 0.9,
      payload: "window_frame_3",
    },
    // Inside window #4 (t = 10000ms, exact t = 0): user slightly twitched right at countdown end
    {
      timestampMs: 10000,
      motion: 0.0165,
      sharpness: 15.2,
      meanVisibility: 0.78,
      payload: "window_frame_4_shaky_last",
    },
  ];

  for (const c of candidates) {
    buffer = cq.pushCandidateFrame(buffer, c, deadlineMs);
  }

  assert(
    buffer.length <= cq.CAMERA_QUALITY_THRESHOLDS.maxCandidateBufferSize,
    "Candidate buffer respects maxCandidateBufferSize"
  );
  assert(
    !buffer.some((c) => c.payload === "early_outside_window"),
    "Frames before (deadline - bestFrameWindowMs) are excluded from buffer"
  );

  const selected = cq.selectBestFrameFromWindow(buffer, {
    nowMs: 10000,
    deadlineMs,
  });
  assert(selected !== null, "selectBestFrameFromWindow returns a candidate");
  assert.strictEqual(
    selected.payload,
    "window_frame_2_best",
    "Must select the sharpest & stillest frame in the window rather than the shaky frame at t=0"
  );
  pass("selectBestFrameFromWindow picks 'window_frame_2_best' over shaky t=0 frame and ignores out-of-window frames");
}

// ============================================================================
// 3. Test Countdown State Machine & Immediate Cancellation on Quality Loss
// ============================================================================
function testCountdownCancellation() {
  console.log("\n=== 3. Testing Countdown Lifecycle & Immediate Cancellation ===");

  const sharpImg = createSyntheticImageData(80, 60, { baseLum: 130, edgeContrast: 20 });
  const lms = createLandmarks();
  const goodEval = cq.evaluateClientFrameQuality({
    imageData: sharpImg,
    feedback: { ready: true, message: "OK", landmarks: lms },
    previousLandmarks: lms,
  });

  let state = {
    stableFrames: 0,
    deadlineMs: 0,
    countSeconds: null,
    previousLandmarks: null,
    candidateBuffer: [],
    cancelledReason: null,
    wasCancelled: false,
    shouldCapture: false,
    selectedCandidate: null,
  };

  // Frame 1 & Frame 2: stableFrames = 1, 2 -> countdown not started yet
  state = cq.stepCountdownState(state, goodEval, 1000, { landmarks: lms, payload: "f1" });
  assert.strictEqual(state.stableFrames, 1);
  assert.strictEqual(state.deadlineMs, 0);
  assert.strictEqual(state.countSeconds, null);

  state = cq.stepCountdownState(state, goodEval, 1400, { landmarks: lms, payload: "f2" });
  assert.strictEqual(state.stableFrames, 2);
  assert.strictEqual(state.deadlineMs, 0);

  // Frame 3: reaches minStableFramesBeforeCountdown (3) -> countdown starts at t=1800, deadline=3800
  state = cq.stepCountdownState(state, goodEval, 1800, { landmarks: lms, payload: "f3" });
  assert.strictEqual(state.stableFrames, 3);
  assert.strictEqual(state.deadlineMs, 3800);
  assert.strictEqual(state.countSeconds, 2);
  pass("Countdown starts only after 3 consecutive stable frames (minStableFramesBeforeCountdown = 3)");

  // Advance to t=2400 (1400ms left, inside the 1600ms best-frame window) -> buffers candidate
  state = cq.stepCountdownState(state, goodEval, 2400, { landmarks: lms, payload: "f4_in_window" });
  assert.strictEqual(state.countSeconds, 2);
  assert.strictEqual(state.candidateBuffer.length, 1);

  // At t=3000 (800ms left), user moves abruptly -> must cancel countdown IMMEDIATELY
  const movedLms = createLandmarks({ offsetX: 0.04 });
  const badMotionEval = cq.evaluateClientFrameQuality({
    imageData: sharpImg,
    feedback: { ready: true, message: "OK", landmarks: movedLms },
    previousLandmarks: lms,
  });

  state = cq.stepCountdownState(state, badMotionEval, 3000, {
    landmarks: movedLms,
    payload: "f5_bad",
  });
  assert.strictEqual(state.wasCancelled, true, "wasCancelled must be true when active countdown is aborted");
  assert.strictEqual(state.deadlineMs, 0, "deadlineMs must reset to 0");
  assert.strictEqual(state.countSeconds, null, "countSeconds must reset to null");
  assert.strictEqual(state.stableFrames, 0, "stableFrames must reset to 0");
  assert.strictEqual(state.candidateBuffer.length, 0, "candidateBuffer must be cleared");
  assert.strictEqual(
    state.cancelledReason,
    "Hình ảnh đang bị nhòe do chuyển động. Hãy đứng yên hơn."
  );
  pass("Countdown cancels immediately on single unstable frame, clearing deadline and candidateBuffer with specific reason");
}

// ============================================================================
// 4. Test Geometry Preservation (Preview vs Captured Canvas)
// ============================================================================
function testGeometryPreservation() {
  console.log("\n=== 4. Testing Preview vs Captured Frame Geometry Preservation ===");

  const resolutions = [
    [1920, 1080],
    [1280, 720],
    [1080, 1920],
    [640, 480],
    [2560, 1440],
  ];

  for (const [vw, vh] of resolutions) {
    const previewDim = cq.computeGeometryPreservingDimensions(vw, vh, 720);
    const previewCheck = cq.verifyFrameGeometry(vw, vh, previewDim.width, previewDim.height, vw / vh);
    assert.strictEqual(
      previewCheck.geometryValid,
      true,
      `Preview geometry invalid for ${vw}x${vh}: delta=${previewCheck.aspectRatioDelta}`
    );
    assert(
      previewCheck.aspectRatioDelta < 0.002,
      `Aspect ratio delta ${previewCheck.aspectRatioDelta} >= 0.002 for ${vw}x${vh}`
    );

    const fullDim = cq.computeGeometryPreservingDimensions(vw, vh, null);
    assert.strictEqual(fullDim.width, vw);
    assert.strictEqual(fullDim.height, vh);
    const fullCheck = cq.verifyFrameGeometry(vw, vh, fullDim.width, fullDim.height, vw / vh);
    assert.strictEqual(fullCheck.geometryValid, true);
    assert.strictEqual(fullCheck.aspectRatioDelta, 0);
  }
  pass("computeGeometryPreservingDimensions & verifyFrameGeometry keep aspectRatioDelta < 0.002 across all resolutions");

  // Verify extractGeometryPreservingFrame with mock video and canvas
  let transformArgs = null;
  let drawImageArgs = null;
  const mockVideo = { videoWidth: 1920, videoHeight: 1080 };
  const extracted = cq.extractGeometryPreservingFrame(mockVideo, {
    maxDimension: 720,
    createCanvas(w, h) {
      return {
        width: w,
        height: h,
        getContext() {
          return {
            setTransform(...args) {
              transformArgs = args;
            },
            drawImage(...args) {
              drawImageArgs = args;
            },
          };
        },
      };
    },
  });

  assert.strictEqual(extracted.width, 720);
  assert.strictEqual(extracted.height, 405);
  assert.strictEqual(extracted.geometryValid, true);
  assert.strictEqual(extracted.mirrored, false);
  assert.strictEqual(extracted.cropped, false);
  assert.deepStrictEqual(transformArgs, [1, 0, 0, 1, 0, 0]);
  assert.deepStrictEqual(drawImageArgs.slice(1), [0, 0, 1920, 1080, 0, 0, 720, 405]);
  pass("extractGeometryPreservingFrame uses identity transform (unmirrored) and full source bounds (uncropped)");
}

// ============================================================================
// 5. Test Hardware Error Mapping & Component Integration
// ============================================================================
function testHardwareErrorsAndComponentIntegration() {
  console.log("\n=== 5. Testing Hardware Error Mapping & Component Integration ===");

  assert.strictEqual(
    cq.mapCameraDeviceError({ name: "NotAllowedError" }).code,
    "permission_denied"
  );
  assert.strictEqual(
    cq.mapCameraDeviceError({ name: "PermissionDeniedError" }).code,
    "permission_denied"
  );
  assert.strictEqual(
    cq.mapCameraDeviceError({ name: "NotFoundError" }).code,
    "device_not_found"
  );
  assert.strictEqual(
    cq.mapCameraDeviceError({ name: "DevicesNotFoundError" }).code,
    "device_not_found"
  );
  assert.strictEqual(
    cq.mapCameraDeviceError({ name: "NotReadableError" }).code,
    "device_busy"
  );
  assert.strictEqual(
    cq.mapCameraDeviceError({ name: "TrackStartError" }).code,
    "device_busy"
  );
  pass("mapCameraDeviceError maps permission, missing device, and busy camera errors accurately");

  const sessionSrc = fs.readFileSync(CAPTURE_SESSION_TSX, "utf-8");
  const fitSrc = fs.readFileSync(FIT_EXPERIENCE_TSX, "utf-8");
  const qualitySrc = fs.readFileSync(CAPTURE_QUALITY_TS, "utf-8");

  assert(
    !sessionSrc.includes("95%") && !fitSrc.includes("95%") && !qualitySrc.includes("95%"),
    "Must not contain fabricated 95% confidence claims"
  );
  assert(
    sessionSrc.includes("extractGeometryPreservingFrame") &&
      sessionSrc.includes("evaluateClientFrameQuality") &&
      sessionSrc.includes("pushCandidateFrame") &&
      sessionSrc.includes("selectBestFrameFromWindow") &&
      sessionSrc.includes("mapCameraDeviceError"),
    "CaptureSession.tsx integrates all quality and best-frame helpers from captureQuality.ts"
  );
  assert(
    fitSrc.includes("requiresHipMeasurement") &&
      fitSrc.includes("hệ thống sẽ từ chối tự động gợi ý size quần/váy từ số đo mẫu 3D") &&
      fitSrc.includes("không lưu trữ lâu dài hồ sơ ảnh thô"),
    "FitExperience.tsx includes full-body preparation guidance, laptop upper_body hip warning, and data lifecycle consent notice"
  );
  pass("CaptureSession.tsx and FitExperience.tsx verified for full integration and honest disclosures");
}

// ============================================================================
// 6. Test the Three-Marker Aiming Frame (U1)
// ============================================================================
function testAimFrame() {
  console.log("\n=== 6. Testing the Three-Marker Aiming Frame (U1) ===");

  const zones = cq.aimFrameZones("upper_body");
  assert.strictEqual(zones.length, 3, "The aiming frame must define exactly three markers");
  assert.deepStrictEqual(
    zones.map((z) => z.key),
    ["head", "shoulder", "hip"],
    "The three markers must be crown, shoulder and hip, in body order"
  );
  assert.deepStrictEqual(
    cq.aimFrameZones("full_body").map((z) => z.key),
    ["head", "shoulder", "hip"]
  );

  const pending = cq.pendingAimFrame("upper_body");
  assert.strictEqual(pending.ok, true);
  assert.strictEqual(pending.anchors.length, 0, "Bands alone must not invent a body position");
  assert.strictEqual(pending.zones.length, 3);
  pass("Aiming frame exposes crown/shoulder/hip bands per capture mode without inventing anchors");

  const base = createLandmarks(); // nose .16, shoulders .28, hips .58
  const anchors = cq.extractAimAnchors(base);
  assert.strictEqual(anchors.length, 3, "Three anchors must be extracted from a full pose");
  assert(anchors[0].y < anchors[1].y && anchors[1].y < anchors[2].y, "Anchors must stay head < shoulder < hip");
  assert(anchors[0].y < base[0][1], "Crown anchor must sit above the nose landmark");
  assert(Math.abs(anchors[1].x - 0.5) < 1e-6 && Math.abs(anchors[2].x - 0.5) < 1e-6);
  pass("extractAimAnchors places crown above the nose and shoulder/hip at the torso centre");

  const okFrame = cq.evaluateAimFrame(base, "upper_body", "front");
  assert.strictEqual(okFrame.ok, true, `Default pose must fit the frame: ${okFrame.message}`);

  const fullBody = cq.evaluateAimFrame(
    createLandmarks({ shoulderY: 0.22, hipY: 0.52 }),
    "full_body",
    "front"
  );
  assert.strictEqual(fullBody.ok, true, `Full-body pose must fit its own bands: ${fullBody.message}`);
  pass("Accepted frames pass for both upper_body and full_body bands");

  // Hip too high in frame -> torso span below the minimum -> countdown must be blocked
  const highHip = createLandmarks({ hipY: 0.44 });
  const highHipEval = cq.evaluateAimFrame(highHip, "upper_body", "front");
  assert.strictEqual(highHipEval.ok, false);
  assert.strictEqual(highHipEval.failing, "hip");
  assert(/Lùi camera/.test(highHipEval.message));

  const sharpImg = createSyntheticImageData(80, 60, { baseLum: 130, edgeContrast: 20 });
  const blockedEval = cq.evaluateClientFrameQuality({
    imageData: sharpImg,
    feedback: { ready: true, message: "OK", landmarks: highHip },
    previousLandmarks: highHip,
  });
  assert.strictEqual(blockedEval.ok, false, "A frame outside the aiming bands must block the countdown");
  assert.strictEqual(blockedEval.issue, "aim_frame_off");
  assert.strictEqual(blockedEval.aim.failing, "hip");
  pass("Too little torso in frame blocks the countdown with 'aim_frame_off' and names the hip marker");

  // Head cropped at the top edge -> crown band fails
  const croppedHead = createLandmarks({ shoulderY: 0.16 }); // nose .04 -> crown estimate < 0
  const croppedEval = cq.evaluateAimFrame(croppedHead, "upper_body", "front");
  assert.strictEqual(croppedEval.ok, false);
  assert.strictEqual(croppedEval.failing, "head");
  assert(/Đỉnh đầu/.test(croppedEval.message));
  pass("Cropped crown is rejected on the head marker with specific Vietnamese guidance");

  // Standing to one side of the frame -> x band fails
  const offCentre = createLandmarks({ offsetX: 0.4 });
  const offCentreEval = cq.evaluateAimFrame(offCentre, "upper_body", "front");
  assert.strictEqual(offCentreEval.ok, false);
  assert.strictEqual(offCentreEval.message, "Đứng vào giữa khung ngắm.");
  pass("Anchors outside the horizontal band are rejected with a centring instruction");

  // Tilted shoulders in the front view -> shoulder marker fails
  const tilted = createLandmarks();
  tilted[11] = [0.42, 0.4, 0.92]; // .12 vs torso .30 (> 0.2 * .30)
  const tiltedEval = cq.evaluateAimFrame(tilted, "upper_body", "front");
  assert.strictEqual(tiltedEval.ok, false);
  assert.strictEqual(tiltedEval.failing, "shoulder");
  assert(/hai vai ngang/.test(tiltedEval.message));
  pass("Tilted front-view shoulders are rejected on the shoulder marker");

  // The aiming frame must not pre-empt the cross-view drift diagnosis on the side photo
  const sideTilted = createLandmarks({ shoulderY: 0.43, hipY: 0.73 });
  const driftEval = cq.evaluateClientFrameQuality({
    imageData: sharpImg,
    feedback: { ready: true, message: "OK", landmarks: sideTilted },
    frontLandmarks: base,
    view: "side",
    mode: "upper_body",
  });
  assert.strictEqual(driftEval.issue, "cross_view_drift");
  pass("Aiming frame runs after the cross-view check, so distance drift keeps its own diagnosis");
}

function main() {
  testThresholdsAndQualityGates();
  testBestFrameSelection();
  testCountdownCancellation();
  testGeometryPreservation();
  testHardwareErrorsAndComponentIntegration();
  testAimFrame();
  console.log(`\nALL ${passedCount} CAPTURE QUALITY VERIFICATION CHECKS PASSED.`);
}

main();
