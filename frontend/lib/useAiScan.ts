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
  key: "chest_cm" | "waist_cm" | "hip_cm" | "shoulder_width_cm";
  label: string;
  value_cm: number | null;
  source: "ai_vision_estimate";
};

export type AiScanResultData = {
  status: "completed";
  provider: "google-genai";
  model: string;
  capture_mode: AiCaptureMode;
  measurements: {
    height_cm: number;
    chest_cm: number | null;
    waist_cm: number | null;
    hip_cm: number | null;
    shoulder_width_cm: number | null;
  };
  details: AiMeasurementDetail[];
  confidence: number;
  pose_quality: string;
  notes: string;
  warnings: string[];
  elapsed_seconds: number;
  source: "ai_vision_estimate";
};

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

  const analyze = useCallback(
    async (
      pair: { front: File; side: File },
      height: string,
      captureMode: AiCaptureMode
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
        body.append("consent", "true");

        const response = await fetch("/api/ai-scan/analyze", {
          method: "POST",
          body,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            typeof data?.detail === "string"
              ? data.detail
              : "AI chưa phân tích được hai ảnh. Hãy thử lại."
          );
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
