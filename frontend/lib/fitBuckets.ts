/**
 * Try-on fit buckets (UI only).
 *
 * The measurement API keeps its own provisional verdicts (tight/snug/regular/
 * loose). The try-on screen groups the *same* circumference ease into three
 * buckets so the colour map and the legend agree:
 *
 *   chật:  ease < 0 cm
 *   vừa:   0 <= ease <= 2 cm  (áo body)
 *   rộng:  ease > 2 cm
 *   thiếu: no garment measurement for this region
 *
 * Colours differ in lightness as well as hue (dark red / mid green / light
 * blue), so the three states stay distinguishable with colour-vision deficiency.
 * Nothing here recalculates a measurement: ease comes from /api/fit-map.
 */
import type { FitMapResult, FitRegion } from "./fitMap";

export type FitBucket = "tight" | "fit" | "loose" | "unknown";

export const FIT_BUCKETS: Record<
  FitBucket,
  { label: string; color: string; threshold: string; onColor: string }
> = {
  tight: { label: "Chật", color: "#7a2a1e", threshold: "< 0 cm", onColor: "#fdf3f1" },
  fit: { label: "Vừa", color: "#3f7d55", threshold: "0 – +2 cm", onColor: "#f1f8f3" },
  loose: { label: "Rộng", color: "#a9cbe0", threshold: "> +2 cm", onColor: "#18323f" },
  unknown: { label: "Thiếu dữ liệu", color: "#8b9188", threshold: "không có số đo áo", onColor: "#ffffff" },
};

export const FIT_UNKNOWN_COLOR = FIT_BUCKETS.unknown.color;

export function bucketForEase(ease: number | null | undefined): FitBucket {
  if (typeof ease !== "number" || !Number.isFinite(ease)) return "unknown";
  if (ease < 0) return "tight";
  if (ease <= 2) return "fit";
  return "loose";
}

export type BucketRegion = {
  key: string;
  label: string;
  bucket: FitBucket;
  ease_cm: number | null;
  body_cm?: number;
  garment_cm?: number;
  from: number;
  to: number;
  status: string;
};

const REGION_LABEL: Record<string, string> = {
  chest_cm: "Vòng ngực",
  waist_cm: "Vòng eo",
  hip_cm: "Vòng mông",
};

export function bucketRegions(fit: FitMapResult | null): BucketRegion[] {
  if (!fit) return [];
  return (fit.regions || []).map((region: FitRegion) => {
    const hasValue = typeof region.ease_cm === "number" && Number.isFinite(region.ease_cm);
    const bucket = hasValue && region.status === "estimated"
      ? bucketForEase(region.ease_cm)
      : "unknown";
    return {
      key: region.key,
      label: region.label || REGION_LABEL[region.key] || region.key,
      bucket,
      ease_cm: hasValue ? (region.ease_cm as number) : null,
      body_cm: region.body_cm,
      garment_cm: region.garment_estimate_cm,
      from: region.band?.from ?? 0,
      to: region.band?.to ?? 0,
      status: region.status,
    };
  });
}

/** Human sentence for one region, e.g. "Áo rộng hơn cơ thể 2,9 cm". */
export function easeSentence(region: BucketRegion): string {
  if (region.ease_cm == null) {
    return region.status === "no_garment_data"
      ? "Chưa có số đo áo cho vùng này."
      : "Thiếu số đo cơ thể cho vùng này.";
  }
  const value = Math.abs(region.ease_cm).toFixed(1).replace(".", ",");
  return region.ease_cm < 0
    ? `Áo hẹp hơn cơ thể ${value} cm`
    : `Áo rộng hơn cơ thể ${value} cm`;
}
