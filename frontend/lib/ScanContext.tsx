"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from "react";
import type { Job } from "./useBodyScan";
import type { Product } from "./catalog";
import { useAuth } from "./AuthContext";

export interface SizeAdviceResult {
  status: "matched" | "no_match" | "insufficient_measurements" | "error";
  candidates: string[];
  message: string;
  warning?: string;
  chart_name?: string;
}

export type ScanSaveStatus = "idle" | "saving" | "saved" | "error";

export interface ScanContextValue {
  job: Job | null;
  setJob: (job: Job | null) => void;
  jobError: string;
  setJobError: (err: string) => void;
  adviceCache: Record<string, SizeAdviceResult>;
  fetchAdviceForProduct: (product: Product, currentJob?: Job | null) => Promise<SizeAdviceResult>;
  clearScanSession: () => Promise<void>;
  // Global modal helpers
  isScanModalOpen: boolean;
  activeScanProduct: Product | null;
  openScanModal: (product: Product) => void;
  closeScanModal: () => void;
  // Size applied directly to product from scan
  appliedSizes: Record<string, string>; // productId -> selected size
  applySizeToProduct: (productId: string, size: string) => void;
  // Body profile scan saving & guest token management
  guestTokens: Record<string, string>;
  getGuestToken: (scanId: string) => string;
  savedScans: Record<string, ScanSaveStatus>;
  saveErrors: Record<string, string>;
  saveScanToProfile: (
    scanId: string,
    guestToken?: string
  ) => Promise<{ success: boolean; error?: string; expired?: boolean }>;
  clearPersonalScanData: () => void;
  applySavedScanToSession: (scan: {
    id: string;
    source_scan_id?: string | null;
    capture_mode: "upper_body" | "full_body";
    height_input_cm: number;
    measurements: {
      metric_key: string;
      label: string;
      value_cm: number | null;
      source: string;
    }[];
  }) => void;
}

const ScanContext = createContext<ScanContextValue | null>(null);

export function computeClientSizeAdvice(
  measurements: Record<string, number | null | undefined>,
  chart: Product["chart"]
): SizeAdviceResult {
  const isBottom = chart.garment === "bottom";
  const hasHipInChart = isBottom || chart.rows.some((r) => r.hip_cm != null);
  // Áo chọn size theo vòng ngực: hàng eo trong bảng áo là tham khảo, không bắt
  // buộc phải có số đo eo. Quần/váy vẫn cần cả eo và mông.
  const required: ("chest_cm" | "waist_cm" | "hip_cm")[] = isBottom
    ? ["waist_cm", "hip_cm"]
    : hasHipInChart
      ? ["chest_cm", "hip_cm"]
      : ["chest_cm"];

  if (hasHipInChart && (measurements.hip_cm == null || measurements.hip_cm <= 0)) {
    return {
      status: "insufficient_measurements",
      candidates: [],
      chart_name: chart.name,
      message: "Chưa đủ dữ liệu để gợi ý (cần số đo vòng mông)",
      warning: "Webcam thân trên không đo được vòng mông. Hãy chụp toàn thân để có số đo này.",
    };
  }

  for (const dim of required) {
    const val = measurements[dim];
    if (val == null || val <= 0) {
      return {
        status: "insufficient_measurements",
        candidates: [],
        chart_name: chart.name,
        message: dim === "hip_cm" ? "Chưa đủ dữ liệu để gợi ý (cần số đo vòng mông)" : "Chưa đủ số đo để đối chiếu bảng size.",
      };
    }
  }

  const candidates: string[] = [];
  for (const row of chart.rows) {
    let fits = true;
    for (const dim of required) {
      const range = row[dim];
      const val = measurements[dim];
      if (range && val != null) {
        if (val < range.min || val > range.max) {
          fits = false;
          break;
        }
      }
    }
    if (fits) {
      candidates.push(row.size);
    }
  }

  return {
    status: candidates.length > 0 ? "matched" : "no_match",
    candidates,
    chart_name: chart.name,
    message:
      candidates.length > 0
        ? "Khớp các khoảng trong bảng đã chọn."
        : "Không có size nào khớp tất cả số đo của bạn trong bảng.",
    warning:
      "Số đo từ ảnh chưa được kiểm chứng; đây là gợi ý tham khảo. Độ co giãn và độ rộng trang phục chưa được mô phỏng.",
  };
}

export function ScanProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [job, setJobState] = useState<Job | null>(null);
  const [jobError, setJobError] = useState<string>("");
  const [adviceCache, setAdviceCache] = useState<Record<string, SizeAdviceResult>>({});
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [activeScanProduct, setActiveScanProduct] = useState<Product | null>(null);
  const [appliedSizes, setAppliedSizes] = useState<Record<string, string>>({});

  // Profile save states & guest tokens
  const [guestTokens, setGuestTokens] = useState<Record<string, string>>({});
  const [savedScans, setSavedScans] = useState<Record<string, ScanSaveStatus>>({});
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({});

  const prevUserRef = useRef(user);

  // Clear personal scan save status when user logs out
  useEffect(() => {
    if (prevUserRef.current && !user) {
      setSavedScans({});
      setSaveErrors({});
    }
    prevUserRef.current = user;
  }, [user]);

  const getGuestToken = useCallback(
    (scanId: string): string => {
      if (!scanId) return "";
      if (guestTokens[scanId]) return guestTokens[scanId];
      if (job?.id === scanId && job.guest_token) {
        setGuestTokens((prev) => ({ ...prev, [scanId]: job.guest_token! }));
        return job.guest_token;
      }

      if (typeof window !== "undefined") {
        try {
          const stored = sessionStorage.getItem(`morph_scan_guest_token_${scanId}`);
          if (stored) {
            setGuestTokens((prev) => ({ ...prev, [scanId]: stored }));
            return stored;
          }
        } catch {
          // sessionStorage may fail in private mode
        }
      }

      return "";
    },
    [guestTokens, job]
  );

  const setJob = useCallback(
    (newJob: Job | null) => {
      // React bails out when the state updater returns the same reference.
      // This keeps the local-hook -> ScanContext sync from re-rendering on
      // every parent render (which previously caused "Maximum update depth").
      setJobState((prev) => (prev === newJob ? prev : newJob));
      setAdviceCache((prev) => (Object.keys(prev).length === 0 ? prev : {}));
      if (newJob && newJob.id && newJob.guest_token && !newJob.user_id) {
        setGuestTokens((prev) =>
          prev[newJob.id] === newJob.guest_token
            ? prev
            : { ...prev, [newJob.id]: newJob.guest_token! }
        );
        if (typeof window !== "undefined") {
          try {
            sessionStorage.setItem(`morph_scan_guest_token_${newJob.id}`, newJob.guest_token);
          } catch {}
        }
      }
    },
    []
  );

  // Shared job polling: Maintain active job polling in ScanContext across modal open/close
  useEffect(() => {
    if (!job || !["queued", "processing"].includes(job.status)) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;

    async function poll() {
      try {
        const token = job!.user_id ? "" : job!.guest_token || getGuestToken(job!.id);
        const headers: Record<string, string> = {};
        if (token) headers["X-Guest-Token"] = token;
        const r = await fetch(`/api/scans/${job!.id}`, {
          headers,
          credentials: "include",
        });
        if (r.status === 404) {
          if (alive) {
            setJobState(null);
            setAdviceCache({});
            setJobError("Phiên đã hết hạn hoặc máy chủ đã khởi động lại. Vui lòng quét lại.");
          }
          return;
        }
        if (!r.ok) throw new Error("Không đọc được trạng thái scan.");
        const data: Job = await r.json();
        if (!alive) return;
        failures = 0;
        setJobState(data);
        if (data.status === "failed") {
          setJobError(data.error || "Chưa dựng được hình. Hãy thử ảnh khác.");
        } else if (data.status === "completed") {
          setJobError("");
        }
        if (["queued", "processing"].includes(data.status)) {
          timer = setTimeout(poll, 1200);
        }
      } catch {
        if (!alive) return;
        failures += 1;
        if (failures < 5) {
          timer = setTimeout(poll, 2000);
        } else {
          setJobError("Mất kết nối backend. Kết quả có thể vẫn đang xử lý; kiểm tra backend rồi thử lại.");
        }
      }
    }

    timer = setTimeout(poll, 500);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [job?.id, job?.status, job?.guest_token, job?.user_id, getGuestToken]);

  const clearScanSession = useCallback(async () => {
    if (job?.id) {
      try {
        const token = job.user_id ? "" : job.guest_token || getGuestToken(job.id);
        const headers: Record<string, string> = {};
        if (token) headers["X-Guest-Token"] = token;
        await fetch(`/api/scans/${job.id}`, {
          method: "DELETE",
          headers,
          credentials: "include",
        });
      } catch {
        // Backend cleanup
      }
    }
    setJobState(null);
    setAdviceCache({});
    setJobError("");
  }, [job?.id, job?.guest_token, job?.user_id, getGuestToken]);

  const fetchAdviceForProduct = useCallback(
    async (product: Product, currentJob?: Job | null): Promise<SizeAdviceResult> => {
      const activeJob = currentJob || job;
      if (!activeJob || activeJob.status !== "completed") {
        return {
          status: "error",
          candidates: [],
          message: "Chưa có dữ liệu scan hoàn chỉnh.",
        };
      }

      const modeKey = activeJob.body_profile?.capture_mode || "default";
      const cacheKey = `${activeJob.id}:${modeKey}:${product.id}:${product.chart.name}:${product.chart.rows.length}`;
      if (adviceCache[cacheKey]) {
        return adviceCache[cacheKey];
      }

      const token = activeJob.user_id ? "" : getGuestToken(activeJob.id) || activeJob.guest_token || "";
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) {
        headers["X-Guest-Token"] = token;
      }

      try {
        let res = await fetch("/api/sizing/recommend", {
          method: "POST",
          headers,
          credentials: "include",
          body: JSON.stringify({
            product_id: product.id,
            scan_id: activeJob.id,
            guest_token: token || undefined,
            chart: product.chart,
          }),
        });

        if (res.status === 405) {
          res = await fetch(`/api/scans/${activeJob.id}/size-advice`, {
            method: "POST",
            headers,
            credentials: "include",
            body: JSON.stringify(product.chart),
          });
        }

        if (res.status === 404) {
          setJobState(null);
          setAdviceCache({});
          const expiredMsg = "Phiên đã hết hạn hoặc máy chủ đã khởi động lại. Vui lòng quét lại.";
          setJobError(expiredMsg);
          throw new Error(expiredMsg);
        }

        if (res.ok) {
          const data = (await res.json()) as SizeAdviceResult;
          const needsHip =
            product.chart.garment === "bottom" ||
            product.chart.rows.some((r) => r.hip_cm != null);
          if (
            data.status === "insufficient_measurements" &&
            (needsHip || activeJob.measurements?.hip_cm == null)
          ) {
            data.message = data.message || "Chưa đủ dữ liệu để gợi ý (cần số đo vòng mông)";
          }
          setAdviceCache((prev) => ({ ...prev, [cacheKey]: data }));
          return data;
        }

        setAdviceCache((prev) => {
          const next = { ...prev };
          delete next[cacheKey];
          return next;
        });

        let detailMsg = "Không thể lấy gợi ý size từ máy chủ.";
        try {
          const errData = await res.json();
          if (errData?.detail && typeof errData.detail === "string") {
            detailMsg = errData.detail;
          }
        } catch {}
        throw new Error(detailMsg);
      } catch (err) {
        setAdviceCache((prev) => {
          const next = { ...prev };
          delete next[cacheKey];
          return next;
        });
        if (err instanceof Error && err.message === "Phiên đã hết hạn hoặc máy chủ đã khởi động lại. Vui lòng quét lại.") {
          throw err;
        }
        if (err instanceof Error && err.message) {
          throw err;
        }
        throw new Error("Lỗi kết nối máy chủ khi đối chiếu size. Vui lòng thử lại.");
      }
    },
    [job, adviceCache, getGuestToken]
  );

  const saveScanToProfile = useCallback(
    async (
      scanId: string,
      guestTokenParam?: string
    ): Promise<{ success: boolean; error?: string; expired?: boolean }> => {
      if (!scanId) {
        return { success: false, error: "Thiếu mã phiên scan." };
      }
      const token = guestTokenParam || getGuestToken(scanId);

      setSavedScans((prev) => ({ ...prev, [scanId]: "saving" }));
      setSaveErrors((prev) => ({ ...prev, [scanId]: "" }));

      try {
        const res = await fetch("/api/user/scans/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            scan_id: scanId,
            guest_token: token || undefined,
          }),
        });

        if (res.status === 404 || res.status === 410) {
          const expiredMsg = "Phiên scan tạm thời đã hết hạn, vui lòng quét lại để lưu số đo mới nhất.";
          setSavedScans((prev) => ({ ...prev, [scanId]: "error" }));
          setSaveErrors((prev) => ({ ...prev, [scanId]: expiredMsg }));
          return { success: false, expired: true, error: expiredMsg };
        }

        if (!res.ok) {
          let errMsg = "Không thể lưu vào hồ sơ lúc này. Vui lòng thử lại.";
          try {
            const data = await res.json();
            if (data?.detail) {
              errMsg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
            } else if (data?.message) {
              errMsg = data.message;
            }
          } catch {}
          setSavedScans((prev) => ({ ...prev, [scanId]: "error" }));
          setSaveErrors((prev) => ({ ...prev, [scanId]: errMsg }));
          return { success: false, error: errMsg };
        }

        let savedId: string | undefined;
        try {
          const savedData = await res.json();
          if (savedData?.id) {
            savedId = savedData.id;
          }
        } catch {}

        setSavedScans((prev) => ({
          ...prev,
          [scanId]: "saved",
          ...(savedId ? { [savedId]: "saved" } : {}),
        }));
        setGuestTokens((prev) => {
          const next = { ...prev };
          delete next[scanId];
          return next;
        });
        if (typeof window !== "undefined") {
          try {
            sessionStorage.removeItem(`morph_scan_guest_token_${scanId}`);
          } catch {}
        }
        setJobState((prev) =>
          prev && prev.id === scanId
            ? { ...prev, guest_token: undefined, user_id: user?.id || prev.user_id }
            : prev
        );
        return { success: true };
      } catch {
        const networkErrMsg = "Lỗi kết nối mạng khi lưu hồ sơ. Vui lòng thử lại.";
        setSavedScans((prev) => ({ ...prev, [scanId]: "error" }));
        setSaveErrors((prev) => ({ ...prev, [scanId]: networkErrMsg }));
        return { success: false, error: networkErrMsg };
      }
    },
    [getGuestToken, user?.id]
  );

  const clearPersonalScanData = useCallback(() => {
    setSavedScans({});
    setSaveErrors({});
    setGuestTokens({});
    setAdviceCache({});
    setAppliedSizes({});
    if (typeof window !== "undefined") {
      try {
        sessionStorage.removeItem("morph_saved_scans_map");
        const keysToRemove: string[] = [];
        for (let i = 0; i < sessionStorage.length; i++) {
          const key = sessionStorage.key(i);
          if (key && (key.startsWith("morph_scan_guest_token_") || key === "morph_saved_scans_map")) {
            keysToRemove.push(key);
          }
        }
        keysToRemove.forEach((k) => sessionStorage.removeItem(k));
      } catch {}
    }
  }, []);

  // Listen to logout broadcast event to clear memory cache immediately
  useEffect(() => {
    const handleLogout = () => {
      clearPersonalScanData();
    };
    window.addEventListener("morph:auth:logout", handleLogout);
    return () => {
      window.removeEventListener("morph:auth:logout", handleLogout);
    };
  }, [clearPersonalScanData]);

  const applySavedScanToSession = useCallback(
    (scan: {
      id: string;
      source_scan_id?: string | null;
      capture_mode: "upper_body" | "full_body";
      height_input_cm: number;
      measurements: {
        metric_key: string;
        label: string;
        value_cm: number | null;
        source: string;
      }[];
    }) => {
      const measMap: Record<string, number | undefined> = {};
      scan.measurements.forEach((m) => {
        if (
          m.value_cm !== null &&
          m.value_cm > 0 &&
          m.source !== "template_model" &&
          m.source !== "unavailable" &&
          !(scan.capture_mode === "upper_body" && m.metric_key === "hip_cm" && m.source !== "user_input")
        ) {
          measMap[m.metric_key] = m.value_cm;
        }
      });
      measMap.height_cm = scan.height_input_cm;

      const sessionJobId = scan.source_scan_id || scan.id;
      const sessionJob: Job = {
        id: sessionJobId,
        status: "completed",
        stage: "complete",
        user_id: user?.id || null,
        measurements: measMap,
        body_profile: {
          capture_mode: scan.capture_mode,
          measurement_details: scan.measurements.map((m) => ({
            key: m.metric_key,
            label: m.label,
            value_cm: m.value_cm,
            source: m.source as any,
            color: "#C29B38",
            points_m: [],
          })),
        },
      };

      setJobState(sessionJob);
      setAdviceCache({});
      setSavedScans((prev) => ({
        ...prev,
        [scan.id]: "saved",
        ...(scan.source_scan_id ? { [scan.source_scan_id]: "saved" } : {}),
      }));
    },
    [user?.id]
  );

  const openScanModal = useCallback((product: Product) => {
    setActiveScanProduct(product);
    setIsScanModalOpen(true);
  }, []);

  const closeScanModal = useCallback(() => {
    setIsScanModalOpen(false);
  }, []);

  const applySizeToProduct = useCallback((productId: string, size: string) => {
    setAppliedSizes((prev) => ({ ...prev, [productId]: size }));
  }, []);

  return (
    <ScanContext.Provider
      value={{
        job,
        setJob,
        jobError,
        setJobError,
        adviceCache,
        fetchAdviceForProduct,
        clearScanSession,
        isScanModalOpen,
        activeScanProduct,
        openScanModal,
        closeScanModal,
        appliedSizes,
        applySizeToProduct,
        guestTokens,
        getGuestToken,
        savedScans,
        saveErrors,
        saveScanToProfile,
        clearPersonalScanData,
        applySavedScanToSession,
      }}
    >
      {children}
    </ScanContext.Provider>
  );
}

export function useScan() {
  const ctx = useContext(ScanContext);
  if (!ctx) throw new Error("useScan must be used within a ScanProvider");
  return ctx;
}
