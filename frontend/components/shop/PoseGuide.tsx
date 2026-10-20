/**
 * Lightweight posture frame drawn over the live camera preview.
 * It is deliberately generic (no face or identity cues) and turns gold when
 * the existing pose/quality check reports a usable frame.
 */
export default function PoseGuide({
  upper,
  ready,
}: {
  upper: boolean;
  ready: boolean;
}) {
  return (
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
          <line className="pose-guide-band" x1="96" y1="154" x2="204" y2="154" />
          <line className="pose-guide-band" x1="98" y1="308" x2="202" y2="308" />
          <line className="pose-guide-band" x1="100" y1="404" x2="200" y2="404" />
          <text className="pose-guide-label" x="36" y="150">Vai</text>
          <text className="pose-guide-label" x="36" y="304">Eo</text>
          <text className="pose-guide-label" x="36" y="400">Cạp quần</text>
        </>
      ) : (
        <>
          <path className="pose-guide-axis" d="M150 28V566" />
          <circle className="pose-guide-silhouette" cx="150" cy="62" r="30" />
          <path
            className="pose-guide-silhouette"
            d="M118 104C96 160 92 226 102 292L112 336L104 470L96 550M182 104C204 160 208 226 198 292L188 336L196 470L204 550"
          />
          <line className="pose-guide-band" x1="100" y1="112" x2="200" y2="112" />
          <line className="pose-guide-band" x1="96" y1="246" x2="204" y2="246" />
          <line className="pose-guide-band" x1="98" y1="318" x2="202" y2="318" />
          <line className="pose-guide-band" x1="104" y1="548" x2="196" y2="548" />
          <text className="pose-guide-label" x="24" y="108">Vai</text>
          <text className="pose-guide-label" x="24" y="242">Eo</text>
          <text className="pose-guide-label" x="24" y="314">Hông</text>
          <text className="pose-guide-label" x="24" y="544">Bàn chân</text>
        </>
      )}
    </svg>
  );
}
