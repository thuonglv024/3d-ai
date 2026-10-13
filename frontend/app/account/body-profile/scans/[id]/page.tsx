"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  Activity,
  ArrowLeft,
  Calendar,
  Clock,
  Trash2,
  Edit3,
  Scale,
  ShieldCheck,
  AlertTriangle,
  Info,
  LoaderCircle,
  Check,
  CheckCircle2,
  Camera,
  ExternalLink,
  ShoppingBag,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import Header from "../../../../../components/shop/Header";
import Footer from "../../../../../components/shop/Footer";
import CartDrawer from "../../../../../components/shop/CartDrawer";
import WishlistDrawer from "../../../../../components/shop/WishlistDrawer";
import ScanCompareModal from "../../../../../components/shop/ScanCompareModal";
import { useAuth } from "../../../../../lib/AuthContext";
import { useScan } from "../../../../../lib/ScanContext";
import { useDrawerA11y } from "../../../../../lib/useDrawerA11y";
import {
  type BodyScanDetail,
  type BodyScanSummary,
  fetchScanDetail,
  fetchUserScans,
  updateScanNote,
  deleteSavedScan,
  formatScanDateTime,
  getModeLabel,
  getSourceLabel,
  SOURCE_DESCRIPTIONS,
} from "../../../../../lib/userScansApi";

export default function ScanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { applySavedScanToSession } = useScan();

  const scanId = typeof params?.id === "string" ? params.id : Array.isArray(params?.id) ? params.id[0] : "";

  const [scan, setScan] = useState<BodyScanDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleApplyScanToShopping = () => {
    if (!scan) return;
    applySavedScanToSession(scan);
    router.push("/#catalog");
  };

  // Note Editing
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [noteSuccess, setNoteSuccess] = useState(false);
  const [noteError, setNoteError] = useState("");

  // Compare Modal & Previous Scan
  const [previousScan, setPreviousScan] = useState<BodyScanSummary | null>(null);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  // Delete Confirmation
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const deleteModalRef = useRef<HTMLDivElement>(null);

  useDrawerA11y(
    isDeleteModalOpen,
    () => {
      if (!deleting) setIsDeleteModalOpen(false);
    },
    deleteModalRef
  );

  // Fetch scan detail & previous scan
  useEffect(() => {
    if (!scanId || !user) return;

    let aborted = false;
    setLoading(true);
    setError(null);

    // 1. Fetch scan detail
    fetchScanDetail(scanId)
      .then((data) => {
        if (!aborted) {
          setScan(data);
          setNoteText(data.note || "");
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!aborted) {
          setError(err?.message || "Không thể tải thông tin lần scan.");
          setLoading(false);
        }
      });

    // 2. Fetch scans list to locate the previous scan for quick compare
    fetchUserScans({ page: 1, limit: 30 })
      .then((res) => {
        if (!aborted && res.items) {
          const currentIndex = res.items.findIndex((s) => s.id === scanId);
          if (currentIndex !== -1 && currentIndex + 1 < res.items.length) {
            // Next item in descending order is chronologically earlier
            setPreviousScan(res.items[currentIndex + 1]);
          } else if (currentIndex > 0) {
            // If this was the oldest, pick the newer one
            setPreviousScan(res.items[currentIndex - 1]);
          }
        }
      })
      .catch((err) => {
        console.warn("Could not load neighbor scans:", err);
      });

    return () => {
      aborted = true;
    };
  }, [scanId, user]);

  // Handle note save
  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scan) return;
    setSavingNote(true);
    setNoteError("");
    setNoteSuccess(false);

    try {
      const updated = await updateScanNote(scan.id, noteText.trim());
      setScan(updated);
      setNoteSuccess(true);
      setTimeout(() => setNoteSuccess(false), 3000);
    } catch (err: unknown) {
      const e = err as Error;
      setNoteError(e.message || "Không thể lưu ghi chú.");
    } finally {
      setSavingNote(false);
    }
  };

  // Handle delete
  const handleDeleteScan = async () => {
    if (!scan) return;
    setDeleting(true);
    setDeleteError("");

    try {
      await deleteSavedScan(scan.id);
      router.push("/account/body-profile");
    } catch (err: unknown) {
      const e = err as Error;
      setDeleteError(e.message || "Không thể xóa bản ghi scan.");
      setDeleting(false);
    }
  };

  return (
    <div className="account-page-layout">
      <Header />
      <CartDrawer />
      <WishlistDrawer />

      <main className="account-main-content">
        {/* Breadcrumb Navigation */}
        <nav className="account-breadcrumbs" aria-label="Đường dẫn">
          <Link href="/">Trang chủ</Link>
          <span className="bc-separator">/</span>
          <Link href="/account">Tài khoản</Link>
          <span className="bc-separator">/</span>
          <Link href="/account/body-profile">Hồ sơ hình thể</Link>
          <span className="bc-separator">/</span>
          <span className="bc-current">Chi tiết lần scan</span>
        </nav>

        {/* Loading State */}
        {loading && (
          <div className="account-auth-guard-box">
            <LoaderCircle size={44} className="spin-gold" />
            <p style={{ marginTop: 16 }}>Đang tải chi tiết số đo lần scan…</p>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="account-auth-guard-box">
            <AlertTriangle size={36} color="#9E2A2B" style={{ margin: "0 auto 16px auto" }} />
            <h2>Không thể tải bản ghi scan</h2>
            <p>{error}</p>
            <div className="guard-actions-row">
              <Link href="/account/body-profile" className="btn-gold-primary">
                Quay lại hồ sơ hình thể
              </Link>
            </div>
          </div>
        )}

        {/* Detail Content */}
        {!loading && !error && scan && (
          <>
            {/* Top Page Header & Actions */}
            <div className="account-header-area">
              <div className="account-header-title-box">
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <Link
                    href="/account/body-profile"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      color: "var(--account-text-secondary)",
                      fontSize: 13,
                      textDecoration: "none",
                    }}
                  >
                    <ArrowLeft size={14} /> Quay lại danh sách
                  </Link>
                </div>
                <h1>Chi tiết lần scan {formatScanDateTime(scan.captured_at)}</h1>
                <p className="account-header-subtitle">
                  Xem lại toàn bộ thông số nhân trắc học, độ tin cậy và nguồn gốc số đo được lưu trữ.
                </p>
              </div>

              <div className="account-header-actions">
                <button
                  type="button"
                  className="btn-gold-primary"
                  onClick={handleApplyScanToShopping}
                  title="Áp dụng số đo này để chọn size trang phục trong cửa hàng"
                >
                  <Sparkles size={16} /> Thử áp dụng số đo này để chọn size trang phục
                </button>
                {previousScan && (
                  <button
                    type="button"
                    className="btn-gold-secondary"
                    onClick={() => setIsCompareModalOpen(true)}
                  >
                    <Scale size={16} /> So sánh với lần {formatScanDateTime(previousScan.captured_at)}
                  </button>
                )}
                <button
                  type="button"
                  className="btn-danger-outline"
                  onClick={() => setIsDeleteModalOpen(true)}
                >
                  <Trash2 size={15} /> Xóa lần scan này
                </button>
              </div>
            </div>

            {/* Scan Card Container */}
            <div className="scan-detail-card">
              {/* Metadata 4-Column Grid */}
              <div className="meta-grid-four">
                <div className="meta-box-item">
                  <div className="meta-box-label">Thời gian chụp (Captured)</div>
                  <div className="meta-box-value">{formatScanDateTime(scan.captured_at)}</div>
                </div>

                <div className="meta-box-item">
                  <div className="meta-box-label">Thời gian lưu (Saved)</div>
                  <div className="meta-box-value">{formatScanDateTime(scan.saved_at)}</div>
                </div>

                <div className="meta-box-item">
                  <div className="meta-box-label">Chế độ chụp (Capture Mode)</div>
                  <div className="meta-box-value">
                    <span className="mode-pill">{getModeLabel(scan.capture_mode)}</span>
                  </div>
                </div>

                <div className="meta-box-item">
                  <div className="meta-box-label">Phiên bản Engine</div>
                  <div className="meta-box-value">
                    <code>{scan.engine_version}</code>
                  </div>
                </div>
              </div>

              {/* Warnings & Engine Notes (if any) */}
              {scan.warnings && scan.warnings.length > 0 && (
                <div className="compare-warning-banner" role="alert" style={{ marginBottom: 24 }}>
                  <AlertTriangle size={20} className="warning-icon" />
                  <div className="warning-text">
                    <strong>Lưu ý công nghệ ghi nhận trong phiên scan:</strong>
                    <ul>
                      {scan.warnings.map((w, idx) => (
                        <li key={`warn-${idx}`}>{w}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Full Measurements Table */}
              <div className="detail-measurements-table-wrapper">
                <table className="detail-measurements-table">
                  <caption className="sr-only">Bảng chi tiết các số đo hình thể</caption>
                  <thead>
                    <tr>
                      <th scope="col">Chỉ số số đo</th>
                      <th scope="col">Giá trị (cm)</th>
                      <th scope="col">Nguồn gốc số đo</th>
                      <th scope="col">Ghi chú & Phương pháp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scan.measurements && scan.measurements.length > 0 ? (
                      scan.measurements.map((m) => (
                        <tr key={`metric-${m.metric_key}`}>
                          <td style={{ fontWeight: 600, color: "var(--account-text)" }}>
                            {m.label}
                          </td>
                          <td>
                            {m.value_cm !== null ? (
                              <strong style={{ fontSize: 16 }}>{m.value_cm} cm</strong>
                            ) : (
                              <span className="text-muted" style={{ fontStyle: "italic" }}>
                                Không khả dụng
                              </span>
                            )}
                          </td>
                          <td>
                            <span className={`metric-source-badge badge-${m.source}`}>
                              {getSourceLabel(m.source)}
                            </span>
                          </td>
                          <td style={{ color: "var(--account-text-secondary)", fontSize: 12.5 }}>
                            {m.source === "template_model"
                              ? "Theo mô hình mẫu MakeHuman gốc (không phải số đo cơ thể thực tế được quan sát)."
                              : SOURCE_DESCRIPTIONS[m.source] || "Ước lượng qua thị giác máy tính."}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} style={{ textAlign: "center", padding: 24, color: "var(--account-text-muted)" }}>
                          Không có dữ liệu số đo chi tiết cho phiên này.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Size Fitting CTA Section */}
              <div className="detail-size-fitting-card">
                <div className="fitting-card-left">
                  <div className="fitting-badge-gold">
                    <Sparkles size={16} /> Chọn size trang phục với số đo này
                  </div>
                  <h3>Thử áp dụng số đo này để chọn size trang phục</h3>
                  <p>
                    Hệ thống sẽ lấy các số đo {scan.capture_mode === "upper_body" ? "thân trên thực tế (ngực, eo, rộng vai)" : "toàn thân thực tế (ngực, eo, mông, vai)"} từ phiên scan này để đối chiếu tự động với bảng size sản phẩm trong catalog.
                  </p>
                </div>
                <div className="fitting-card-actions">
                  <button
                    type="button"
                    className="btn-gold-primary"
                    onClick={handleApplyScanToShopping}
                  >
                    <ShoppingBag size={16} /> Thử áp dụng số đo này để chọn size trang phục <ArrowRight size={15} />
                  </button>
                  <Link href="/scan" className="btn-gold-secondary">
                    <Camera size={16} /> Mở phòng thử 3D độc lập
                  </Link>
                </div>
              </div>

              {/* Personal Note Editor */}
              <div className="note-editor-card">
                <h4>Ghi chú cá nhân cho lần scan này</h4>
                <p style={{ fontSize: 13, color: "var(--account-text-secondary)", margin: "0 0 12px 0" }}>
                  Lưu lại hoàn cảnh đo (ví dụ: &quot;Đo buổi sáng chưa ăn&quot;, &quot;Đo sau buổi tập gym&quot;, &quot;Mặc đồ mỏng sát người&quot;) để đối chiếu chính xác hơn.
                </p>

                <form onSubmit={handleSaveNote}>
                  <textarea
                    className="note-textarea"
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Nhập ghi chú của bạn…"
                    rows={3}
                    disabled={savingNote}
                  />

                  {noteError && (
                    <p style={{ color: "#9E2A2B", fontSize: 12, margin: "0 0 8px 0" }}>
                      {noteError}
                    </p>
                  )}

                  {noteSuccess && (
                    <p style={{ color: "#194E3D", fontSize: 12, fontWeight: 600, margin: "0 0 8px 0" }}>
                      ✓ Đã lưu ghi chú thành công.
                    </p>
                  )}

                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <button type="submit" className="btn-gold-primary" disabled={savingNote}>
                      {savingNote ? <LoaderCircle size={15} className="spin-gold" /> : <Check size={15} />}{" "}
                      Lưu ghi chú
                    </button>
                  </div>
                </form>
              </div>

              {/* Disclaimer */}
              <div className="chart-disclaimer-bar">
                <Info size={16} className="disclaimer-icon" />
                <span className="disclaimer-text">
                  Số đo được ước lượng bằng thị giác máy tính từ ảnh và mô hình MakeHuman, không phải
                  phép đo nhân trắc học chính xác hay may đo y tế. Các thông số từ template_model
                  không thể dùng để theo dõi biến thiên cơ thể.
                </span>
              </div>
            </div>
          </>
        )}
      </main>

      <Footer />

      {/* =================================================================
          MODAL: So sánh với lần scan trước đó
         ================================================================= */}
      {previousScan && (
        <ScanCompareModal
          isOpen={isCompareModalOpen}
          onClose={() => setIsCompareModalOpen(false)}
          scanAId={previousScan.id}
          scanBId={scanId}
        />
      )}

      {/* =================================================================
          MODAL: Xác nhận xóa lần scan
         ================================================================= */}
      {isDeleteModalOpen && scan && (
        <div
          className="compare-modal-backdrop"
          onClick={() => !deleting && setIsDeleteModalOpen(false)}
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="delete-scan-title"
          aria-describedby="delete-scan-desc"
        >
          <div
            ref={deleteModalRef}
            tabIndex={-1}
            className="confirm-modal-box"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="confirm-icon-danger">
              <Trash2 size={28} />
            </div>
            <h3 id="delete-scan-title">Xóa bản ghi scan này?</h3>
            <p id="delete-scan-desc">
              Bạn có chắc chắn muốn xóa bản ghi scan ngày{" "}
              <strong>{formatScanDateTime(scan.captured_at)}</strong> không? Hành động này không thể
              hoàn tác.
            </p>

            {deleteError && (
              <p style={{ color: "#9E2A2B", fontSize: 13, marginBottom: 16 }}>{deleteError}</p>
            )}

            <div className="confirm-actions-row">
              <button
                type="button"
                className="btn-gold-secondary"
                onClick={() => setIsDeleteModalOpen(false)}
                disabled={deleting}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn-danger-outline"
                style={{ backgroundColor: "#9E2A2B", color: "#FFFFFF", borderColor: "#9E2A2B" }}
                onClick={handleDeleteScan}
                disabled={deleting}
              >
                {deleting ? <LoaderCircle size={15} className="spin-gold" /> : <Trash2 size={15} />}{" "}
                Xác nhận xóa
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
