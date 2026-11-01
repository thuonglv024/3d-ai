"use client";

import { FIT_BUCKETS, bucketRegions, easeSentence, type BucketRegion, type FitBucket } from "../../lib/fitBuckets";
import type { FitMapResult } from "../../lib/fitMap";

function overallBucket(regions: BucketRegion[]): FitBucket {
  if (regions.some((region) => region.bucket === "tight")) return "tight";
  if (regions.some((region) => region.bucket === "loose")) return "loose";
  if (regions.some((region) => region.bucket === "fit")) return "fit";
  return "unknown";
}

export default function FitBucketPanel({
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
  const regions = bucketRegions(fit);
  const overall = overallBucket(regions);

  return (
    <section className="tryon-fit" aria-label="Độ vừa của size đang chọn">
      <div className="tryon-panel-head">
        <strong>Độ vừa · size {size || "—"}</strong>
        {fit && (
          <span
            className="tryon-bucket"
            style={{ background: FIT_BUCKETS[overall].color, color: FIT_BUCKETS[overall].onColor }}
          >
            {FIT_BUCKETS[overall].label}
          </span>
        )}
      </div>

      <div className="tryon-size-chips" role="group" aria-label="Chọn size để xem độ vừa">
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
        <p className="tryon-fit-error" role="alert">
          {error}
        </p>
      ) : loading ? (
        <p className="tryon-fit-loading">Đang tính độ vừa cho size {size}…</p>
      ) : fit ? (
        <>
          <div className="tryon-fit-rows">
            {regions.map((region) => (
              <div className="tryon-fit-row" key={region.key}>
                <div className="tryon-fit-row-top">
                  <span>{region.label}</span>
                  <em
                    className="tryon-bucket"
                    style={{
                      background: FIT_BUCKETS[region.bucket].color,
                      color: FIT_BUCKETS[region.bucket].onColor,
                    }}
                  >
                    {FIT_BUCKETS[region.bucket].label}
                  </em>
                </div>
                <p>{easeSentence(region)}</p>
                <small>
                  Cơ thể {region.body_cm != null ? `${region.body_cm} cm` : "—"} · Áo{" "}
                  {region.garment_cm != null ? `${region.garment_cm} cm` : "—"}
                </small>
              </div>
            ))}
          </div>

          <ul className="tryon-bucket-legend" aria-label="Chú thích mức độ vừa">
            {(["tight", "fit", "loose", "unknown"] as const).map((key) => (
              <li key={key}>
                <i style={{ background: FIT_BUCKETS[key].color }} aria-hidden="true" />
                <span>{FIT_BUCKETS[key].label}</span>
                <small>{FIT_BUCKETS[key].threshold}</small>
              </li>
            ))}
          </ul>

          <p className="tryon-fit-note">
            {fit.confidence === "published_garment_spec"
              ? "Chu vi áo = 2 × ½ ngực (số đo trải phẳng)."
              : "Chu vi áo ước lượng từ khoảng số đo cơ thể của bảng size, không phải số đo may."}{" "}
            Màu chỉ tô vùng thân áo trên mô hình; tay áo không có số đo nên để xám.
          </p>
        </>
      ) : (
        <p className="tryon-fit-loading">Chọn size để xem độ vừa.</p>
      )}
    </section>
  );
}
