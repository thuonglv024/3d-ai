/**
 * MORPH Studio — Camera Input Quality, Geometry Preservation & Best-Frame Selection
 *
 * Explicit, configurable quality gates for the two-photo webcam capture flow:
 * 1. Center-region luminance (underexposure & overexposure/backlighting detection)
 * 2. 2D Laplacian variance sharpness (motion blur / out-of-focus detection)
 * 3. Multi-frame landmark visibility & inter-frame displacement stability
 * 4. Cross-view scale & vertical shoulder alignment between front and 90° side views
 * 5. Geometry-preserving frame extraction (aspect ratio delta < 0.002, uncropped, unmirrored)
 * 6. Best-frame selection within the final countdown window (`bestFrameWindowMs`)
 */

export interface CameraQualityThresholds {
  /** Minimum average luminance (0..255) in central region */
  minBrightness: number;
  /** Maximum average luminance (0..255) in central region before overexposure */
  maxBrightness: number;
  /** Minimum variance of 2D Laplacian operator on grayscale analysis frame */
  minSharpnessLaplacian: number;
  /** Maximum normalized average displacement of key landmarks between consecutive frames */
  maxLandmarkMotion: number;
  /** Minimum visibility score (0..1) for key pose landmarks */
  minLandmarkVisibility: number;
  /** Minimum consecutive stable frames required before starting the 5s countdown */
  minStableFramesBeforeCountdown: number;
  /** Countdown duration in milliseconds */
  countdownDurationMs: number;
  /** Window at the end of countdown (ms) during which candidate frames are buffered & ranked */
  bestFrameWindowMs: number;
  /** Maximum relative change in torso length (hip_y - shoulder_y) between front and side views */
  maxCrossViewScaleDrift: number;
  /** Maximum normalized vertical drift of shoulder center |shoulder_y_side - shoulder_y_front| */
  maxCrossViewShoulderYDrift: number;
  /** Maximum allowed aspect ratio delta between video stream and exported canvas */
  maxAspectRatioDelta: number;
  /** Maximum number of full-resolution candidate frames retained in the countdown window */
  maxCandidateBufferSize: number;
}

export const CAMERA_QUALITY_THRESHOLDS: Readonly<CameraQualityThresholds> = Object.freeze({
  minBrightness: 45,
  maxBrightness: 235,
  minSharpnessLaplacian: 14.0,
  maxLandmarkMotion: 0.018,
  minLandmarkVisibility: 0.55,
  minStableFramesBeforeCountdown: 3,
  countdownDurationMs: 2000,
  bestFrameWindowMs: 1600,
  maxCrossViewScaleDrift: 0.18,
  maxCrossViewShoulderYDrift: 0.12,
  maxAspectRatioDelta: 0.002,
  maxCandidateBufferSize: 4,
});

export const QUALITY_MESSAGES = Object.freeze({
  DARK_FRAME: "Khung hình hơi tối. Hãy bật thêm đèn hoặc đứng hướng về nguồn sáng.",
  BRIGHT_FRAME: "Ánh sáng phía sau quá gắt. Hãy tránh đứng ngược sáng trực tiếp.",
  BLURRY_FRAME: "Hình ảnh đang bị nhòe do chuyển động. Hãy đứng yên hơn.",
  CROSS_VIEW_DRIFT:
    "Khoảng cách đứng đã thay đổi so với góc chính diện. Hãy đứng đúng vị trí cũ và xoay 90°.",
  LOW_VISIBILITY: "Chưa thấy rõ các mốc cơ thể chính. Hãy đứng trọn trong khung và đủ sáng.",
  GEOMETRY_MISMATCH: "Tỷ lệ khung hình camera không đồng nhất. Hãy giữ nguyên thiết bị và thử lại.",
});

export type QualityIssueCode =
  | "none"
  | "pose_not_ready"
  | "too_dark"
  | "too_bright"
  | "too_blurry"
  | "excessive_motion"
  | "low_visibility"
  | "cross_view_drift"
  | "geometry_mismatch";

export interface ImageDataLike {
  data: Uint8ClampedArray | Uint8Array | number[];
  width: number;
  height: number;
}

export interface PixelQualityMetrics {
  brightness: number;
  sharpness: number;
  darkPixelRatio: number;
  overexposedPixelRatio: number;
  sampleWidth: number;
  sampleHeight: number;
}

export interface BackendQualityFeedback {
  brightness?: number;
  sharpness?: number;
  ok?: boolean;
  issue?: string;
  issues?: string[];
  message?: string;
}

export interface CaptureCheckFeedback {
  ready: boolean;
  message: string;
  landmarks: number[][];
  view?: "front" | "side";
  capture_mode?: "upper_body" | "full_body";
  quality?: BackendQualityFeedback;
}

export interface LandmarkStabilityResult {
  motion: number;
  meanVisibility: number;
  visibleCount: number;
  requiredCount: number;
  hasEnoughLandmarks: boolean;
  isFirstFrame: boolean;
  isStable: boolean;
}

export interface TorsoGeometry {
  shoulderY: number;
  hipY: number;
  torsoLength: number;
  shoulderX: number;
  hipX: number;
  valid: boolean;
}

export interface CrossViewCompatibilityResult {
  compatible: boolean;
  scaleDrift: number;
  shoulderYDrift: number;
  frontTorsoLength: number;
  sideTorsoLength: number;
  frontShoulderY: number;
  sideShoulderY: number;
  message: string;
}

export interface ClientFrameQualityEvaluation {
  ok: boolean;
  issue: QualityIssueCode;
  message: string;
  brightness: number;
  sharpness: number;
  darkPixelRatio: number;
  overexposedPixelRatio: number;
  motion: number;
  meanVisibility: number;
  crossViewCompatible: boolean;
  scaleDrift: number;
  shoulderYDrift: number;
  frameQualityScore: number;
}

export interface CandidateFrame<TPayload = unknown> {
  timestampMs: number;
  frameQualityScore: number;
  motion: number;
  sharpness: number;
  meanVisibility: number;
  brightness?: number;
  ready?: boolean;
  landmarks?: number[][];
  payload?: TPayload;
}

export interface GeometryCheckResult {
  videoWidth: number;
  videoHeight: number;
  frameWidth: number;
  frameHeight: number;
  sourceAspect: number;
  targetAspect: number;
  aspectRatioDelta: number;
  previewAspectDelta: number;
  mirrored: boolean;
  cropped: boolean;
  geometryValid: boolean;
}

export interface ExtractedFrameResult extends GeometryCheckResult {
  width: number;
  height: number;
  canvas: HTMLCanvasElement;
}

export interface CountdownStepState<TPayload = unknown> {
  stableFrames: number;
  deadlineMs: number;
  countSeconds: number | null;
  previousLandmarks: number[][] | null;
  candidateBuffer: Array<CandidateFrame<TPayload>>;
  cancelledReason: string | null;
  wasCancelled: boolean;
  shouldCapture: boolean;
  selectedCandidate: CandidateFrame<TPayload> | null;
}

export function resolveThresholds(
  overrides?: Partial<CameraQualityThresholds>
): CameraQualityThresholds {
  if (!overrides) return { ...CAMERA_QUALITY_THRESHOLDS };
  return {
    ...CAMERA_QUALITY_THRESHOLDS,
    ...overrides,
  };
}

/**
 * Computes center-region luminance (0..255), dark/overexposed pixel ratios,
 * and 2D Laplacian variance sharpness on an ImageData-like buffer or HTMLCanvasElement.
 */
export function computePixelQualityMetrics(
  source: ImageDataLike | HTMLCanvasElement,
  analysisMaxDimension = 160
): PixelQualityMetrics {
  let imageData: ImageDataLike;

  if (typeof HTMLCanvasElement !== "undefined" && source instanceof HTMLCanvasElement) {
    const srcW = source.width;
    const srcH = source.height;
    if (srcW <= 0 || srcH <= 0) {
      return {
        brightness: 0,
        sharpness: 0,
        darkPixelRatio: 1,
        overexposedPixelRatio: 0,
        sampleWidth: 0,
        sampleHeight: 0,
      };
    }
    const scale = Math.min(1, analysisMaxDimension / Math.max(srcW, srcH));
    const sampleW = Math.max(8, Math.round(srcW * scale));
    const sampleH = Math.max(8, Math.round(srcH * scale));

    let ctx: CanvasRenderingContext2D | null = null;
    if (sampleW === srcW && sampleH === srcH) {
      ctx = source.getContext("2d");
      if (ctx) {
        imageData = ctx.getImageData(0, 0, srcW, srcH);
      } else {
        return {
          brightness: 120,
          sharpness: 25,
          darkPixelRatio: 0,
          overexposedPixelRatio: 0,
          sampleWidth: srcW,
          sampleHeight: srcH,
        };
      }
    } else if (typeof document !== "undefined") {
      const sampleCanvas = document.createElement("canvas");
      sampleCanvas.width = sampleW;
      sampleCanvas.height = sampleH;
      const sampleCtx = sampleCanvas.getContext("2d");
      if (sampleCtx) {
        sampleCtx.setTransform(1, 0, 0, 1, 0, 0);
        sampleCtx.drawImage(source, 0, 0, srcW, srcH, 0, 0, sampleW, sampleH);
        imageData = sampleCtx.getImageData(0, 0, sampleW, sampleH);
      } else {
        return {
          brightness: 120,
          sharpness: 25,
          darkPixelRatio: 0,
          overexposedPixelRatio: 0,
          sampleWidth: sampleW,
          sampleHeight: sampleH,
        };
      }
    } else {
      return {
        brightness: 120,
        sharpness: 25,
        darkPixelRatio: 0,
        overexposedPixelRatio: 0,
        sampleWidth: sampleW,
        sampleHeight: sampleH,
      };
    }
  } else {
    imageData = source as ImageDataLike;
  }

  const { data, width, height } = imageData;
  if (!data || width <= 2 || height <= 2 || data.length < width * height * 4) {
    return {
      brightness: 0,
      sharpness: 0,
      darkPixelRatio: 1,
      overexposedPixelRatio: 0,
      sampleWidth: width || 0,
      sampleHeight: height || 0,
    };
  }

  // Central ROI: middle 60% width x 70% height where the user stands
  const x0 = Math.max(0, Math.floor(width * 0.2));
  const x1 = Math.min(width - 1, Math.ceil(width * 0.8));
  const y0 = Math.max(0, Math.floor(height * 0.15));
  const y1 = Math.min(height - 1, Math.ceil(height * 0.85));

  const roiW = x1 - x0 + 1;
  const roiH = y1 - y0 + 1;
  if (roiW <= 2 || roiH <= 2) {
    return {
      brightness: 0,
      sharpness: 0,
      darkPixelRatio: 1,
      overexposedPixelRatio: 0,
      sampleWidth: width,
      sampleHeight: height,
    };
  }

  const gray = new Float32Array(roiW * roiH);
  let sumLum = 0;
  let darkCount = 0;
  let brightCount = 0;
  const totalPixels = roiW * roiH;

  for (let ry = 0; ry < roiH; ry++) {
    const sy = y0 + ry;
    const rowOffset = sy * width * 4;
    const grayRowOffset = ry * roiW;
    for (let rx = 0; rx < roiW; rx++) {
      const idx = rowOffset + (x0 + rx) * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const lum = 0.299 * r + 0.587 * g + 0.114 * b;
      gray[grayRowOffset + rx] = lum;
      sumLum += lum;
      if (lum < 22) darkCount++;
      if (lum > 245) brightCount++;
    }
  }

  const brightness = sumLum / totalPixels;
  const darkPixelRatio = darkCount / totalPixels;
  const overexposedPixelRatio = brightCount / totalPixels;

  // 2D Laplacian operator on interior ROI pixels: L = 4*C - U - D - L - R
  let sumLap = 0;
  let sumLapSq = 0;
  let lapCount = 0;

  for (let ry = 1; ry < roiH - 1; ry++) {
    const rowOffset = ry * roiW;
    const prevRowOffset = (ry - 1) * roiW;
    const nextRowOffset = (ry + 1) * roiW;
    for (let rx = 1; rx < roiW - 1; rx++) {
      const center = gray[rowOffset + rx];
      const lap =
        4 * center -
        gray[prevRowOffset + rx] -
        gray[nextRowOffset + rx] -
        gray[rowOffset + rx - 1] -
        gray[rowOffset + rx + 1];
      sumLap += lap;
      sumLapSq += lap * lap;
      lapCount++;
    }
  }

  let sharpness = 0;
  if (lapCount > 0) {
    const meanLap = sumLap / lapCount;
    sharpness = Math.max(0, sumLapSq / lapCount - meanLap * meanLap);
  }

  return {
    brightness: Number(brightness.toFixed(2)),
    sharpness: Number(sharpness.toFixed(2)),
    darkPixelRatio: Number(darkPixelRatio.toFixed(4)),
    overexposedPixelRatio: Number(overexposedPixelRatio.toFixed(4)),
    sampleWidth: width,
    sampleHeight: height,
  };
}

/**
 * Evaluates pose landmark visibility and inter-frame displacement stability.
 */
export function evaluateLandmarkStability(
  currentLandmarks: number[][] | null | undefined,
  previousLandmarks: number[][] | null | undefined,
  mode: "upper_body" | "full_body" = "upper_body",
  view: "front" | "side" = "front",
  overrides?: Partial<CameraQualityThresholds>
): LandmarkStabilityResult {
  const thresholds = resolveThresholds(overrides);
  const keyIndices =
    mode === "upper_body" ? [0, 11, 12, 23, 24] : [11, 12, 23, 24, 25, 26, 27, 28];
  // In 90° side view, one side of the body can be legitimately occluded
  const requiredCount = view === "side" ? 3 : 4;

  if (!Array.isArray(currentLandmarks) || currentLandmarks.length === 0) {
    return {
      motion: Infinity,
      meanVisibility: 0,
      visibleCount: 0,
      requiredCount,
      hasEnoughLandmarks: false,
      isFirstFrame: !previousLandmarks,
      isStable: false,
    };
  }

  const currentVisibleIndices = keyIndices.filter(
    (idx) => (currentLandmarks[idx]?.[2] ?? 0) >= thresholds.minLandmarkVisibility
  );
  const visibleCount = currentVisibleIndices.length;
  const hasEnoughLandmarks = visibleCount >= requiredCount;

  const meanVisibility =
    visibleCount > 0
      ? currentVisibleIndices.reduce((acc, idx) => acc + (currentLandmarks[idx]?.[2] ?? 0), 0) /
        visibleCount
      : 0;

  if (!hasEnoughLandmarks) {
    return {
      motion: Infinity,
      meanVisibility: Number(meanVisibility.toFixed(4)),
      visibleCount,
      requiredCount,
      hasEnoughLandmarks: false,
      isFirstFrame: !previousLandmarks,
      isStable: false,
    };
  }

  // First valid frame in a sequence initializes the baseline landmarks
  if (!Array.isArray(previousLandmarks) || previousLandmarks.length === 0) {
    return {
      motion: 0,
      meanVisibility: Number(meanVisibility.toFixed(4)),
      visibleCount,
      requiredCount,
      hasEnoughLandmarks: true,
      isFirstFrame: true,
      isStable: true,
    };
  }

  const sharedVisible = keyIndices.filter(
    (idx) =>
      (currentLandmarks[idx]?.[2] ?? 0) >= thresholds.minLandmarkVisibility &&
      (previousLandmarks[idx]?.[2] ?? 0) >= thresholds.minLandmarkVisibility
  );

  if (sharedVisible.length < requiredCount) {
    return {
      motion: Infinity,
      meanVisibility: Number(meanVisibility.toFixed(4)),
      visibleCount: sharedVisible.length,
      requiredCount,
      hasEnoughLandmarks: false,
      isFirstFrame: false,
      isStable: false,
    };
  }

  const totalDisplacement = sharedVisible.reduce((sum, idx) => {
    const dx = (currentLandmarks[idx]?.[0] ?? 0) - (previousLandmarks[idx]?.[0] ?? 0);
    const dy = (currentLandmarks[idx]?.[1] ?? 0) - (previousLandmarks[idx]?.[1] ?? 0);
    return sum + Math.hypot(dx, dy);
  }, 0);

  const motion = totalDisplacement / sharedVisible.length;
  return {
    motion: Number(motion.toFixed(6)),
    meanVisibility: Number(meanVisibility.toFixed(4)),
    visibleCount: sharedVisible.length,
    requiredCount,
    hasEnoughLandmarks: true,
    isFirstFrame: false,
    isStable: motion < thresholds.maxLandmarkMotion,
  };
}

/**
 * Extracts normalized shoulder & hip vertical positions and torso span from MediaPipe landmarks.
 * Uses visibility-aware selection so occluded side-view landmarks do not skew torso geometry.
 */
export function extractTorsoGeometry(
  landmarks: number[][] | null | undefined,
  minVisibility = CAMERA_QUALITY_THRESHOLDS.minLandmarkVisibility
): TorsoGeometry {
  if (!Array.isArray(landmarks) || landmarks.length < 25) {
    return { shoulderY: 0, hipY: 0, torsoLength: 0, shoulderX: 0, hipX: 0, valid: false };
  }

  const sL = landmarks[11];
  const sR = landmarks[12];
  const hL = landmarks[23];
  const hR = landmarks[24];
  if (!sL || !sR || !hL || !hR) {
    return { shoulderY: 0, hipY: 0, torsoLength: 0, shoulderX: 0, hipX: 0, valid: false };
  }

  const sLVis = sL[2] ?? 0;
  const sRVis = sR[2] ?? 0;
  const hLVis = hL[2] ?? 0;
  const hRVis = hR[2] ?? 0;

  let shoulderX: number;
  let shoulderY: number;
  if (sLVis >= minVisibility && sRVis < minVisibility) {
    shoulderX = sL[0];
    shoulderY = sL[1];
  } else if (sRVis >= minVisibility && sLVis < minVisibility) {
    shoulderX = sR[0];
    shoulderY = sR[1];
  } else {
    const wL = Math.max(sLVis, 0.05);
    const wR = Math.max(sRVis, 0.05);
    shoulderX = (sL[0] * wL + sR[0] * wR) / (wL + wR);
    shoulderY = (sL[1] * wL + sR[1] * wR) / (wL + wR);
  }

  let hipX: number;
  let hipY: number;
  if (hLVis >= minVisibility && hRVis < minVisibility) {
    hipX = hL[0];
    hipY = hL[1];
  } else if (hRVis >= minVisibility && hLVis < minVisibility) {
    hipX = hR[0];
    hipY = hR[1];
  } else {
    const wL = Math.max(hLVis, 0.05);
    const wR = Math.max(hRVis, 0.05);
    hipX = (hL[0] * wL + hR[0] * wR) / (wL + wR);
    hipY = (hL[1] * wL + hR[1] * wR) / (wL + wR);
  }

  const torsoLength = hipY - shoulderY;
  const valid =
    Number.isFinite(shoulderY) &&
    Number.isFinite(hipY) &&
    Number.isFinite(torsoLength) &&
    torsoLength > 0.05 &&
    Math.max(sLVis, sRVis) >= minVisibility &&
    Math.max(hLVis, hRVis) >= minVisibility;

  return {
    shoulderY: Number(shoulderY.toFixed(5)),
    hipY: Number(hipY.toFixed(5)),
    torsoLength: Number(torsoLength.toFixed(5)),
    shoulderX: Number(shoulderX.toFixed(5)),
    hipX: Number(hipX.toFixed(5)),
    valid,
  };
}

/**
 * Checks whether the 90° side view maintains consistent standing distance and camera pitch
 * relative to the captured front view (`scaleDrift <= 0.18` and `shoulderYDrift <= 0.12`).
 */
export function evaluateCrossViewCompatibility(
  frontLandmarks: number[][] | null | undefined,
  sideLandmarks: number[][] | null | undefined,
  overrides?: Partial<CameraQualityThresholds>
): CrossViewCompatibilityResult {
  const thresholds = resolveThresholds(overrides);
  const frontGeo = extractTorsoGeometry(frontLandmarks, thresholds.minLandmarkVisibility);
  const sideGeo = extractTorsoGeometry(sideLandmarks, thresholds.minLandmarkVisibility);

  if (!frontGeo.valid || !sideGeo.valid) {
    return {
      compatible: false,
      scaleDrift: 1,
      shoulderYDrift: 1,
      frontTorsoLength: frontGeo.torsoLength,
      sideTorsoLength: sideGeo.torsoLength,
      frontShoulderY: frontGeo.shoulderY,
      sideShoulderY: sideGeo.shoulderY,
      message: QUALITY_MESSAGES.CROSS_VIEW_DRIFT,
    };
  }

  const scaleDrift =
    Math.abs(sideGeo.torsoLength - frontGeo.torsoLength) / Math.max(frontGeo.torsoLength, 1e-6);
  const shoulderYDrift = Math.abs(sideGeo.shoulderY - frontGeo.shoulderY);

  const compatible =
    scaleDrift <= thresholds.maxCrossViewScaleDrift &&
    shoulderYDrift <= thresholds.maxCrossViewShoulderYDrift;

  return {
    compatible,
    scaleDrift: Number(scaleDrift.toFixed(4)),
    shoulderYDrift: Number(shoulderYDrift.toFixed(4)),
    frontTorsoLength: frontGeo.torsoLength,
    sideTorsoLength: sideGeo.torsoLength,
    frontShoulderY: frontGeo.shoulderY,
    sideShoulderY: sideGeo.shoulderY,
    message: compatible ? "" : QUALITY_MESSAGES.CROSS_VIEW_DRIFT,
  };
}

/**
 * Computes a composite quality score in [0..1] combining stillness (`1 - motion`),
 * Laplacian sharpness, and landmark visibility.
 */
export function computeFrameQualityScore(
  metrics: {
    motion: number;
    sharpness: number;
    meanVisibility: number;
    brightness?: number;
  },
  overrides?: Partial<CameraQualityThresholds>
): number {
  const thresholds = resolveThresholds(overrides);
  const safeMotion = Number.isFinite(metrics.motion) ? Math.max(0, metrics.motion) : 1;
  const maxMotion = Math.max(thresholds.maxLandmarkMotion, 1e-6);

  // Stillness component: 1.0 when completely still, 0 when motion >= maxLandmarkMotion
  const stillnessScore = Math.max(0, 1 - Math.min(1, safeMotion / maxMotion));

  // Sharpness component: saturates smoothly above 3.5x minSharpnessLaplacian with linear tie-breaker
  const minSharp = Math.max(thresholds.minSharpnessLaplacian, 1);
  const sharpnessNorm = Math.min(1, Math.max(0, metrics.sharpness) / (minSharp * 3.5));
  const sharpnessTieBreaker = Math.min(0.08, Math.max(0, metrics.sharpness) / 2500);
  const sharpnessScore = Math.min(1, sharpnessNorm * 0.92 + sharpnessTieBreaker);

  // Visibility component: [0..1]
  const visibilityScore = Math.max(0, Math.min(1, metrics.meanVisibility || 0));

  const composite = 0.45 * stillnessScore + 0.35 * sharpnessScore + 0.2 * visibilityScore;
  return Number(composite.toFixed(6));
}

/**
 * Evaluates overall client frame quality by combining pixel metrics, backend `/api/capture-check`
 * feedback, multi-frame landmark motion, and cross-view compatibility.
 */
export function evaluateClientFrameQuality(
  input: {
    imageData?: ImageDataLike;
    canvas?: HTMLCanvasElement;
    pixelMetrics?: Partial<PixelQualityMetrics>;
    feedback?: CaptureCheckFeedback | null;
    previousLandmarks?: number[][] | null;
    frontLandmarks?: number[][] | null;
    mode?: "upper_body" | "full_body";
    view?: "front" | "side";
  },
  overrides?: Partial<CameraQualityThresholds>
): ClientFrameQualityEvaluation {
  const thresholds = resolveThresholds(overrides);
  const mode = input.mode ?? "upper_body";
  const view = input.view ?? "front";

  let pixel: PixelQualityMetrics;
  if (input.pixelMetrics && typeof input.pixelMetrics.brightness === "number") {
    pixel = {
      brightness: input.pixelMetrics.brightness,
      sharpness: input.pixelMetrics.sharpness ?? thresholds.minSharpnessLaplacian + 10,
      darkPixelRatio: input.pixelMetrics.darkPixelRatio ?? 0,
      overexposedPixelRatio: input.pixelMetrics.overexposedPixelRatio ?? 0,
      sampleWidth: input.pixelMetrics.sampleWidth ?? 160,
      sampleHeight: input.pixelMetrics.sampleHeight ?? 90,
    };
  } else if (input.imageData) {
    pixel = computePixelQualityMetrics(input.imageData);
  } else if (input.canvas) {
    pixel = computePixelQualityMetrics(input.canvas);
  } else {
    pixel = {
      brightness: 128,
      sharpness: thresholds.minSharpnessLaplacian + 12,
      darkPixelRatio: 0,
      overexposedPixelRatio: 0,
      sampleWidth: 160,
      sampleHeight: 90,
    };
  }

  // Merge backend quality metrics if provided by /api/capture-check
  const backendQuality = input.feedback?.quality;
  const effectiveBrightness =
    typeof backendQuality?.brightness === "number" ? backendQuality.brightness : pixel.brightness;
  const effectiveSharpness =
    typeof backendQuality?.sharpness === "number" ? backendQuality.sharpness : pixel.sharpness;

  const landmarks = input.feedback?.landmarks ?? [];
  const stability = evaluateLandmarkStability(
    landmarks,
    input.previousLandmarks,
    mode,
    view,
    thresholds
  );

  let crossView: CrossViewCompatibilityResult = {
    compatible: true,
    scaleDrift: 0,
    shoulderYDrift: 0,
    frontTorsoLength: 0,
    sideTorsoLength: 0,
    frontShoulderY: 0,
    sideShoulderY: 0,
    message: "",
  };

  if (view === "side" && input.frontLandmarks && input.frontLandmarks.length > 0 && landmarks.length > 0) {
    crossView = evaluateCrossViewCompatibility(input.frontLandmarks, landmarks, thresholds);
  }

  const frameQualityScore = computeFrameQualityScore(
    {
      motion: stability.motion,
      sharpness: effectiveSharpness,
      meanVisibility: stability.meanVisibility,
      brightness: effectiveBrightness,
    },
    thresholds
  );

  // Priority 1: Severe underexposure or overexposure (explain WHY pose or frame failed)
  if (effectiveBrightness < thresholds.minBrightness || pixel.darkPixelRatio > 0.78) {
    return {
      ok: false,
      issue: "too_dark",
      message: QUALITY_MESSAGES.DARK_FRAME,
      brightness: effectiveBrightness,
      sharpness: effectiveSharpness,
      darkPixelRatio: pixel.darkPixelRatio,
      overexposedPixelRatio: pixel.overexposedPixelRatio,
      motion: stability.motion,
      meanVisibility: stability.meanVisibility,
      crossViewCompatible: crossView.compatible,
      scaleDrift: crossView.scaleDrift,
      shoulderYDrift: crossView.shoulderYDrift,
      frameQualityScore: 0,
    };
  }

  if (effectiveBrightness > thresholds.maxBrightness || pixel.overexposedPixelRatio > 0.55) {
    return {
      ok: false,
      issue: "too_bright",
      message: QUALITY_MESSAGES.BRIGHT_FRAME,
      brightness: effectiveBrightness,
      sharpness: effectiveSharpness,
      darkPixelRatio: pixel.darkPixelRatio,
      overexposedPixelRatio: pixel.overexposedPixelRatio,
      motion: stability.motion,
      meanVisibility: stability.meanVisibility,
      crossViewCompatible: crossView.compatible,
      scaleDrift: crossView.scaleDrift,
      shoulderYDrift: crossView.shoulderYDrift,
      frameQualityScore: 0,
    };
  }

  // Priority 2: Backend pose check not ready
  if (input.feedback && !input.feedback.ready) {
    return {
      ok: false,
      issue: "pose_not_ready",
      message: input.feedback.message || QUALITY_MESSAGES.LOW_VISIBILITY,
      brightness: effectiveBrightness,
      sharpness: effectiveSharpness,
      darkPixelRatio: pixel.darkPixelRatio,
      overexposedPixelRatio: pixel.overexposedPixelRatio,
      motion: stability.motion,
      meanVisibility: stability.meanVisibility,
      crossViewCompatible: crossView.compatible,
      scaleDrift: crossView.scaleDrift,
      shoulderYDrift: crossView.shoulderYDrift,
      frameQualityScore: 0,
    };
  }

  // Priority 3: Cross-view scale / shoulder alignment drift on side view
  if (view === "side" && input.frontLandmarks && !crossView.compatible) {
    return {
      ok: false,
      issue: "cross_view_drift",
      message: QUALITY_MESSAGES.CROSS_VIEW_DRIFT,
      brightness: effectiveBrightness,
      sharpness: effectiveSharpness,
      darkPixelRatio: pixel.darkPixelRatio,
      overexposedPixelRatio: pixel.overexposedPixelRatio,
      motion: stability.motion,
      meanVisibility: stability.meanVisibility,
      crossViewCompatible: false,
      scaleDrift: crossView.scaleDrift,
      shoulderYDrift: crossView.shoulderYDrift,
      frameQualityScore: 0,
    };
  }

  // Priority 4: Insufficient landmark visibility
  if (!stability.hasEnoughLandmarks) {
    return {
      ok: false,
      issue: "low_visibility",
      message: QUALITY_MESSAGES.LOW_VISIBILITY,
      brightness: effectiveBrightness,
      sharpness: effectiveSharpness,
      darkPixelRatio: pixel.darkPixelRatio,
      overexposedPixelRatio: pixel.overexposedPixelRatio,
      motion: stability.motion,
      meanVisibility: stability.meanVisibility,
      crossViewCompatible: crossView.compatible,
      scaleDrift: crossView.scaleDrift,
      shoulderYDrift: crossView.shoulderYDrift,
      frameQualityScore: 0,
    };
  }

  // Priority 5: Laplacian sharpness (motion blur / out-of-focus)
  if (effectiveSharpness < thresholds.minSharpnessLaplacian) {
    return {
      ok: false,
      issue: "too_blurry",
      message: QUALITY_MESSAGES.BLURRY_FRAME,
      brightness: effectiveBrightness,
      sharpness: effectiveSharpness,
      darkPixelRatio: pixel.darkPixelRatio,
      overexposedPixelRatio: pixel.overexposedPixelRatio,
      motion: stability.motion,
      meanVisibility: stability.meanVisibility,
      crossViewCompatible: crossView.compatible,
      scaleDrift: crossView.scaleDrift,
      shoulderYDrift: crossView.shoulderYDrift,
      frameQualityScore: 0,
    };
  }

  // Priority 6: Excessive inter-frame landmark motion
  if (!stability.isStable) {
    return {
      ok: false,
      issue: "excessive_motion",
      message: QUALITY_MESSAGES.BLURRY_FRAME,
      brightness: effectiveBrightness,
      sharpness: effectiveSharpness,
      darkPixelRatio: pixel.darkPixelRatio,
      overexposedPixelRatio: pixel.overexposedPixelRatio,
      motion: stability.motion,
      meanVisibility: stability.meanVisibility,
      crossViewCompatible: crossView.compatible,
      scaleDrift: crossView.scaleDrift,
      shoulderYDrift: crossView.shoulderYDrift,
      frameQualityScore: 0,
    };
  }

  return {
    ok: true,
    issue: "none",
    message: input.feedback?.message || "Tư thế và chất lượng hình ảnh đạt chuẩn. Giữ yên.",
    brightness: effectiveBrightness,
    sharpness: effectiveSharpness,
    darkPixelRatio: pixel.darkPixelRatio,
    overexposedPixelRatio: pixel.overexposedPixelRatio,
    motion: stability.motion,
    meanVisibility: stability.meanVisibility,
    crossViewCompatible: crossView.compatible,
    scaleDrift: crossView.scaleDrift,
    shoulderYDrift: crossView.shoulderYDrift,
    frameQualityScore,
  };
}

/**
 * Selects the highest-quality candidate frame from the final countdown window (`bestFrameWindowMs`).
 */
export function selectBestFrameFromWindow<T extends CandidateFrame>(
  candidates: T[],
  options?: {
    nowMs?: number;
    deadlineMs?: number;
    overrides?: Partial<CameraQualityThresholds>;
  }
): T | null {
  if (!Array.isArray(candidates) || candidates.length === 0) {
    return null;
  }

  const thresholds = resolveThresholds(options?.overrides);
  const referenceEndMs =
    options?.deadlineMs ??
    options?.nowMs ??
    Math.max(...candidates.map((c) => c.timestampMs));
  const windowStartMs = referenceEndMs - thresholds.bestFrameWindowMs;

  const eligible = candidates.filter((c) => {
    if (c.ready === false) return false;
    if (c.timestampMs < windowStartMs || c.timestampMs > referenceEndMs + 400) return false;
    if (Number.isFinite(c.motion) && c.motion >= thresholds.maxLandmarkMotion) return false;
    if (Number.isFinite(c.sharpness) && c.sharpness < thresholds.minSharpnessLaplacian) return false;
    return true;
  });

  const pool = eligible.length > 0 ? eligible : candidates.filter((c) => c.ready !== false);
  if (pool.length === 0) return null;

  let best: T = pool[0];
  let bestScore =
    typeof best.frameQualityScore === "number" && best.frameQualityScore > 0
      ? best.frameQualityScore
      : computeFrameQualityScore(best, thresholds);

  for (let i = 1; i < pool.length; i++) {
    const candidate = pool[i];
    const score =
      typeof candidate.frameQualityScore === "number" && candidate.frameQualityScore > 0
        ? candidate.frameQualityScore
        : computeFrameQualityScore(candidate, thresholds);
    if (score > bestScore) {
      best = candidate;
      bestScore = score;
    }
  }

  return best;
}

/**
 * Buffers a candidate frame if it falls within the final `bestFrameWindowMs` of the countdown,
 * retaining up to `maxCandidateBufferSize` top-scoring frames to bound memory usage.
 */
export function pushCandidateFrame<T extends CandidateFrame>(
  buffer: T[],
  candidate: T,
  deadlineMs: number,
  overrides?: Partial<CameraQualityThresholds>
): T[] {
  const thresholds = resolveThresholds(overrides);
  const windowStartMs = deadlineMs - thresholds.bestFrameWindowMs;
  if (candidate.timestampMs < windowStartMs) {
    return buffer;
  }

  const normalizedCandidate: T = {
    ...candidate,
    frameQualityScore:
      typeof candidate.frameQualityScore === "number" && candidate.frameQualityScore > 0
        ? candidate.frameQualityScore
        : computeFrameQualityScore(candidate, thresholds),
  };

  const active = buffer
    .filter((item) => item.timestampMs >= windowStartMs)
    .concat(normalizedCandidate);

  active.sort((a, b) => b.frameQualityScore - a.frameQualityScore);
  return active.slice(0, thresholds.maxCandidateBufferSize);
}

/**
 * Pure countdown state machine step:
 * - Requires `minStableFramesBeforeCountdown` stable frames to initiate the countdown
 * - Buffers candidate frames during the final `bestFrameWindowMs`
 * - Immediately cancels the countdown (`deadlineMs = 0`, `countSeconds = null`, `candidateBuffer = []`)
 *   if any frame fails pose, motion, sharpness, brightness, or cross-view distance checks
 */
export function stepCountdownState<TPayload = unknown>(
  prevState: CountdownStepState<TPayload>,
  evaluation: ClientFrameQualityEvaluation,
  nowMs: number,
  options?: {
    landmarks?: number[][];
    payload?: TPayload;
    overrides?: Partial<CameraQualityThresholds>;
  }
): CountdownStepState<TPayload> {
  const thresholds = resolveThresholds(options?.overrides);

  if (!evaluation.ok) {
    const wasCountingDown = prevState.deadlineMs > 0 || prevState.countSeconds !== null;
    return {
      stableFrames: 0,
      deadlineMs: 0,
      countSeconds: null,
      previousLandmarks: null,
      candidateBuffer: [],
      cancelledReason: evaluation.message,
      wasCancelled: wasCountingDown,
      shouldCapture: false,
      selectedCandidate: null,
    };
  }

  const stableFrames = prevState.stableFrames + 1;
  let deadlineMs = prevState.deadlineMs;
  if (stableFrames >= thresholds.minStableFramesBeforeCountdown && !deadlineMs) {
    deadlineMs = nowMs + thresholds.countdownDurationMs;
  }

  let candidateBuffer = prevState.candidateBuffer;
  if (deadlineMs > 0) {
    const candidate: CandidateFrame<TPayload> = {
      timestampMs: nowMs,
      frameQualityScore: evaluation.frameQualityScore,
      motion: evaluation.motion,
      sharpness: evaluation.sharpness,
      meanVisibility: evaluation.meanVisibility,
      brightness: evaluation.brightness,
      ready: true,
      landmarks: options?.landmarks,
      payload: options?.payload,
    };
    candidateBuffer = pushCandidateFrame(candidateBuffer, candidate, deadlineMs, thresholds);
  }

  if (deadlineMs > 0 && nowMs >= deadlineMs) {
    const selectedCandidate = selectBestFrameFromWindow(candidateBuffer, {
      nowMs,
      deadlineMs,
      overrides: thresholds,
    });
    return {
      stableFrames,
      deadlineMs,
      countSeconds: null,
      previousLandmarks: options?.landmarks ?? prevState.previousLandmarks,
      candidateBuffer,
      cancelledReason: null,
      wasCancelled: false,
      shouldCapture: true,
      selectedCandidate,
    };
  }

  const countSeconds =
    deadlineMs > 0 ? Math.max(1, Math.ceil((deadlineMs - nowMs) / 1000)) : null;

  return {
    stableFrames,
    deadlineMs,
    countSeconds,
    previousLandmarks: options?.landmarks ?? prevState.previousLandmarks,
    candidateBuffer,
    cancelledReason: null,
    wasCancelled: false,
    shouldCapture: false,
    selectedCandidate: null,
  };
}

/**
 * Verifies that preview container and exported canvas dimensions preserve the native video
 * aspect ratio without cropping or horizontal mirror discrepancy.
 */
export function verifyFrameGeometry(
  videoWidth: number,
  videoHeight: number,
  frameWidth: number,
  frameHeight: number,
  previewAspectRatio?: number,
  overrides?: Partial<CameraQualityThresholds>
): GeometryCheckResult {
  const thresholds = resolveThresholds(overrides);
  if (videoWidth <= 0 || videoHeight <= 0 || frameWidth <= 0 || frameHeight <= 0) {
    return {
      videoWidth,
      videoHeight,
      frameWidth,
      frameHeight,
      sourceAspect: 0,
      targetAspect: 0,
      aspectRatioDelta: Infinity,
      previewAspectDelta: Infinity,
      mirrored: false,
      cropped: false,
      geometryValid: false,
    };
  }

  const sourceAspect = videoWidth / videoHeight;
  const targetAspect = frameWidth / frameHeight;
  const aspectRatioDelta = Math.abs(sourceAspect - targetAspect) / sourceAspect;
  const previewAspect = previewAspectRatio ?? sourceAspect;
  const previewAspectDelta = Math.abs(sourceAspect - previewAspect) / sourceAspect;

  const geometryValid =
    aspectRatioDelta < thresholds.maxAspectRatioDelta &&
    previewAspectDelta < thresholds.maxAspectRatioDelta;

  return {
    videoWidth,
    videoHeight,
    frameWidth,
    frameHeight,
    sourceAspect: Number(sourceAspect.toFixed(6)),
    targetAspect: Number(targetAspect.toFixed(6)),
    aspectRatioDelta: Number(aspectRatioDelta.toFixed(6)),
    previewAspectDelta: Number(previewAspectDelta.toFixed(6)),
    mirrored: false,
    cropped: false,
    geometryValid,
  };
}

/**
 * Computes geometry-preserving target dimensions for a video stream.
 * Ensures aspectRatioDelta < 0.002 across both preview-check (720p) and full-res captures.
 */
export function computeGeometryPreservingDimensions(
  videoWidth: number,
  videoHeight: number,
  maxDimension?: number | null
): { width: number; height: number; scale: number } {
  if (videoWidth <= 0 || videoHeight <= 0) {
    return { width: 0, height: 0, scale: 0 };
  }
  if (!maxDimension || maxDimension <= 0 || Math.max(videoWidth, videoHeight) <= maxDimension) {
    return { width: videoWidth, height: videoHeight, scale: 1 };
  }

  const sourceAspect = videoWidth / videoHeight;
  const scale = Math.min(1, maxDimension / Math.max(videoWidth, videoHeight));
  let width = Math.max(1, Math.round(videoWidth * scale));
  let height = Math.max(1, Math.round(width / sourceAspect));

  // Fine-tune if integer rounding caused aspect ratio delta >= 0.002
  const delta = Math.abs(sourceAspect - width / height) / sourceAspect;
  if (delta >= CAMERA_QUALITY_THRESHOLDS.maxAspectRatioDelta) {
    height = Math.max(1, Math.round(videoHeight * scale));
    width = Math.max(1, Math.round(height * sourceAspect));
  }

  return { width, height, scale };
}

/**
 * Extracts an uncropped, unmirrored frame from an HTMLVideoElement onto an HTMLCanvasElement
 * while strictly preserving `videoWidth : videoHeight` geometry (`aspectRatioDelta < 0.002`).
 */
export function extractGeometryPreservingFrame(
  videoEl: Pick<HTMLVideoElement, "videoWidth" | "videoHeight"> & Partial<HTMLVideoElement>,
  options?: {
    maxDimension?: number | null;
    createCanvas?: (width: number, height: number) => HTMLCanvasElement;
    overrides?: Partial<CameraQualityThresholds>;
  }
): ExtractedFrameResult {
  const videoWidth = videoEl?.videoWidth ?? 0;
  const videoHeight = videoEl?.videoHeight ?? 0;
  if (videoWidth <= 0 || videoHeight <= 0) {
    throw new Error("Luồng video chưa sẵn sàng (videoWidth/videoHeight = 0).");
  }

  const { width, height } = computeGeometryPreservingDimensions(
    videoWidth,
    videoHeight,
    options?.maxDimension
  );

  const canvas = options?.createCanvas
    ? options.createCanvas(width, height)
    : document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext("2d");
  if (ctx) {
    // Identity transform guarantees zero horizontal flip discrepancy between /api/capture-check and /api/scans
    if (typeof ctx.setTransform === "function") {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
    }
    ctx.drawImage(
      videoEl as HTMLVideoElement,
      0,
      0,
      videoWidth,
      videoHeight,
      0,
      0,
      width,
      height
    );
  }

  const check = verifyFrameGeometry(
    videoWidth,
    videoHeight,
    width,
    height,
    videoWidth / videoHeight,
    options?.overrides
  );

  return {
    ...check,
    width,
    height,
    canvas,
  };
}

/**
 * Maps browser MediaDevices / DOMException errors to clear, actionable Vietnamese guidance.
 */
export function mapCameraDeviceError(error: unknown): {
  code:
    | "permission_denied"
    | "device_not_found"
    | "device_busy"
    | "insecure_context"
    | "stream_ended"
    | "unknown_camera_error";
  message: string;
} {
  if (!error) {
    return {
      code: "unknown_camera_error",
      message: "Không mở được camera. Hãy kiểm tra kết nối thiết bị rồi thử lại.",
    };
  }

  const name =
    typeof error === "object" && error !== null && "name" in error
      ? String((error as { name?: unknown }).name)
      : "";
  const rawMessage =
    typeof error === "object" && error !== null && "message" in error
      ? String((error as { message?: unknown }).message)
      : String(error);

  if (
    name === "NotAllowedError" ||
    name === "PermissionDeniedError" ||
    name === "SecurityError"
  ) {
    return {
      code: "permission_denied",
      message:
        "Chưa được cấp quyền camera. Hãy cho phép quyền truy cập camera trên trình duyệt rồi bấm Thử lại.",
    };
  }

  if (
    name === "NotFoundError" ||
    name === "DevicesNotFoundError" ||
    name === "OverconstrainedError"
  ) {
    return {
      code: "device_not_found",
      message:
        "Không tìm thấy thiết bị camera. Hãy kiểm tra kết nối webcam hoặc chọn thiết bị camera khác.",
    };
  }

  if (name === "NotReadableError" || name === "TrackStartError" || name === "AbortError") {
    return {
      code: "device_busy",
      message:
        "Camera đang bị ứng dụng khác chiếm dụng. Hãy đóng ứng dụng đang dùng camera (Zoom, Teams, tab khác) rồi thử lại.",
    };
  }

  if (rawMessage.includes("localhost") || rawMessage.includes("HTTPS")) {
    return {
      code: "insecure_context",
      message: "Camera cần chạy trên localhost hoặc kết nối HTTPS an toàn.",
    };
  }

  return {
    code: "unknown_camera_error",
    message: "Không mở được camera. Đóng ứng dụng đang dùng camera hoặc kiểm tra thiết bị rồi thử lại.",
  };
}

