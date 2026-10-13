/**
 * Client API services and utilities for user body scans, history, chart and comparisons.
 * Aligns with MORPH Studio backend endpoints: /api/user/scans and /api/auth.
 */

export interface KeyMeasurements {
  height_cm?: number | null;
  chest_cm?: number | null;
  waist_cm?: number | null;
  hip_cm?: number | null;
  shoulder_width_cm?: number | null;
}

export interface BodyScanSummary {
  id: string;
  source_scan_id?: string | null;
  captured_at: string;
  saved_at: string;
  capture_mode: "upper_body" | "full_body";
  height_input_cm: number;
  engine_version: string;
  note?: string | null;
  key_measurements: KeyMeasurements;
}

export interface BodyMeasurementDetail {
  metric_key: string;
  label: string;
  value_cm: number | null;
  source: "user_input" | "photo_estimate" | "photo_with_prior" | "template_model" | "unavailable" | string;
}

export interface BodyScanDetail {
  id: string;
  source_scan_id?: string | null;
  captured_at: string;
  saved_at: string;
  capture_mode: "upper_body" | "full_body";
  height_input_cm: number;
  engine_version: string;
  measurement_schema_version?: number;
  warnings: string[];
  note?: string | null;
  measurements: BodyMeasurementDetail[];
}

export interface MetricChartPoint {
  value: number | null;
  source: string;
  valid_for_tracking: boolean;
}

export interface ChartTimelinePoint {
  scan_id: string;
  captured_at: string;
  capture_mode: "upper_body" | "full_body";
  engine_version: string;
  metrics: Record<string, MetricChartPoint>;
}

export interface ChartResponse {
  range: "30d" | "90d" | "all";
  disclaimer: string;
  timeline: ChartTimelinePoint[];
}

export interface ComparisonScanMeta {
  id: string;
  captured_at: string;
  capture_mode: "upper_body" | "full_body";
  engine_version: string;
  note?: string | null;
}

export interface ScanComparisonMetric {
  metric_key: string;
  label: string;
  value_a_cm: number | null;
  value_b_cm: number | null;
  delta_cm: number | null;
  source_a: string;
  source_b: string;
  is_comparable: boolean;
  summary_text: string;
}

export interface ScanComparisonResponse {
  scan_a: ComparisonScanMeta;
  scan_b: ComparisonScanMeta;
  compatibility_warnings: string[];
  comparisons: ScanComparisonMetric[];
  disclaimer: string;
}

export interface ScansListResponse {
  items: BodyScanSummary[];
  total: number;
  page: number;
  limit: number;
}

// Vietnamese source label map
export const SOURCE_LABELS: Record<string, string> = {
  user_input: "Bạn nhập",
  photo_estimate: "Ước lượng ảnh",
  photo_with_prior: "Ảnh + tỷ lệ mẫu",
  template_model: "Theo mẫu 3D",
  unavailable: "Không khả dụng",
};

export const SOURCE_DESCRIPTIONS: Record<string, string> = {
  user_input: "Chiều cao do bạn tự nhập trước khi quét ảnh.",
  photo_estimate: "Ước lượng từ đường bao thân hình qua 2 ảnh camera toàn thân.",
  photo_with_prior: "Ước lượng từ ảnh kết hợp tỷ lệ nhân trắc mẫu thân trên.",
  template_model: "Số đo tham chiếu từ mô hình 3D MakeHuman gốc (không phải số đo thực tế của bạn).",
  unavailable: "Không khả dụng ở chế độ chụp này.",
};

export function getSourceLabel(source?: string): string {
  if (!source) return "Không xác định";
  return SOURCE_LABELS[source] || source;
}

export function getModeLabel(mode?: string): string {
  if (mode === "upper_body") return "Thân trên";
  if (mode === "full_body") return "Toàn thân";
  return mode || "Chưa rõ";
}

/**
 * Format timestamp in Vietnamese locale (e.g., 14:30 13/10/2026)
 */
export function formatScanDateTime(dateStr?: string): string {
  if (!dateStr) return "--:-- --/--/----";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${hours}:${minutes} ${day}/${month}/${year}`;
  } catch {
    return dateStr;
  }
}

export function formatScanDate(dateStr?: string): string {
  if (!dateStr) return "--/--/----";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  } catch {
    return dateStr;
  }
}

export function formatScanTime(dateStr?: string): string {
  if (!dateStr) return "--:--";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    return `${hours}:${minutes}`;
  } catch {
    return dateStr;
  }
}

// --- API Calls ---

export async function fetchUserScans(params?: {
  page?: number;
  limit?: number;
  capture_mode?: string;
  from_date?: string;
  to_date?: string;
}): Promise<ScansListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.capture_mode) query.set("capture_mode", params.capture_mode);
  if (params?.from_date) query.set("from_date", params.from_date);
  if (params?.to_date) query.set("to_date", params.to_date);

  const res = await fetch(`/api/user/scans?${query.toString()}`, {
    method: "GET",
    credentials: "include",
  });

  if (!res.ok) {
    if (res.status === 401) {
      throw new Error("UNAUTHORIZED");
    }
    const errData = await res.json().catch(() => null);
    throw new Error(errData?.detail || `Không thể tải lịch sử scan (${res.status})`);
  }

  return res.json();
}

export async function fetchScanDetail(id: string): Promise<BodyScanDetail> {
  const res = await fetch(`/api/user/scans/${encodeURIComponent(id)}`, {
    method: "GET",
    credentials: "include",
  });

  if (!res.ok) {
    if (res.status === 401) throw new Error("UNAUTHORIZED");
    const errData = await res.json().catch(() => null);
    throw new Error(errData?.detail || `Không thể tải chi tiết scan (${res.status})`);
  }

  return res.json();
}

export async function updateScanNote(id: string, note: string): Promise<BodyScanDetail> {
  const res = await fetch(`/api/user/scans/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ note }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => null);
    throw new Error(errData?.detail || "Không thể cập nhật ghi chú");
  }

  return res.json();
}

export async function deleteSavedScan(id: string): Promise<void> {
  const res = await fetch(`/api/user/scans/${encodeURIComponent(id)}`, {
    method: "DELETE",
    credentials: "include",
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => null);
    throw new Error(errData?.detail || "Không thể xóa bản ghi scan");
  }
}

export async function fetchChartData(
  range: "30d" | "90d" | "all" = "30d",
  metrics = "chest_cm,waist_cm,hip_cm,shoulder_width_cm"
): Promise<ChartResponse> {
  const query = new URLSearchParams({ range, metrics });
  const res = await fetch(`/api/user/scans/chart?${query.toString()}`, {
    method: "GET",
    credentials: "include",
  });

  if (!res.ok) {
    if (res.status === 401) throw new Error("UNAUTHORIZED");
    const errData = await res.json().catch(() => null);
    throw new Error(errData?.detail || "Không thể tải dữ liệu biểu đồ");
  }

  return res.json();
}

export async function fetchScanComparison(scanAId: string, scanBId: string): Promise<ScanComparisonResponse> {
  const query = new URLSearchParams({
    scan_a: scanAId,
    scan_b: scanBId,
  });

  const res = await fetch(`/api/user/scans/compare?${query.toString()}`, {
    method: "GET",
    credentials: "include",
  });

  if (!res.ok) {
    if (res.status === 401) throw new Error("UNAUTHORIZED");
    const errData = await res.json().catch(() => null);
    throw new Error(errData?.detail || "Không thể so sánh hai lần scan");
  }

  return res.json();
}
