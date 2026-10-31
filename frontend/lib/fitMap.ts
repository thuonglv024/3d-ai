export type FitVerdict = "tight" | "snug" | "regular" | "loose" | "unknown";

export type FitBand = { from: number; to: number; color: string };

export type FitRegion = {
  key: string;
  label: string;
  status: string;
  body_cm?: number;
  range_min_cm?: number;
  range_max_cm?: number;
  garment_estimate_cm?: number;
  ease_cm?: number;
  clearance_cm?: number;
  verdict: FitVerdict;
  label_text?: string;
  color: string;
  basis?: "size_chart_estimate" | "garment_flat_spec";
  band: FitBand;
};

export type FitMapResult = {
  status: string;
  size: string;
  garment?: string;
  stretch?: boolean;
  baseline_ease_cm?: number;
  regions: FitRegion[];
  overall: { key: FitVerdict; label: string; color: string };
  confidence: string;
  garment_source?: string | null;
  warnings: string[];
  available_sizes?: string[];
};

export async function fetchFitMap(
  productSlug: string,
  size: string,
  measurements: Record<string, number | null | undefined>
): Promise<FitMapResult> {
  const response = await fetch("/api/fit-map", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_slug: productSlug, size, measurements }),
  });
  if (!response.ok) {
    let message = "Chưa tính được bản đồ độ vừa.";
    try {
      const body = await response.json();
      if (body?.detail) message = body.detail;
    } catch {
      /* keep the default message */
    }
    throw new Error(message);
  }
  const body = (await response.json()) as Partial<FitMapResult> | null;
  // A response without regions/overall cannot be rendered; fail here instead of
  // letting FitMapPanel throw during render and take the whole result page down.
  if (!body || !Array.isArray(body.regions) || !body.overall || !Array.isArray(body.warnings)) {
    throw new Error("Phản hồi bản đồ độ vừa không hợp lệ. Hãy thử lại.");
  }
  return body as FitMapResult;
}
