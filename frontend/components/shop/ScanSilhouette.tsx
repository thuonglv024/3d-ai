"use client";

/**
 * Khung ngắm dạng pictogram: vùng ngoài hình người bị làm mờ, người dùng phải
 * đứng khớp vào hình. Chỉ là hướng dẫn thị giác — không tham gia tính số đo.
 *
 * Hình được ghép từ các khối đơn giản (đầu, thân, tay, chân) thay vì một path
 * phức tạp, vì path cũ vẽ chồng và hiện thành hai silhouette lệch nhau.
 *
 * `state`: "idle" chưa thấy người (không mờ) · "align" lệch khung (hổ phách) ·
 * "ready" khớp (xanh). `scale` co giãn theo tỉ lệ vai–hông, kẹp 0,75–1,25.
 */
export type FrameState = "idle" | "align" | "ready";

const ACCENT: Record<FrameState, string> = {
  idle: "#8f8a82",
  align: "#e0a33c",
  ready: "#4f9d6b",
};

const HEAD = { cx: 50, cy: 15, r: 9 };
const BLOCKS = [
  // Thân kéo xuống hết mông (bottom of the buttocks) — khung quét là MÔNG-up,
  // không phải waist-up: đùi trên nằm ngoài vùng chụp nên không vẽ chân.
  { x: 36, y: 26, w: 28, h: 46, r: 12 }, // thân + mông
  { x: 27, y: 28, w: 7, h: 33, r: 3.5 }, // tay trái
  { x: 66, y: 28, w: 7, h: 33, r: 3.5 }, // tay phải
];

function Blocks({ fill, stroke }: { fill: string; stroke?: string }) {
  return (
    <>
      <circle cx={HEAD.cx} cy={HEAD.cy} r={HEAD.r} fill={fill} stroke={stroke} strokeWidth={stroke ? 1.2 : 0} />
      {BLOCKS.map((b, index) => (
        <rect
          key={index}
          x={b.x}
          y={b.y}
          width={b.w}
          height={b.h}
          rx={b.r}
          fill={fill}
          stroke={stroke}
          strokeWidth={stroke ? 1.2 : 0}
        />
      ))}
    </>
  );
}

export function ScanSilhouette({
  state = "idle",
  dim = 0.4,
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
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
      }}
    >
      <defs>
        <mask id="scan-silhouette-hole">
          <rect x="0" y="0" width="100" height="120" fill="white" />
          <Blocks fill="black" />
        </mask>
      </defs>
      <g transform={`translate(50 60) scale(${clamped}) translate(-50 -60)`}>
        {/* Tô mờ toàn khung rồi khoét lỗ hình người: chỉ thân là sáng. */}
        <rect
          x="0"
          y="0"
          width="100"
          height="120"
          fill="#0b0b0a"
          mask="url(#scan-silhouette-hole)"
          opacity={state === "idle" ? 0 : dim}
        />
        <Blocks fill="none" stroke={accent} />
      </g>
    </svg>
  );
}

