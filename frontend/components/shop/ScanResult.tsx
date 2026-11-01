"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Component, useRef, useState, useEffect, useMemo, type ReactNode } from "react";
import {
  ArrowRight,
  Box,
  Copy,
  Download,
  Expand,
  Image as ImageIcon,
  RotateCcw,
  Rotate3D,
  Ruler,
  SlidersHorizontal,
  Sparkles,
  AlertCircle,
  Bookmark,
  CheckCircle2,
  TrendingUp,
  LoaderCircle,
  Paintbrush,
  Pencil,
} from "lucide-react";
import type { Job, MeasurementDetail } from "../../lib/useBodyScan";
import type { Product } from "../../lib/catalog";
import { fetchFitMap, type FitBand, type FitMapResult } from "../../lib/fitMap";
import { FIT_BUCKETS, bucketRegions } from "../../lib/fitBuckets";
import { fetchAllProducts } from "../../lib/catalogApi";
import { EXPLAIN_METRIC_LABEL, fetchFitExplain, type FitExplainResult } from "../../lib/fitExplain";
import FitBucketPanel from "./FitBucketPanel";
import TryOnWardrobe from "./TryOnWardrobe";
import type { FitHeatmap } from "../BodyViewer";
import { useScan, type SizeAdviceResult } from "../../lib/ScanContext";
import { useAuth } from "../../lib/AuthContext";
import { useRouter } from "next/navigation";
import { buildAuthUrl } from "../../lib/authNav";

const Viewer = dynamic(() => import("../BodyViewer"), {
  ssr: false,
  loading: () => <p className="scan-loading">Đang tải mô hình 3D…</p>,
});

const SOURCE: Record<MeasurementDetail["source"], string> = {
  user_input: "Bạn nhập",
  photo_estimate: "Đo từ ảnh",
  photo_with_prior: "Đo từ ảnh + tỷ lệ mẫu",
  template_model: "Mô hình mẫu",
  unavailable: "Chưa đo được",
};

// Chỉ các mốc dùng để chọn size mới được kiểm nguồn: đầu/cổ/đùi/bắp chân luôn
// thuộc mô hình nền nên sẽ làm cảnh báo thành tiếng ồn nếu tính cả.
const SIZING_KEYS = new Set([
  "chest_cm",
  "waist_cm",
  "hip_cm",
  "shoulder_width_cm",
  "bicep_cm",
  "forearm_cm",
  "arm_length_cm",
]);
const PHOTO_SOURCES = new Set<MeasurementDetail["source"]>([
  "photo_estimate",
  "photo_with_prior",
  "user_input",
]);

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <p className="scan-loading">Không mở được mô hình 3D (phiên có thể đã hết hạn hoặc trình duyệt chặn WebGL). Số đo và file tải xuống vẫn khả dụng.</p>
    ) : (
      this.props.children
    );
  }
}

export default function ScanResult({
  job,
  active,
  onReset,
  deleting,
  onSelectSize,
  advice,
  adviceError,
  onRetry,
  error,
  product,
  onOpenSizeChart,
  onResetFullBody,
  onSelectProduct,
}: {
  job: Job;
  active: boolean;
  onReset: () => void;
  deleting: boolean;
  onSelectSize: (size: string) => void;
  advice: SizeAdviceResult | null;
  adviceError: string;
  onRetry: () => void;
  error: string;
  product?: Product;
  onOpenSizeChart?: () => void;
  onResetFullBody?: () => void;
  onSelectProduct?: (product: Product) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const [rotate, setRotate] = useState(false);
  const [rings, setRings] = useState(false);
  const [mode, setMode] = useState("solid");
  const [reset, setReset] = useState(0);
  const [unit, setUnit] = useState("cm");
  const [selected, setSelected] = useState("");
  const [notice, setNotice] = useState("");
  const [loadingTimedOut, setLoadingTimedOut] = useState(false);
  const [fitSize, setFitSize] = useState("");
  const [fitMap, setFitMap] = useState<FitMapResult | null>(null);
  const [fitLoading, setFitLoading] = useState(false);
  const [fitError, setFitError] = useState("");
  const [fitView, setFitView] = useState(true);
  const [wardrobe, setWardrobe] = useState<Product[]>([]);
  const [explain, setExplain] = useState<FitExplainResult | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const explainCache = useRef<Record<string, FitExplainResult>>({});
  const [editing, setEditing] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [editForm, setEditForm] = useState({ height_cm: "", chest_cm: "", waist_cm: "", hip_cm: "" });

  useEffect(() => {
    if (!advice && !adviceError) {
      setLoadingTimedOut(false);
      const timer = setTimeout(() => {
        setLoadingTimedOut(true);
      }, 7000);
      return () => clearTimeout(timer);
    } else {
      setLoadingTimedOut(false);
    }
  }, [advice, adviceError]);

  const activeFitSize = fitSize || advice?.candidates?.[0] || product?.sizes?.[0] || "";

  useEffect(() => {
    if (!product || !activeFitSize || job.status !== "completed") {
      setFitMap(null);
      return;
    }
    let cancelled = false;
    setFitLoading(true);
    setFitError("");
    fetchFitMap(product.slug, activeFitSize, job.measurements || {})
      .then((result) => {
        if (!cancelled) setFitMap(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setFitMap(null);
          setFitError(err?.message || "Chưa tính được bản đồ độ vừa.");
        }
      })
      .finally(() => {
        if (!cancelled) setFitLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [product?.slug, activeFitSize, job.id, job.status, job.revision]);

  const isBottom = product?.chart?.garment === "bottom";
  const fitBands: FitBand[] = useMemo(
    () =>
      (fitMap?.regions || [])
        .filter((region) => region.verdict !== "unknown")
        .map((region) => ({ from: region.band.from, to: region.band.to, color: region.color })),
    [fitMap]
  );

  // Try-on heatmap: UI-only three-bucket map built from the API's ease values.
  // Only the garment torso (chest/waist bands) is painted; arms and bottoms stay
  // neutral, and a region without garment data is grey instead of guessed.
  const bucketFit = useMemo(() => bucketRegions(fitMap), [fitMap]);
  const fitHeatmap = useMemo<FitHeatmap | undefined>(() => {
    if (!fitMap || !bucketFit.length || isBottom) return undefined;
    const source = (fitMap as FitMapResult & {
      heatmap?: { garment_length_cm?: number | null; shoulder_level?: number };
    }).heatmap;
    return {
      mode: "region_buckets",
      regions: bucketFit.map((region) => ({
        from: region.from,
        to: region.to,
        color: FIT_BUCKETS[region.bucket].color,
        label: region.label,
        ease_cm: region.ease_cm,
      })),
      unknown_color: FIT_BUCKETS.unknown.color,
      arm_x_fraction: 0.18,
      garment_length_cm: source?.garment_length_cm ?? null,
      shoulder_level: source?.shoulder_level ?? 0.805,
      unverified: true,
    };
  }, [fitMap, bucketFit, isBottom]);

  // Tủ đồ: danh sách sản phẩm thân trên cho cột 22%. Sản phẩm đang xem đứng
  // đầu danh sách và chỉ đổi được khi trang cha sở hữu state sản phẩm (/scan).
  useEffect(() => {
    let cancelled = false;
    fetchAllProducts()
      .then((items) => {
        if (!cancelled) setWardrobe(items.filter((item) => item.chart?.garment !== "bottom"));
      })
      .catch(() => {
        /* fall back to the current product only */
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const wardrobeProducts = useMemo<Product[]>(() => {
    // Ưu tiên món có số đo áo thật (garment_specs) để heatmap có dữ liệu; các
    // món còn lại vẫn hiện nhưng vùng thiếu số đo sẽ xám.
    const rest = wardrobe
      .filter((item) => item.id !== product?.id)
      .sort((a, b) => Number(Boolean(b.garment_specs?.length)) - Number(Boolean(a.garment_specs?.length)));
    return product ? [product, ...rest].slice(0, 24) : rest.slice(0, 24);
  }, [wardrobe, product]);

  // A size chosen for one garment may not exist on the next one.
  useEffect(() => {
    setFitSize("");
  }, [product?.slug]);

  const chestEase = bucketFit.find((region) => region.key === "chest_cm")?.ease_cm ?? null;
  const waistEase = bucketFit.find((region) => region.key === "waist_cm")?.ease_cm ?? null;

  // One explanation per (product, size, ease): cached in this ref and again on
  // the backend. The endpoint answers with the deterministic fallback when the
  // AI is unconfigured, rate-limited or produces a foreign number, so a failure
  // never blocks the result screen.
  useEffect(() => {
    if (!product || isBottom || !activeFitSize || job.status !== "completed") {
      setExplain(null);
      return;
    }
    if (chestEase == null && waistEase == null) {
      setExplain(null);
      return;
    }
    const key = `${product.slug}|${activeFitSize}|${chestEase ?? ""}|${waistEase ?? ""}`;
    const cached = explainCache.current[key];
    if (cached) {
      setExplain(cached);
      return;
    }
    const controller = new AbortController();
    setExplainLoading(true);
    fetchFitExplain(
      activeFitSize,
      { chest_cm: chestEase, waist_cm: waistEase },
      { name: product.name, fit: product.fit, material: product.material },
      controller.signal
    )
      .then((result) => {
        explainCache.current[key] = result;
        setExplain(result);
      })
      .catch((err) => {
        if (err?.name !== "AbortError") setExplain(null);
      })
      .finally(() => setExplainLoading(false));
    return () => controller.abort();
  }, [product?.slug, activeFitSize, chestEase, waistEase, isBottom, job.status]);

  const router = useRouter();
  const { user } = useAuth();
  const { savedScans, saveErrors, saveScanToProfile, getGuestToken, setJob } = useScan();
  const autoSavedJobRef = useRef<Record<string, boolean>>({});

  const currentSaveStatus = savedScans[job.id] || "idle";
  const currentSaveError = saveErrors[job.id] || "";

  useEffect(() => {
    if (job?.status === "completed" && job?.id) {
      if (
        user &&
        user.auto_save_scans &&
        (!savedScans[job.id] || savedScans[job.id] === "idle") &&
        !autoSavedJobRef.current[job.id]
      ) {
        autoSavedJobRef.current[job.id] = true;
        void saveScanToProfile(job.id, getGuestToken(job.id));
      }
    }
  }, [job?.id, job?.status, user, savedScans, saveScanToProfile, getGuestToken]);

  // Vai tạm ẩn: bảng size dùng vai áo, so với vai cơ thể dễ gây hiểu nhầm.
  const HIDDEN_METRICS = new Set(["hip_cm", "thigh_cm", "calf_cm", "inseam_cm"]);
  const upper = job.body_profile?.capture_mode === "upper_body";
  const rows = (job.body_profile?.measurement_details || []).filter(
    (m) => !HIDDEN_METRICS.has(m.key) && !(upper && m.key === "hip_cm"),
  );
  const value = (m: MeasurementDetail) =>
    m.value_cm == null ? "—" : (m.value_cm / (unit === "in" ? 2.54 : 1)).toFixed(1);
  const reason = (m: MeasurementDetail) =>
    job.body_profile?.unavailable?.[m.key] || m.quality_warnings?.[0] || "";
  // Chỉ báo khi một mốc dùng để chọn size không đến từ ảnh (mô hình nền hoặc
  // chưa đo được). photo_with_prior vẫn là số suy từ ảnh nên không tính.
  const notFromPhoto = rows.filter(
    (m) => SIZING_KEYS.has(m.key) && !PHOTO_SOURCES.has(m.source),
  );

  const guestToken = job.user_id
    ? ""
    : job.guest_token ||
      getGuestToken(job.id) ||
      (typeof window !== "undefined"
        ? (() => {
            try {
              return sessionStorage.getItem(`morph_scan_guest_token_${job.id}`) || "";
            } catch {
              return "";
            }
          })()
        : "");

  const withGuestToken = (url?: string) => {
    if (!url || !guestToken) return url;
    const sep = url.includes("?") ? "&" : "?";
    return `${url}${sep}guest_token=${encodeURIComponent(guestToken)}`;
  };

  const modelUrl = (() => {
    const base = withGuestToken(job.model_url);
    if (!base || !job.revision) return base;
    return `${base}${base.includes("?") ? "&" : "?"}v=${job.revision}`;
  })();
  const hasModel = Boolean(modelUrl);
  const measurementsUrl = withGuestToken(`/api/scans/${job.id}/measurements`);

  function openEditor() {
    setEditForm({
      height_cm: job.measurements?.height_cm != null ? String(job.measurements.height_cm) : "",
      chest_cm: job.measurements?.chest_cm != null ? String(job.measurements.chest_cm) : "",
      waist_cm: job.measurements?.waist_cm != null ? String(job.measurements.waist_cm) : "",
      hip_cm: job.measurements?.hip_cm != null ? String(job.measurements.hip_cm) : "",
    });
    setEditError("");
    setEditing(true);
  }

  async function saveEdits() {
    const parse = (value: string) => (value.trim() === "" ? null : Number(value.replace(",", ".")));
    const next = {
      height_cm: parse(editForm.height_cm),
      chest_cm: parse(editForm.chest_cm),
      waist_cm: parse(editForm.waist_cm),
      hip_cm: parse(editForm.hip_cm),
    };
    const current = job.measurements || {};
    const payload: Record<string, number> = {};
    (Object.keys(next) as (keyof typeof next)[]).forEach((key) => {
      const value = next[key];
      const before = current[key as keyof typeof current];
      if (value == null || !Number.isFinite(value)) return;
      if (before == null || Math.abs(value - before) > 0.05) payload[key] = value;
    });
    if (Object.keys(payload).length === 0) {
      setEditError("Chưa có số đo nào thay đổi.");
      return;
    }
    setEditSaving(true);
    setEditError("");
    try {
      const response = await fetch(`/api/scans/${job.id}/measurements`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(guestToken ? { "X-Guest-Token": guestToken } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || "Không lưu được số đo mới.");
      }
      const updated = (await response.json()) as Job;
      setJob(updated);
      setEditing(false);
      setNotice("Đã cập nhật số đo và dựng lại mô hình 3D.");
      onRetry();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Không lưu được số đo mới.");
    } finally {
      setEditSaving(false);
    }
  }

  async function fullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await host.current?.requestFullscreen();
    } catch {
      setNotice("Trình duyệt chưa mở được toàn màn hình. Bạn vẫn có thể kéo và phóng to mô hình.");
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(
        JSON.stringify(
          {
            unit: "cm",
            capture_mode: job.body_profile?.capture_mode,
            measurements: job.measurements,
            details: rows,
            warnings: job.warnings,
          },
          null,
          2
        )
      );
      setNotice("Đã sao chép JSON kèm nguồn số đo.");
    } catch {
      setNotice("Không sao chép được. Hãy dùng Tải JSON.");
    }
  }

  function snapshot() {
    const canvas = host.current?.querySelector("canvas");
    if (!canvas) return;
    requestAnimationFrame(() =>
      canvas.toBlob((blob) => {
        if (!blob) {
          setNotice("Không xuất được ảnh 3D.");
        } else {
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "morph-body.png";
          a.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
      }, "image/png")
    );
  }

  const editFields = [
    { key: "height_cm", label: "Chiều cao", min: 100, max: 230 },
    { key: "chest_cm", label: "Vòng ngực", min: 40, max: 200 },
    { key: "waist_cm", label: "Vòng eo", min: 30, max: 200 },
    { key: "hip_cm", label: "Vòng mông", min: 40, max: 200 },
  ] as const;
  const sexLabel =
    job.body_profile?.sex === "male" ? "Nam" : job.body_profile?.sex === "female" ? "Nữ" : "";

  return (
    <div className="scan-result" ref={host}>
      <header className="scan-result-heading">
        <div>
          <h2>Hình thể 3D của bạn</h2>
          <p>
            {job.measurements?.height_cm} cm · {upper ? "Webcam thân trên" : "Ảnh toàn thân"} · Mô hình ước lượng
            {sexLabel && ` · Dáng ${sexLabel}${job.body_profile?.sex_source === "auto" ? " (tự động)" : ""}`}
          </p>
        </div>
        <div className="scan-header-actions">
          <button className="scan-btn-subtle" type="button" onClick={onReset} disabled={deleting}>
            <RotateCcw size={15} />
            {deleting ? "Đang xóa…" : "Chụp lại"}
          </button>
          <button className="scan-btn-subtle" type="button" onClick={fullscreen}>
            <Expand size={15} />
            Toàn màn hình
          </button>
        </div>
      </header>

      <p className="scan-source-note">
        {upper
          ? "Không chụp chân. Ngực/eo dựa trên ảnh và tỷ lệ vai–hông giả định; phần đầu, mông và chân theo mẫu 3D."
          : "Ngực/eo/mông ước lượng từ hai ảnh. Các vòng đầu, cổ và chân trích từ mẫu 3D."}{" "}
        Chưa kiểm chứng độ chính xác trên người thật.
      </p>

      <div className="scan-edit-row">
        <button type="button" className="scan-btn-subtle" onClick={() => (editing ? setEditing(false) : openEditor())} disabled={editSaving}>
          <Pencil size={15} />
          {editing ? "Đóng sửa số đo" : "Sửa số đo"}
        </button>
        {job.revision ? <span className="scan-edit-badge">Đã sửa {job.revision} lần</span> : null}
        <span className="scan-edit-hint">Sửa ngực/eo/mông hoặc chiều cao; mô hình và gợi ý size sẽ được dựng lại.</span>
      </div>

      {editing && (
        <section className="scan-edit-panel" aria-label="Sửa số đo của bạn">
          <div className="scan-edit-grid">
            {editFields.map((field) => (
              <label key={field.key}>
                <span>{field.label}</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min={field.min}
                  max={field.max}
                  step="0.5"
                  value={editForm[field.key]}
                  onChange={(event) => setEditForm((prev) => ({ ...prev, [field.key]: event.target.value }))}
                  placeholder={field.key === "hip_cm" ? "Chưa đo" : ""}
                />
                <small>cm</small>
              </label>
            ))}
          </div>
          {editError && (
            <p className="scan-edit-error" role="alert">
              {editError}
            </p>
          )}
          <div className="scan-edit-actions">
            <button type="button" className="scan-size-apply-btn" onClick={saveEdits} disabled={editSaving}>
              {editSaving ? "Đang dựng lại mô hình…" : "Lưu & dựng lại mô hình"}
            </button>
            <button type="button" className="scan-btn-subtle" onClick={() => setEditing(false)} disabled={editSaving}>
              Hủy
            </button>
            <span className="scan-edit-note">Số đo sửa tay được ghi nguồn “Bạn nhập”.</span>
          </div>
        </section>
      )}

      {/* Body Profile Save & Measurement History Bar */}
      <div className="scan-profile-bar" role="region" aria-label="Lưu hồ sơ hình thể">
        <div className="scan-profile-status-group">
          {currentSaveStatus === "saved" ? (
            <div className="scan-save-badge is-saved" role="status">
              <CheckCircle2 size={16} />
              <span>Đã lưu vào hồ sơ hình thể</span>
              <Link href="/account/body-profile" className="scan-profile-link">
                Xem trong hồ sơ →
              </Link>
            </div>
          ) : currentSaveStatus === "saving" ? (
            <div className="scan-save-badge is-saving" role="status">
              <LoaderCircle size={16} className="scan-spin" />
              <span>Đang lưu vào hồ sơ hình thể…</span>
            </div>
          ) : user ? (
            <button
              type="button"
              className="scan-save-btn"
              onClick={() => saveScanToProfile(job.id, getGuestToken(job.id))}
            >
              <Bookmark size={15} />
              <span>Lưu vào hồ sơ hình thể</span>
            </button>
          ) : (
            <button
              type="button"
              className="scan-save-btn is-guest"
              onClick={() => {
                const token = job.guest_token || getGuestToken(job.id);
                const authUrl = buildAuthUrl("register", {
                  returnTo: `/scan?scan_id=${encodeURIComponent(job.id)}`,
                  intent: "save_scan",
                  scanId: job.id,
                  guestToken: token || undefined,
                });
                router.push(authUrl);
              }}
            >
              <Bookmark size={15} />
              <span>Lưu vào hồ sơ của tôi</span>
            </button>
          )}

          {currentSaveStatus === "error" && (
            <div className="scan-profile-error" role="alert">
              <AlertCircle size={15} />
              <span>{currentSaveError || "Lỗi lưu kết quả vào hồ sơ."}</span>
              <button
                type="button"
                className="scan-retry-save-btn"
                onClick={() => saveScanToProfile(job.id, getGuestToken(job.id))}
              >
                Thử lại
              </button>
            </div>
          )}
        </div>

        <div className="scan-profile-shortcuts">
          <Link href="/account/body-profile" className="scan-btn-subtle scan-profile-history-btn">
            <TrendingUp size={15} />
            <span>Xem biểu đồ & Lịch sử số đo</span>
          </Link>
        </div>
      </div>

      {/* Prominent Sizing Advice & Call To Action */}
      <section className="scan-size-panel" aria-label="Gợi ý size">
        <div className="scan-size-panel-info">
          <div className="scan-size-panel-title-row">
            <Sparkles size={20} className="scan-panel-gold-icon" />
            <h3>Gợi ý kích thước cho {product?.name || "sản phẩm"}</h3>
          </div>
          <p>
            {isBottom
              ? "Đối chiếu vòng eo và mông của bạn với bảng size của sản phẩm."
              : "Đối chiếu vòng ngực và eo của bạn với bảng size của sản phẩm."}{" "}
            Gợi ý mang tính tham khảo theo tỷ lệ hình thể.
          </p>
        </div>

        <div className="scan-size-panel-content">
          {adviceError ? (
            <div className="scan-advice-nomatch" role="alert">
              <div className="scan-nomatch-header">
                <AlertCircle size={18} />
                <p>{adviceError}</p>
              </div>
              <div className="scan-advice-actions">
                <button className="scan-btn-subtle" type="button" onClick={onRetry}>
                  <RotateCcw size={14} /> Thử lại
                </button>
                {onOpenSizeChart && (
                  <button className="scan-btn-subtle" type="button" onClick={onOpenSizeChart}>
                    Xem bảng size & chọn thủ công
                  </button>
                )}
              </div>
            </div>
          ) : !advice ? (
            loadingTimedOut ? (
              <div className="scan-advice-timeout" role="alert">
                <div className="scan-timeout-msg">
                  <AlertCircle size={18} />
                  <span>Quá trình đối chiếu size mất nhiều thời gian hơn dự kiến.</span>
                </div>
                <div className="scan-advice-actions">
                  <button className="scan-btn-subtle" type="button" onClick={onRetry}>
                    <RotateCcw size={14} /> Thử lại
                  </button>
                  {onOpenSizeChart && (
                    <button className="scan-btn-subtle" type="button" onClick={onOpenSizeChart}>
                      Xem bảng size & chọn thủ công
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="scan-advice-loading" role="status">
                <LoaderCircle size={20} className="scan-spin" />
                <span>Đang đối chiếu số đo hình thể với bảng size…</span>
              </div>
            )
          ) : advice.status === "insufficient_measurements" ? (
            <div className="scan-advice-insufficient" role="region" aria-label="Thiếu số đo để gợi ý size">
              <div className="scan-insufficient-header">
                <AlertCircle size={18} />
                <h4>Chưa đủ dữ liệu để gợi ý (cần số đo vòng mông)</h4>
              </div>
              <p>
                Sản phẩm <strong>{product?.name || "này"}</strong> là {isBottom ? "quần/chân váy" : "trang phục"} cần số đo vòng mông. Webcam thân trên chỉ ước lượng ngực và eo từ ảnh; không quan sát vòng mông thực tế.
              </p>
              <div className="scan-advice-actions">
                <button
                  className="scan-size-apply-btn scan-fullbody-btn"
                  type="button"
                  onClick={() => {
                    if (onResetFullBody) {
                      onResetFullBody();
                    } else {
                      onReset();
                    }
                  }}
                  disabled={deleting}
                >
                  <RotateCcw size={15} />
                  Quét lại toàn thân →
                </button>
                {onOpenSizeChart && (
                  <button
                    className="scan-btn-subtle"
                    type="button"
                    onClick={onOpenSizeChart}
                  >
                    Xem bảng size & chọn thủ công
                  </button>
                )}
              </div>
            </div>
          ) : advice.candidates && advice.candidates.length > 0 ? (
            <div className="scan-advice-success" role="region" aria-label="Size gợi ý">
              <div className="scan-advice-success-info">
                <span className="scan-advice-badge">
                  <Sparkles size={16} /> Gợi ý: Size {advice.candidates.join(", ")}
                </span>
                <span className="scan-advice-subnote">
                  Số đo của bạn vừa vặn với khoảng chuẩn trong bảng size.
                </span>
              </div>
              <div className="scan-advice-actions">
                {advice.candidates.map((size) => (
                  <button
                    key={size}
                    type="button"
                    className="scan-size-apply-btn"
                    onClick={() => onSelectSize(size)}
                  >
                    Áp dụng size {size} →
                  </button>
                ))}
                {onOpenSizeChart && (
                  <button
                    type="button"
                    className="scan-btn-subtle"
                    onClick={onOpenSizeChart}
                  >
                    Xem bảng size chi tiết
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="scan-advice-nomatch" role="region" aria-label="Không khớp size">
              <div className="scan-nomatch-header">
                <AlertCircle size={18} />
                <p>Không có size nào khớp tất cả số đo trong bảng. Bạn hãy xem bảng size hoặc chọn size thủ công theo sở thích.</p>
              </div>
              <div className="scan-advice-actions">
                {onOpenSizeChart && (
                  <button className="scan-size-apply-btn scan-manual-btn" type="button" onClick={onOpenSizeChart}>
                    Xem bảng size & chọn thủ công →
                  </button>
                )}
                <button className="scan-btn-subtle" type="button" onClick={onReset}>
                  <RotateCcw size={14} /> Quét lại
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Try-on: wardrobe | 3D stage | product + size + measurements + heatmap */}
      <div className="scan-workspace">
        <TryOnWardrobe
          products={wardrobeProducts}
          selectedId={product?.id || ""}
          size={activeFitSize}
          onSelect={onSelectProduct}
        />

        <div className="scan-stage">
          <div className="scan-stage-label">
            <b>
              MORPH<span> STUDIO</span>
            </b>
            <small>Mô hình ước lượng · tương tác 3D</small>
          </div>
          <div className="scan-tools">
            <button type="button" aria-pressed={rotate} onClick={() => setRotate(!rotate)}>
              <Rotate3D size={15} />
              {rotate ? "Dừng xoay" : "Tự xoay"}
            </button>
            <button
              type="button"
              onClick={() => {
                setReset((n) => n + 1);
                setRotate(false);
              }}
            >
              <RotateCcw size={15} />
              Đặt lại
            </button>
            <button type="button" aria-pressed={rings} onClick={() => setRings(!rings)}>
              <Ruler size={15} />
              Đường đo
            </button>
            <button
              type="button"
              aria-pressed={fitView}
              onClick={() => setFitView(!fitView)}
              disabled={!product || (!fitHeatmap && fitBands.length === 0)}
              title="Tô màu vùng chật/rộng theo size đang chọn"
            >
              <Paintbrush size={15} />
              Độ vừa
            </button>
            <button
              type="button"
              onClick={() => setMode(mode === "solid" ? "points" : mode === "points" ? "wire" : "solid")}
            >
              <Box size={15} />
              {mode === "solid" ? "Khối đặc" : mode === "points" ? "Điểm 3D" : "Khung lưới"}
            </button>
          </div>

          {active && (hasModel ? (
            <Boundary>
              <Viewer
                url={modelUrl}
                wireframe={mode === "wire"}
                points={mode === "points"}
                reset={reset}
                autoRotate={rotate}
                targetHeightCm={job.measurements?.height_cm}
                showRings={rings}
                technical
                annotations={rows}
                selectedMeasurement={selected}
                fitBands={fitView && !fitHeatmap && !isBottom ? fitBands : undefined}
                fitHeatmap={fitView ? fitHeatmap : undefined}
                onSelectView={() => setRotate(false)}
              />
            </Boundary>
          ) : (
            <p className="scan-loading">
              Mô hình 3D không còn khả dụng cho phiên này (phiên đã hết hạn hoặc đây là bản lưu số đo).
              Số đo và gợi ý size vẫn dùng được; hãy quét lại nếu cần xem hình thể.
            </p>
          ))}
          <p className="scan-stage-help">Kéo để xoay · Cuộn hoặc chạm để phóng to</p>
        </div>

        <aside className="tryon-panel" aria-label="Sản phẩm, size và số đo">
          {product && (
            <section className="tryon-product">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={product.image} alt="" width={56} height={56} />
              <div>
                <strong>{product.name}</strong>
                <small>{product.categoryName} · {product.sizes.join(" / ")}</small>
              </div>
            </section>
          )}

          {product ? (
            <FitBucketPanel
              fit={fitMap}
              size={activeFitSize}
              sizes={product.sizes}
              onSelectSize={(size) => {
                setFitSize(size);
                onSelectSize(size);
              }}
              loading={fitLoading}
              error={fitError}
            />
          ) : null}

          <section className="tryon-measures" aria-label="Số đo cơ thể">
            <div className="tryon-panel-head">
              <strong>
                Số đo <small>{rows.length}</small>
              </strong>
              <div className="scan-units" aria-label="Đơn vị">
                {["cm", "in"].map((u) => (
                  <button key={u} type="button" onClick={() => setUnit(u)} aria-pressed={unit === u}>
                    {u}
                  </button>
                ))}
              </div>
            </div>
            {notFromPhoto.length > 0 && (
              <p className="scan-provenance-warning" role="status">
                <AlertCircle size={14} aria-hidden="true" />
                <span>
                  Kết quả chưa dùng được ảnh cho: <b>{notFromPhoto.map((m) => m.label).join(", ")}</b>.
                  Hãy chụp lại theo hướng dẫn.
                </span>
              </p>
            )}
            <div className="scan-rows tryon-rows">
              {rows.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  className={selected === m.key ? "selected" : ""}
                  onClick={() => {
                    setSelected(selected === m.key ? "" : m.key);
                    setRings(true);
                  }}
                  disabled={!m.points_m.length}
                  aria-pressed={selected === m.key}
                  title={reason(m) || undefined}
                >
                  <i style={{ background: m.color }} />
                  <span>
                    {m.label}
                    <small>{SOURCE[m.source]}</small>
                  </span>
                  <b>
                    {value(m)}
                    <small>{m.value_cm != null ? unit : ""}</small>
                  </b>
                </button>
              ))}
            </div>
            <p className="scan-list-foot">“Mô hình mẫu” không phải số đo cơ thể được camera quan sát.</p>
          </section>

          <section className="tryon-explain" aria-label="Giải thích size">
            <div className="tryon-panel-head">
              <strong>Vì sao size này?</strong>
              {explain && (
                <span className={`tryon-explain-source is-${explain.source}`}>
                  {explain.source === "ai" ? "AI giải thích" : "Giải thích tự động"}
                </span>
              )}
            </div>
            {explainLoading && !explain ? (
              <p className="tryon-explain-text">Đang soạn giải thích…</p>
            ) : explain ? (
              <>
                <p className="tryon-explain-text">{explain.explanation}</p>
                {explain.basis.length > 0 && (
                  <ul className="tryon-explain-basis">
                    {explain.basis.map((item) => (
                      <li key={item.metric}>
                        {EXPLAIN_METRIC_LABEL[item.metric] || item.metric}: ease {item.ease_cm} cm
                      </li>
                    ))}
                  </ul>
                )}
                <p className="tryon-explain-note">
                  Chỉ giải thích dựa trên chênh lệch chu vi đã đo; không đề xuất size khác.
                </p>
              </>
            ) : (
              <p className="tryon-explain-text">
                Chọn áo và size để xem giải thích dựa trên chênh lệch chu vi (ease) từng mốc.
              </p>
            )}
          </section>
        </aside>
      </div>

      {/* Collapsible Technical Details & Data Export */}
      <details className="scan-technical-details">
        <summary>
          <SlidersHorizontal size={16} /> Bảng số đo chi tiết & Công cụ kỹ thuật
        </summary>
        <div className="scan-technical-content">
          <div className="scan-data-grid">
            {rows.map((m) => (
              <div key={m.key}>
                <span>{m.label}</span>
                <strong>
                  {value(m)}
                  <small>{m.value_cm != null ? unit : ""}</small>
                </strong>
                <small title={reason(m) || undefined}>{SOURCE[m.source]}</small>
              </div>
            ))}
          </div>

          <div className="scan-tech-actions">
            <a href={modelUrl} download className="scan-btn-subtle">
              <Download size={15} />
              Tải file GLB 3D
            </a>
            <a href={measurementsUrl} download className="scan-btn-subtle">
              <Download size={15} />
              Tải báo cáo JSON
            </a>
            <button type="button" onClick={copy} className="scan-btn-subtle">
              <Copy size={15} />
              Sao chép JSON
            </button>
            <button type="button" onClick={snapshot} className="scan-btn-subtle">
              <ImageIcon size={15} />
              Xuất ảnh PNG
            </button>
          </div>
        </div>
      </details>

      {(notice || error) && (
        <p role="status" className="scan-result-notice">
          {error || notice}
        </p>
      )}

      <details className="scan-limitations">
        <summary>Cách ước lượng & Giới hạn công nghệ</summary>
        {job.warnings?.map((w) => (
          <p key={w}>{w}</p>
        ))}
        <p>
          Mô hình không tái tạo khuôn mặt và chưa mô phỏng quần áo. Vòng đo mẫu được cắt ngang tại các mức giải phẫu giả
          định; chưa dùng cho may đo thủ công.
        </p>
      </details>
    </div>
  );
}


