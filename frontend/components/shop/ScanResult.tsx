"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Component, useRef, useState, useEffect, type ReactNode } from "react";
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
} from "lucide-react";
import type { Job, MeasurementDetail } from "../../lib/useBodyScan";
import type { Product } from "../../lib/catalog";
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
  photo_estimate: "Ước lượng từ ảnh",
  photo_with_prior: "Ảnh + tỷ lệ mẫu",
  template_model: "Theo mẫu 3D",
  unavailable: "Chưa đủ dữ liệu",
};

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <p className="scan-loading">Không mở được 3D. Số đo và file tải xuống vẫn khả dụng.</p>
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
}) {
  const host = useRef<HTMLDivElement>(null);
  const [rotate, setRotate] = useState(false);
  const [rings, setRings] = useState(true);
  const [mode, setMode] = useState("solid");
  const [reset, setReset] = useState(0);
  const [unit, setUnit] = useState("cm");
  const [selected, setSelected] = useState("");
  const [notice, setNotice] = useState("");
  const [loadingTimedOut, setLoadingTimedOut] = useState(false);

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

  const router = useRouter();
  const { user } = useAuth();
  const { savedScans, saveErrors, saveScanToProfile, getGuestToken } = useScan();
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

  const rows = job.body_profile?.measurement_details || [];
  const upper = job.body_profile?.capture_mode === "upper_body";
  const value = (m: MeasurementDetail) =>
    m.value_cm == null ? "—" : (m.value_cm / (unit === "in" ? 2.54 : 1)).toFixed(1);

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

  const isBottom = product?.chart?.garment === "bottom";

  return (
    <div className="scan-result" ref={host}>
      <header className="scan-result-heading">
        <div>
          <h2>Hình thể 3D của bạn</h2>
          <p>
            {job.measurements?.height_cm} cm · {upper ? "Webcam thân trên" : "Ảnh toàn thân"} · Mô hình ước lượng
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

      {/* 3D Workspace */}
      <div className="scan-workspace">
        <aside className="scan-measure-list" aria-label="Danh sách số đo">
          <div className="scan-list-title">
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
          <p>Chọn một dòng để làm nổi đường đo tương ứng trên hình thể.</p>
          <div className="scan-rows">
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
          <p className="scan-list-foot">“Theo mẫu 3D” không phải số đo cơ thể được camera quan sát.</p>
        </aside>

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
              onClick={() => setMode(mode === "solid" ? "points" : mode === "points" ? "wire" : "solid")}
            >
              <Box size={15} />
              {mode === "solid" ? "Khối đặc" : mode === "points" ? "Điểm 3D" : "Khung lưới"}
            </button>
          </div>

          {active && (
            <Boundary>
              <Viewer
                url={job.model_url}
                wireframe={mode === "wire"}
                points={mode === "points"}
                reset={reset}
                autoRotate={rotate}
                targetHeightCm={job.measurements?.height_cm}
                showRings={rings}
                technical
                annotations={rows}
                selectedMeasurement={selected}
                onSelectView={() => setRotate(false)}
              />
            </Boundary>
          )}
          <p className="scan-stage-help">Kéo để xoay · Cuộn hoặc chụm để phóng to</p>
        </div>
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
                <small>{SOURCE[m.source]}</small>
              </div>
            ))}
          </div>

          <div className="scan-tech-actions">
            <a href={job.model_url} download className="scan-btn-subtle">
              <Download size={15} />
              Tải file GLB 3D
            </a>
            <a href={`/api/scans/${job.id}/measurements`} download className="scan-btn-subtle">
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
