"use client";

/**
 * Khung ngắm dạng hình người: vùng ngoài silhouette bị làm mờ, người dùng phải
 * đứng khớp vào hình. Chỉ là hướng dẫn thị giác — không tham gia tính số đo.
 *
 * `state` do lớp kiểm tra landmark quyết định:
 *  - "idle": chưa thấy người → không làm mờ, chỉ một dòng mời vào khung
 *  - "align": đã thấy người nhưng lệch khung → silhouette hổ phách
 *  - "ready": khớp → silhouette xanh, cho phép chụp
 */
export type FrameState = "idle" | "align" | "ready";

const PATH =
  "M50 4c-6 0-10 4-10 9s4 9 10 9 10-4 10-9-4-9-10-9z" +
  "M32 24c-4 0-6 3-6 6v18c0 3 1 5 3 6v22c0 4 2 6 5 6v38c0 4 2 6 5 6" +
  "s5-2 5-6V92h2v28c0 4 2 6 5 6s5-2 5-6V82c3-1 5-4 5-8V50c0-3-2-6-6-6" +
  "zM28 28c-3 0-5 2-5 5v20c0 3 3 5 6 5" +
  "M72 28c3 0 5 2 5 5v20c0 3-3 5-6 5";

const ACCENT: Record<FrameState, string> = {
  idle: "#8f8a82",
  align: "#e0a33c",
  ready: "#4f9d6b",
};

export function ScanSilhouette({
  state = "idle",
  dim = 0.4,
}: {
  state?: FrameState;
  dim?: number;
}) {
  const accent = ACCENT[state];
  return (
    <svg
      className="scan-silhouette"
      viewBox="0 0 100 120"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    >
      {/* Lớp mờ: tô kín khung rồi khoét lỗ hình người, nên chỉ thân là sáng. */}
      <defs>
        <mask id="scan-silhouette-hole">
          <rect x="0" y="0" width="100" height="120" fill="white" />
          <path d={PATH} fill="black" />
        </mask>
      </defs>
      <rect
        x="0"
        y="0"
        width="100"
        height="120"
        fill="#0b0b0a"
        mask="url(#scan-silhouette-hole)"
        opacity={state === "idle" ? 0 : dim}
      />
      <path
        d={PATH}
        fill="none"
        stroke={accent}
        strokeWidth={state === "ready" ? 1.6 : 1.1}
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity={state === "idle" ? 0.45 : 0.95}
      />
    </svg>
  );
}
