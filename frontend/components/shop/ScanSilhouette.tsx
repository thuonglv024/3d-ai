"use client";

/**
 * Khung ngắm: MỘT silhouette người liền khối (đầu–cổ–vai–tay–thân–mông), kết
 * thúc đúng đáy mông, không có đùi, không có hình lồng nhau.
 *
 * Một path duy nhất được dùng cho cả lỗ mask lẫn viền, nên không thể sinh ra
 * hình thứ hai. Chỉ là hướng dẫn thị giác — không tham gia tính số đo.
 */
export type FrameState = "idle" | "align" | "ready";

const PATH =
  "M50 4 C44.5 4 40 8.5 40 14 C40 18 42 21.5 45 23 L45 26 " +
  "C40 27 34 29 31 32 C28.5 34.5 27.5 39 27.5 44 L27.5 52 " +
  "C27.5 55 29.5 57 31.5 56.5 C33.5 56 34.5 54 34.5 52 L34.5 44 " +
  "C34.5 40 36 37 38 35 L38 44 C38 48 37 52 37 56 " +
  "C37 60 36.5 64 36.5 68 C36.5 71 38 72.5 40 72.5 L60 72.5 " +
  "C62 72.5 63.5 71 63.5 68 C63.5 64 63 60 63 56 " +
  "C63 52 62 48 62 44 L62 35 C64 37 65.5 40 65.5 44 L65.5 52 " +
  "C65.5 54 66.5 56 68.5 56.5 C70.5 57 72.5 55 72.5 52 L72.5 44 " +
  "C72.5 39 71.5 34.5 69 32 C66 29 60 27 55 26 L55 23 " +
  "C58 21.5 60 18 60 14 C60 8.5 55.5 4 50 4 Z";

const ACCENT: Record<FrameState, string> = {
  idle: "#8f8a82",
  align: "#e0a33c",
  ready: "#4f9d6b",
};

export function ScanSilhouette({
  state = "idle",
  dim = 0,
  scale = 1,
}: {
  state?: FrameState;
  dim?: number;
  scale?: number;
}) {
  const accent = ACCENT[state];
  const clamped = Math.min(1.25, Math.max(0.75, scale));
  return (
    <svg
      className="scan-silhouette"
      viewBox="0 0 100 120"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
    >
      <defs>
        <mask id="scan-silhouette-hole">
          <rect x="0" y="0" width="100" height="120" fill="white" />
          <path d={PATH} fill="black" />
        </mask>
      </defs>
      <g transform={`translate(50 60) scale(${clamped}) translate(-50 -60)`}>
        <rect x="0" y="0" width="100" height="120" fill="#0b0b0a" mask="url(#scan-silhouette-hole)" opacity={state === "idle" ? 0 : dim} />
        <path d={PATH} fill={accent} fillOpacity={0.1} stroke={accent} strokeOpacity={0.85} strokeWidth={1.1} strokeLinejoin="round" />
      </g>
    </svg>
  );
}

