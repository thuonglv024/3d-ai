/**
 * Posture frame drawn over the live camera preview.
 * It is deliberately generic (no face or identity cues) and turns gold when
 * the existing pose/quality check reports a usable frame.
 *
 * The aiming frame (U1) adds the three body markers the scan actually needs:
 * crown, shoulder centre and hip centre. The bands are framing guides derived
 * from the mode, and each live marker is drawn from the MediaPipe landmarks the
 * backend returns, so the user can see which marker is outside its band instead
 * of only getting a generic rejection.
 */
import {
  pendingAimFrame,
  type AimAnchorKey,
  type AimFrameEvaluation,
} from "../../lib/captureQuality";

type MarkerState = "idle" | "on" | "off";

export default function PoseGuide({
  upper,
  ready,
  aim,
}: {
  upper: boolean;
  ready: boolean;
  aim?: AimFrameEvaluation | null;
}) {
  const frame = aim ?? pendingAimFrame(upper ? "upper_body" : "full_body");
  const anchorsByKey = new Map(frame.anchors.map((anchor) => [anchor.key, anchor]));

  const stateFor = (key: AimAnchorKey): MarkerState => {
    if (!anchorsByKey.has(key)) return "idle";
    // A frame that fails on another marker should not paint this one red.
    if (frame.ok) return "on";
    return frame.failing === key ? "off" : "on";
  };

  return (
    <>
      <svg
        className={`capture-pose-guide ${ready ? "is-ready" : ""}`}
        viewBox="0 0 300 600"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        {upper ? (
          <>
            <path className="pose-guide-axis" d="M150 40V470" />
            <circle className="pose-guide-silhouette" cx="150" cy="100" r="38" />
            <path
              className="pose-guide-silhouette"
              d="M112 156C100 224 98 300 106 368M188 156C200 224 202 300 194 368"
            />
            <path
              className="pose-guide-silhouette"
              d="M112 156C92 214 90 292 100 372L108 430M188 156C208 214 210 292 200 372L192 430"
            />
          </>
        ) : (
          <>
            <path className="pose-guide-axis" d="M150 28V566" />
            <circle className="pose-guide-silhouette" cx="150" cy="62" r="30" />
            <path
              className="pose-guide-silhouette"
              d="M118 104C96 160 92 226 102 292L112 336L104 470L96 550M182 104C204 160 208 226 198 292L188 336L196 470L204 550"
            />
          </>
        )}
      </svg>

      <div className="capture-aim-frame" aria-hidden="true">
        {frame.zones.map((zone) => {
          const state = stateFor(zone.key);
          return (
            <div
              key={zone.key}
              className={`capture-aim-band is-${state}`}
              data-anchor={zone.key}
              style={{
                top: `${zone.yMin * 100}%`,
                height: `${(zone.yMax - zone.yMin) * 100}%`,
                left: `${zone.xMin * 100}%`,
                width: `${(zone.xMax - zone.xMin) * 100}%`,
              }}
            >
              <span className="capture-aim-band-label">{zone.label}</span>
            </div>
          );
        })}
        {frame.anchors.map((anchor) => (
          <span
            key={anchor.key}
            className={`capture-aim-anchor is-${stateFor(anchor.key)}`}
            data-anchor={anchor.key}
            style={{ left: `${anchor.x * 100}%`, top: `${anchor.y * 100}%` }}
          >
            <i className="capture-aim-dot" />
          </span>
        ))}
      </div>
    </>
  );
}
