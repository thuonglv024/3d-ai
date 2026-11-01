/**
 * Explain a chosen size from its measured ease (POST /api/fit/explain).
 * The endpoint never changes the size and always returns 200 with either an AI
 * or a deterministic explanation; the UI labels which one it received.
 */
export type FitExplainBasis = { metric: string; ease_cm: number };

export type FitExplainResult = {
  size: string;
  explanation: string;
  basis: FitExplainBasis[];
  source: "ai" | "fallback";
  fallback_reason?: string | null;
};

export async function fetchFitExplain(
  size: string,
  eases: { chest_cm?: number | null; waist_cm?: number | null },
  garment: { name?: string; fit?: string; material?: string } | null,
  signal?: AbortSignal
): Promise<FitExplainResult> {
  const response = await fetch("/api/fit/explain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ size, eases, garment }),
    signal,
  });
  if (!response.ok) {
    throw new Error("Chưa giải thích được size này.");
  }
  const body = (await response.json()) as Partial<FitExplainResult> | null;
  if (!body || typeof body.explanation !== "string" || !Array.isArray(body.basis)) {
    throw new Error("Phản hồi giải thích không hợp lệ.");
  }
  return body as FitExplainResult;
}

export const EXPLAIN_METRIC_LABEL: Record<string, string> = {
  chest_cm: "Ngực",
  waist_cm: "Eo",
  hip_cm: "Mông",
};
