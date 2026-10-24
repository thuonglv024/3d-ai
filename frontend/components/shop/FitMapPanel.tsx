"use client";

import type { FitMapResult, FitVerdict } from "../../lib/fitMap";

const LEGEND: { key: FitVerdict; label: string; color: string }[] = [
  { key: "tight", label: "Chật", color: "#b23a2f" },
  { key: "snug", label: "Sát", color: "#c8851c" },
  { key: "regular", label: "Vừa", color: "#2f7a4f" },
  { key: "loose", label: "Rộng", color: "#2f6591" },
];

// The bar spans -8..+20 cm of circumference ease, which covers tight knits to
// oversized wovens without clipping the interesting range.
const EASE_MIN = -8;
const EASE_SPAN = 28;

function markerPercent(ease: number) {
  return Math.max(2, Math.min(98, ((ease - EASE_MIN) / EASE_SPAN) * 100));
}

export default function FitMapPanel({
  fit,
  size,
  sizes,
  onSelectSize,
  loading,
  error,
}: {
  fit: FitMapResult | null;
  size: string;
  sizes: string[];
  onSelectSize: (size: string) => void;
  loading: boolean;
  error: string;
}) {
  return (
    <section className="fit-map-panel" aria-label="Bản đồ độ vừa theo vùng cơ thể">
      <div className="fit-map-head">
        <div>
          <h3>Bản đồ độ vừa</h3>
          <p>
            {fit?.confidence === "published_garment_spec"
              ? "So sánh số đo cơ thể với số đo may trải phẳng đã công bố của hãng cho size này."
              : "So sánh số đo cơ thể với khoảng số đo của size trên mô hình 3D. Đây là ước lượng, chưa phải số đo may trải phẳng."}
          </p>
        </div>
        {fit && (
          <span className="fit-map-overall" style={{ borderColor: fit.overall.color, color: fit.overall.color }}>
            {fit.overall.label}
          </span>
        )}
      </div>

      <div className="fit-map-size-chips" role="group" aria-label="Chọn size để xem độ vừa">
        {sizes.map((s) => (
          <button
            key={s}
            type="button"
            aria-pressed={s === size}
            className={s === size ? "selected" : ""}
            onClick={() => onSelectSize(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {error ? (
        <p className="fit-map-error" role="alert">
          {error}
        </p>
      ) : loading ? (
        <p className="fit-map-loading">Đang tính độ vừa cho size {size}…</p>
      ) : fit ? (
        <div className="fit-map-rows">
          {fit.regions.map((region) => (
            <div className="fit-map-row" key={region.key}>
              <div className="fit-map-row-top">
                <strong>{region.label}</strong>
                <span className="fit-map-verdict" style={{ color: region.color }}>
                  {region.verdict === "unknown" ? "Chưa đủ số đo" : region.label_text || region.verdict}
                </span>
              </div>
              <div className="fit-map-bar" aria-hidden="true">
                {(() => {
                  const percent = (v: number) =>
                    Math.max(0, Math.min(100, ((v - EASE_MIN) / EASE_SPAN) * 100));
                  const tightEnd = fit.stretch ? -5 : 0;
                  const snugEnd = fit.stretch ? 0 : 2;
                  const zones = [
                    { cls: "tight", width: percent(tightEnd) - percent(EASE_MIN) },
                    { cls: "snug", width: percent(snugEnd) - percent(tightEnd) },
                    { cls: "regular", width: percent(10) - percent(snugEnd) },
                    { cls: "loose", width: percent(20) - percent(10) },
                  ];
                  return zones.map((zone) => (
                    <span
                      key={zone.cls}
                      className={`fit-map-zone ${zone.cls}`}
                      style={{ width: `${Math.max(zone.width, 0)}%` }}
                    />
                  ));
                })()}
                {typeof region.ease_cm === "number" && (
                  <i className="fit-map-marker" style={{ left: `${markerPercent(region.ease_cm)}%` }} />
                )}
              </div>
              <div className="fit-map-row-values">
                {typeof region.body_cm === "number" ? (
                  <>
                    <span>
                      Cơ thể <strong>{region.body_cm} cm</strong>
                    </span>
                    <span>
                      Size {fit.size} <strong>{region.range_min_cm}–{region.range_max_cm} cm</strong>
                    </span>
                    <span>
                      {region.basis === "garment_flat_spec" ? "Số đo may" : "Ước tính áo"}{" "}
                      <strong>{region.garment_estimate_cm} cm</strong>
                    </span>
                    {typeof region.clearance_cm === "number" && (
                      <span>
                        Khe hở ~<strong>{region.clearance_cm} cm</strong>
                      </span>
                    )}
                  </>
                ) : (
                  <span>Chưa có số đo vùng này cho sản phẩm.</span>
                )}
              </div>
            </div>
          ))}
          <div className="fit-map-legend" aria-label="Chú thích màu">
            {LEGEND.map((item) => (
              <span key={item.key}>
                <i style={{ background: item.color }} />
                {item.label}
              </span>
            ))}
          </div>
          <p className="fit-map-note">{fit.warnings[0]}</p>
        </div>
      ) : (
        <p className="fit-map-loading">Chọn size để xem bản đồ độ vừa.</p>
      )}
    </section>
  );
}
