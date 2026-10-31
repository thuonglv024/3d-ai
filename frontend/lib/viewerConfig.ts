export const VIEWER_CONFIG = {
  fov: 24,
  frameFill: 0.74,
  shoulderLevel: 0.805,
  hipLevel: 0.534,
  waistLevel: 0.60,
  targetHeight: 1.75,
  offsetY: 0.025,
  rotateSpeed: 0.55,
  dampingFactor: 0.08,
} as const;

// Waist in shoulder-to-hip normalized coordinates (hip=0, shoulder=1).
export const VIEW_CUT_LEVEL =
  (VIEWER_CONFIG.waistLevel - VIEWER_CONFIG.hipLevel) /
  (VIEWER_CONFIG.shoulderLevel - VIEWER_CONFIG.hipLevel);

export type ViewerFrame = {
  cutY: number;
  topY: number;
  targetY: number;
  radius: number;
  height: number;
};

export function frameForBounds(minY: number, maxY: number): ViewerFrame {
  const height = Math.max(maxY - minY, 1e-6);
  const cutY = minY + height * VIEWER_CONFIG.waistLevel;
  const topY = maxY;
  const targetY = (cutY + topY) / 2;
  const segment = Math.max(topY - cutY, 1e-6);
  const halfFov = (VIEWER_CONFIG.fov * Math.PI) / 180 / 2;
  const radius = segment / (2 * Math.tan(halfFov) * VIEWER_CONFIG.frameFill);
  return { cutY, topY, targetY, radius, height };
}

export function defaultFrame(): ViewerFrame {
  return frameForBounds(
    VIEWER_CONFIG.offsetY,
    VIEWER_CONFIG.offsetY + VIEWER_CONFIG.targetHeight,
  );
}
