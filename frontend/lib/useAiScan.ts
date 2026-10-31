"use client";

import { useCallback, useEffect, useState } from "react";

export type AiCaptureMode = "upper_body" | "full_body";

export type AiScanHealth = {
  ready: boolean;
  provider: string;
  model: string;
  message: string;
};

export type AiMeasurementDetail = {
  key: string;
  label: string;
  value_cm: number | null;
  source: "ai_vision_estimate";
  confidence?: number | null;
  support?: number | null;
  estimated_by?: string | null;
};

export type AiEnsembleMember = {
  role: string;
  label: string;
  confidence?: number | null;
  supported_metrics: number;
  error?: string | null;
};

export type AiScanResultData = {
  status: "completed";
  provider: "google-genai";
  model: string;
  capture_mode: AiCaptureMode;
  sex?: "auto" | "female" | "male";
  measurements: {
    height_cm: number;
    chest_cm: number | null;
    waist_cm: number | null;
    hip_cm: number | null;
    shoulder_width_cm: number | null;
    chest_width_cm?: number | null;
    chest_depth_cm?: number | null;
    waist_width_cm?: number | null;
    waist_depth_cm?: number | null;
    hip_width_cm?: number | null;
    hip_depth_cm?: number | null;
  };
  details: AiMeasurementDetail[];
  confidence: number;
  shape_confidence?: number;
  pose_quality: string;
  notes: string;
  warnings: string[];
  elapsed_seconds: number;
  source: "ai_vision_estimate";
  ensemble?: {
    size: number;
    members: AiEnsembleMember[];
    geometric_available: boolean;
  } | null;
  geometric_check?: {
    available: boolean;
    reason: string;
    measurements: Record<string, number | null>;
    warnings: string[];
  } | null;
};

/**
 * One message per failure mode, so the UI never shows a bare status code and
 * never blames the photos for an upstream or quota problem.
 *
 * FastAPI answers request-validation failures with `detail` as a list; every
 * other error path uses a Vietnamese string that we keep as-is.
 */
export function describeAiError(status: number, detail: unknown): string {
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => (item && typeof item === "object" && "msg" in item ? String((item as { msg: unknown }).msg) : String(item)))
      .filter(Boolean);
    const fieldHint = parts.length ? ` (${parts.join("; ")})` : "";
    return `Yêu cầu chưa hợp lệ${fieldHint}. Hãy chọn lại hai ảnh và chiều cao rồi thử lại.`;
  }
  if (typeof detail === "string" && detail.trim()) return detail;
  switch (status) {
    case 400:
      return "Ảnh hoặc lựa chọn chưa hợp lệ. Hãy chọn một ảnh chính diện và một ảnh nghiêng khác nhau.";
    case 413:
      return "Mỗi ảnh tối đa 10 MB. Hãy chụp lại hoặc giảm kích thước ảnh.";
    case 422:
      return "Thiếu hoặc sai thông tin gửi lên (chiều cao, chế độ chụp). Kiểm tra rồi thử lại.";
    case 429:
      return "Hết hạn mức gọi AI (free tier khoảng 20 lượt/ngày mỗi model). Thử lại sau hoặc dùng chế độ quét 3D.";
    case 502:
      return "Dịch vụ AI phía trên trả lỗi nên chưa có kết quả. Thử lại sau ít phút hoặc dùng chế độ quét 3D.";
    case 503:
      return "AI chưa được cấu hình trên máy chủ (thiếu key hoặc thiếu thư viện). Dùng chế độ quét 3D trong lúc chờ.";
    case 504:
      return "AI phản hồi quá lâu. Thử lại với ảnh nhỏ hơn, hoặc dùng chế độ quét 3D.";
    default:
      return `AI chưa phân tích được hai ảnh (mã ${status}). Hãy thử lại.`;
  }
}

const OFFLINE_HEALTH: AiScanHealth = {
  ready: false,
  provider: "google-genai",
  model: "",
  message: "Chưa kết nối được dịch vụ AI.",
};

export function useAiScan() {
  const [health, setHealth] = useState<AiScanHealth | null>(null);
  const [result, setResult] = useState<AiScanResultData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch("/api/ai-scan/health", { cache: "no-store" });
      if (!response.ok) throw new Error("health check failed");
      setHealth((await response.json()) as AiScanHealth);
    } catch {
      setHealth(OFFLINE_HEALTH);
    }
  }, []);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  // The backend may start later or a key may be added while this page is open;
  // retry quietly instead of leaving the AI mode disabled until a manual reload.
  useEffect(() => {
    if (health?.ready) return;
    const timer = setInterval(() => void checkHealth(), 10000);
    return () => clearInterval(timer);
  }, [health?.ready, checkHealth]);

  const analyze = useCallback(
    async (
      pair: { front: File; side: File },
      height: string,
      captureMode: AiCaptureMode,
      sex: "auto" | "female" | "male" = "auto"
    ) => {
      setBusy(true);
      setError("");
      setResult(null);
      try {
        const body = new FormData();
        body.append("front", pair.front);
        body.append("side", pair.side);
        body.append("height_cm", height);
        body.append("capture_mode", captureMode);
        body.append("sex", sex);
        body.append("consent", "true");

        const response = await fetch("/api/ai-scan/analyze", {
          method: "POST",
          body,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(describeAiError(response.status, data?.detail));
        }
        setResult(data as AiScanResultData);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Không gọi được dịch vụ AI.");
      } finally {
        setBusy(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setResult(null);
    setError("");
  }, []);

  return { health, result, busy, error, analyze, reset, checkHealth };
}
