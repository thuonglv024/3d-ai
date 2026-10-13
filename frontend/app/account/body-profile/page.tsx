"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  Calendar,
  Camera,
  Trash2,
  Edit3,
  ExternalLink,
  Scale,
  Sparkles,
  Info,
  Clock,
  CheckCircle2,
  AlertTriangle,
  LoaderCircle,
  X,
  Check,
  ArrowRight,
  User as UserIcon,
  ShoppingBag,
} from "lucide-react";
import Header from "../../../components/shop/Header";
import Footer from "../../../components/shop/Footer";
import CartDrawer from "../../../components/shop/CartDrawer";
import WishlistDrawer from "../../../components/shop/WishlistDrawer";
import BodyChart from "../../../components/shop/BodyChart";
import ScanCompareModal from "../../../components/shop/ScanCompareModal";
import { useAuth } from "../../../lib/AuthContext";
import { useScan } from "../../../lib/ScanContext";
import {
  type BodyScanSummary,
  type ChartTimelinePoint,
  fetchUserScans,
  fetchChartData,
  deleteSavedScan,
  updateScanNote,
  formatScanDateTime,
  formatScanDate,
  formatScanTime,
  getModeLabel,
  getSourceLabel,
} from "../../../lib/userScansApi";

export default function BodyProfilePage() {
  const router = useRouter();
  const { user, loading: authLoading, updateProfile } = useAuth();
  const { applySavedScanToSession } = useScan();

  const handleApplyScanSummary = (s: BodyScanSummary) => {
    const measList: { metric_key: string; label: string; value_cm: number | null; source: string }[] = [];
    if (s.key_measurements.chest_cm != null) {
      measList.push({
        metric_key: "chest_cm",
        label: "Vòng ngực",
        value_cm: s.key_measurements.chest_cm,
        source: s.capture_mode === "upper_body" ? "photo_with_prior" : "photo_estimate",
      });
    }
    if (s.key_measurements.waist_cm != null) {
      measList.push({
        metric_key: "waist_cm",
        label: "Vòng eo",
        value_cm: s.key_measurements.waist_cm,
        source: s.capture_mode === "upper_body" ? "photo_with_prior" : "photo_estimate",
      });
    }
    if (s.key_measurements.hip_cm != null && s.capture_mode === "full_body") {
      measList.push({
        metric_key: "hip_cm",
        label: "Vòng mông",
        value_cm: s.key_measurements.hip_cm,
        source: "photo_estimate",
      });
    }
    if (s.key_measurements.shoulder_width_cm != null) {
      measList.push({
        metric_key: "shoulder_width_cm",
        label: "Rộng vai",
        value_cm: s.key_measurements.shoulder_width_cm,
        source: s.capture_mode === "upper_body" ? "photo_with_prior" : "photo_estimate",
      });
    }
    applySavedScanToSession({
      id: s.id,
      source_scan_id: s.source_scan_id,
      capture_mode: s.capture_mode,
      height_input_cm: s.height_input_cm,
      measurements: measList,
    });
    router.push("/#catalog");
  };

  // Scans List & Latest State
  const [scans, setScans] = useState<BodyScanSummary[]>([]);
  const [totalScans, setTotalScans] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState("");

  // Chart State
  const [chartRange, setChartRange] = useState<"30d" | "90d" | "all">("all");
  const [chartTimeline, setChartTimeline] = useState<ChartTimelinePoint[]>([]);
  const [chartDisclaimer, setChartDisclaimer] = useState("");
  const [loadingChart, setLoadingChart] = useState(true);

  // Compare Selection State
  const [selectedScanIds, setSelectedScanIds] = useState<string[]>([]);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  // Delete Confirmation Modal State
  const [scanToDelete, setScanToDelete] = useState<BodyScanSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  // Note Edit Modal State
  const [scanToEditNote, setScanToEditNote] = useState<BodyScanSummary | null>(null);
  const [noteInput, setNoteInput] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [noteError, setNoteError] = useState("");

  // Quick auto-save toggle state
  const [togglingAutoSave, setTogglingAutoSave] = useState(false);

  // Global Notification Toast
  const [notification, setNotification] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const showToast = (type: "success" | "error", text: string) => {
    setNotification({ type, text });
    setTimeout(() => setNotification(null), 4000);
  };

  // Load Scan List
  const loadScans = useCallback(async () => {
    if (!user) return;
    setLoadingList(true);
    setListError("");
    try {
      const data = await fetchUserScans({ page: 1, limit: 30 });
      setScans(data.items || []);
      setTotalScans(data.total || 0);
    } catch (err: unknown) {
      const e = err as Error;
      if (e.message !== "UNAUTHORIZED") {
        setListError(e.message || "Không thể tải danh sách lần scan.");
      }
    } finally {
      setLoadingList(false);
    }
  }, [user]);

  // Load Chart Data
  const loadChart = useCallback(async (range: "30d" | "90d" | "all") => {
    if (!user) return;
    setLoadingChart(true);
    try {
      const data = await fetchChartData(range);
      setChartTimeline(data.timeline || []);
      setChartDisclaimer(data.disclaimer || "");
    } catch (err: unknown) {
      console.warn("Could not load chart data:", err);
    } finally {
      setLoadingChart(false);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      loadScans();
      loadChart(chartRange);
    }
  }, [user, loadScans, loadChart, chartRange]);

  const handleRangeChange = (range: "30d" | "90d" | "all") => {
    setChartRange(range);
  };

  // Toggle selection for comparison (max 2)
  const toggleSelectForCompare = (scanId: string) => {
    setSelectedScanIds((prev) => {
      if (prev.includes(scanId)) {
        return prev.filter((id) => id !== scanId);
      }
      if (prev.length >= 2) {
        // Replace second selection
        return [prev[0], scanId];
      }
      return [...prev, scanId];
    });
  };

  // Quick auto-save toggle handler
  const handleToggleAutoSave = async () => {
    if (!user || togglingAutoSave) return;
    const nextVal = !user.auto_save_scans;
    setTogglingAutoSave(true);
    try {
      const ok = await updateProfile({ auto_save_scans: nextVal });
      if (ok) {
        showToast("success", nextVal ? "Đã bật tự động lưu scan" : "Đã tắt tự động lưu scan");
      }
    } catch {
      showToast("error", "Lỗi cập nhật cài đặt");
    } finally {
      setTogglingAutoSave(false);
    }
  };

  // Handle Delete Confirmation
  const confirmDelete = async () => {
    if (!scanToDelete) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteSavedScan(scanToDelete.id);
      showToast("success", "Đã xóa bản ghi scan thành công.");
      setScanToDelete(null);
      // Remove from state immediately
      setScans((prev) => prev.filter((s) => s.id !== scanToDelete.id));
      setTotalScans((prev) => Math.max(0, prev - 1));
      setSelectedScanIds((prev) => prev.filter((id) => id !== scanToDelete.id));
      // Refresh chart
      loadChart(chartRange);
    } catch (err: unknown) {
      const e = err as Error;
      setDeleteError(e.message || "Xóa thất bại. Bản ghi vẫn được giữ nguyên.");
      showToast("error", "Không thể xóa lần scan. Vui lòng thử lại.");
    } finally {
      setDeleting(false);
    }
  };

  // Handle Save Note
  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scanToEditNote) return;
    setSavingNote(true);
    setNoteError("");
    try {
      const updated = await updateScanNote(scanToEditNote.id, noteInput.trim());
      // Update in list
      setScans((prev) =>
        prev.map((s) => (s.id === updated.id ? { ...s, note: updated.note } : s))
      );
      showToast("success", "Đã cập nhật ghi chú lần scan.");
      setScanToEditNote(null);
    } catch (err: unknown) {
      const e = err as Error;
      setNoteError(e.message || "Không thể cập nhật ghi chú.");
    } finally {
      setSavingNote(false);
    }
  };

  // Latest scan is the first item in scans array
  const latestScan = scans.length > 0 ? scans[0] : null;

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
          <span className="bc-current">Hồ sơ hình thể & Biểu đồ</span>
        </nav>

        {/* Global Toast Notification */}
        {notification && (
          <div
            style={{
              padding: "12px 20px",
              borderRadius: "12px",
              marginBottom: "20px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              fontSize: "14px",
              fontWeight: 500,
              backgroundColor: notification.type === "success" ? "#EEF6EE" : "#FBEFED",
              color: notification.type === "success" ? "#194E3D" : "#9E2A2B",
              border: `1px solid ${notification.type === "success" ? "#C6E1C6" : "#F5C6C6"}`,
              boxShadow: "0 2px 8px rgba(0, 0, 0, 0.05)",
            }}
          >
            {notification.type === "success" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            <span>{notification.text}</span>
          </div>
        )}

        {/* Auth Loading Guard */}
        {authLoading && (
          <div className="account-auth-guard-box">
            <LoaderCircle size={44} className="spin-gold" />
            <p style={{ marginTop: 16 }}>Đang tải dữ liệu hồ sơ hình thể…</p>
          </div>
        )}

        {/* Unauthenticated State */}
        {!authLoading && !user && (
          <div className="account-auth-guard-box">
            <div className="guard-icon-circle">
              <Activity size={32} />
            </div>
            <h2>Hồ sơ hình thể & Theo dõi số đo</h2>
            <p>
              Vui lòng đăng nhập để lưu trữ kết quả quét 3D, theo dõi biểu đồ biến thiên số đo ngực,
              eo, mông và đối chiếu sự thay đổi qua từng thời kỳ.
            </p>
            <div className="guard-actions-row">
              <Link href="/auth/login?returnTo=/account/body-profile" className="btn-gold-primary">
                Đăng nhập để xem hồ sơ
              </Link>
              <Link href="/scan" className="btn-gold-secondary">
                <Camera size={16} /> Quét thử không cần tài khoản
              </Link>
            </div>
          </div>
        )}

        {/* Authenticated Body Profile Interface */}
        {!authLoading && user && (
          <>
            {/* Top Page Header */}
            <div className="account-header-area">
              <div className="account-header-title-box">
                <h1>Hồ sơ hình thể & Biểu đồ số đo</h1>
                <p className="account-header-subtitle">
                  Theo dõi số đo thực tế, biểu đồ biến thiên qua các lần scan webcam và đối chiếu 2
                  thời điểm bất kỳ.
                </p>
              </div>

              <div className="account-header-actions">
                <Link href="/scan" className="btn-gold-primary">
                  <Camera size={16} /> Scan mới
                </Link>
                {selectedScanIds.length === 2 && (
                  <button
                    type="button"
                    className="btn-gold-secondary"
                    onClick={() => setIsCompareModalOpen(true)}
                  >
                    <Scale size={16} /> So sánh 2 lần đã chọn
                  </button>
                )}
              </div>
            </div>

            {/* Empty State when 0 scans */}
            {!loadingList && scans.length === 0 ? (
              <div className="history-empty-state">
                <Activity size={48} strokeWidth={1.5} />
                <h4>Bạn chưa lưu lần scan nào</h4>
                <p>
                  Hãy thực hiện phiên quét hình thể 3D đầu tiên qua webcam. Bạn sẽ nhận được các số
                  đo tham khảo và theo dõi sự thay đổi theo thời gian.
                </p>
                <Link href="/scan" className="btn-gold-primary">
                  <Camera size={16} /> Bắt đầu scan ngay
                </Link>
              </div>
            ) : (
              <>
                {/* =================================================================
                    PHẦN 1: HERO CARD - SỐ ĐO MỚI NHẤT
                   ================================================================= */}
                {latestScan && (
                  <section className="latest-measurements-hero" aria-label="Số đo lần scan gần nhất">
                    <div className="hero-top-bar">
                      <div className="hero-title-box">
                        <span className="hero-badge-tag">
                          <Sparkles size={12} /> Số đo gần nhất
                        </span>
                        <h2>Lần scan ngày {formatScanDate(latestScan.captured_at)}</h2>
                        <div className="hero-date-banner">
                          <Clock size={15} />
                          <span>
                            Chụp thực tế lúc{" "}
                            <strong>{formatScanDateTime(latestScan.captured_at)}</strong> • Chế độ:{" "}
                            <strong>{getModeLabel(latestScan.capture_mode)}</strong> • Engine:{" "}
                            <code>{latestScan.engine_version}</code>
                          </span>
                        </div>
                      </div>

                      <div className="hero-actions-box">
                        <button
                          type="button"
                          className="btn-gold-secondary"
                          onClick={() => handleApplyScanSummary(latestScan)}
                          title="Áp dụng số đo gần nhất này để chọn size khi xem catalog"
                        >
                          <ShoppingBag size={15} /> Thử áp dụng số đo này để chọn size
                        </button>
                        <Link href="/scan" className="btn-gold-primary">
                          <Camera size={16} /> Scan mới
                        </Link>
                      </div>
                    </div>

                    {/* Metric Cards Row */}
                    <div className="hero-metrics-grid">
                      {/* Chiều cao */}
                      <div className="metric-card-item">
                        <div className="metric-card-header">Chiều cao</div>
                        <div className="metric-card-value">
                          <span className="val-big">{latestScan.height_input_cm}</span>
                          <span className="val-unit">cm</span>
                        </div>
                        <span className="metric-source-badge badge-user_input">
                          {getSourceLabel("user_input")}
                        </span>
                      </div>

                      {/* Vòng ngực */}
                      <div className="metric-card-item">
                        <div className="metric-card-header">Vòng ngực</div>
                        <div className="metric-card-value">
                          {latestScan.key_measurements?.chest_cm ? (
                            <>
                              <span className="val-big">{latestScan.key_measurements.chest_cm}</span>
                              <span className="val-unit">cm</span>
                            </>
                          ) : (
                            <span className="val-null">Chưa có</span>
                          )}
                        </div>
                        <span className="metric-source-badge badge-photo_with_prior">
                          {latestScan.capture_mode === "upper_body"
                            ? getSourceLabel("photo_with_prior")
                            : getSourceLabel("photo_estimate")}
                        </span>
                      </div>

                      {/* Vòng eo */}
                      <div className="metric-card-item">
                        <div className="metric-card-header">Vòng eo</div>
                        <div className="metric-card-value">
                          {latestScan.key_measurements?.waist_cm ? (
                            <>
                              <span className="val-big">{latestScan.key_measurements.waist_cm}</span>
                              <span className="val-unit">cm</span>
                            </>
                          ) : (
                            <span className="val-null">Chưa có</span>
                          )}
                        </div>
                        <span className="metric-source-badge badge-photo_with_prior">
                          {latestScan.capture_mode === "upper_body"
                            ? getSourceLabel("photo_with_prior")
                            : getSourceLabel("photo_estimate")}
                        </span>
                      </div>

                      {/* Vòng mông */}
                      <div className="metric-card-item">
                        <div className="metric-card-header">Vòng mông</div>
                        <div className="metric-card-value">
                          {latestScan.capture_mode === "upper_body" ? (
                            <span
                              className="val-null"
                              title="Chế độ chụp thân trên không ước lượng vòng mông thực tế"
                            >
                              Chưa đo (Thân trên)
                            </span>
                          ) : latestScan.key_measurements?.hip_cm ? (
                            <>
                              <span className="val-big">{latestScan.key_measurements.hip_cm}</span>
                              <span className="val-unit">cm</span>
                            </>
                          ) : (
                            <span className="val-null">Chưa có</span>
                          )}
                        </div>
                        <span
                          className={`metric-source-badge ${
                            latestScan.capture_mode === "upper_body"
                              ? "badge-template_model"
                              : "badge-photo_estimate"
                          }`}
                        >
                          {latestScan.capture_mode === "upper_body"
                            ? "Theo mẫu 3D"
                            : getSourceLabel("photo_estimate")}
                        </span>
                      </div>

                      {/* Rộng vai */}
                      <div className="metric-card-item">
                        <div className="metric-card-header">Rộng vai</div>
                        <div className="metric-card-value">
                          {latestScan.key_measurements?.shoulder_width_cm ? (
                            <>
                              <span className="val-big">
                                {latestScan.key_measurements.shoulder_width_cm}
                              </span>
                              <span className="val-unit">cm</span>
                            </>
                          ) : (
                            <span className="val-null">Chưa có</span>
                          )}
                        </div>
                        <span className="metric-source-badge badge-photo_with_prior">
                          {latestScan.capture_mode === "upper_body"
                            ? getSourceLabel("photo_with_prior")
                            : getSourceLabel("photo_estimate")}
                        </span>
                      </div>
                    </div>

                    {/* Quick Setting Auto-Save Toggle */}
                    <div className="hero-quick-toggle-row">
                      <span>Tự động lưu các lần scan tiếp theo:</span>
                      <label className="toggle-switch-wrapper">
                        <input
                          type="checkbox"
                          checked={user.auto_save_scans}
                          onChange={handleToggleAutoSave}
                          disabled={togglingAutoSave}
                          aria-label="Tự động lưu các lần scan sau"
                        />
                        <span className="toggle-slider"></span>
                      </label>
                      <strong>{user.auto_save_scans ? "Đang bật" : "Đang tắt"}</strong>
                    </div>
                  </section>
                )}

                {/* =================================================================
                    PHẦN 2: BIỂU ĐỒ THAY ĐỔI SỐ ĐO THEO THỜI GIAN
                   ================================================================= */}
                <section aria-label="Biểu đồ biến thiên số đo">
                  {loadingChart ? (
                    <div className="body-chart-card" style={{ textAlign: "center", padding: "48px 0" }}>
                      <LoaderCircle size={36} className="spin-gold" />
                      <p style={{ marginTop: 12, color: "var(--account-text-secondary)" }}>
                        Đang xây dựng biểu đồ số đo…
                      </p>
                    </div>
                  ) : (
                    <BodyChart
                      timeline={chartTimeline}
                      range={chartRange}
                      onRangeChange={handleRangeChange}
                      onSelectScan={(scanId) => router.push(`/account/body-profile/scans/${scanId}`)}
                      disclaimer={chartDisclaimer}
                    />
                  )}
                </section>

                {/* =================================================================
                    PHẦN 3: DANH SÁCH LỊCH SỬ SCAN & CÔNG CỤ SO SÁNH
                   ================================================================= */}
                <section aria-label="Lịch sử các lần scan">
                  <div className="history-section-header">
                    <div className="history-title-box">
                      <h3>Lịch sử các lần scan ({totalScans})</h3>
                      <p className="history-subtitle">
                        Tích chọn 2 lần scan bất kỳ để so sánh đối chiếu số đo trước và sau.
                      </p>
                    </div>

                    {selectedScanIds.length > 0 && (
                      <div className="compare-bar-actions">
                        <button
                          type="button"
                          className="btn-clear-selection"
                          onClick={() => setSelectedScanIds([])}
                        >
                          Bỏ chọn ({selectedScanIds.length})
                        </button>
                        {selectedScanIds.length === 2 && (
                          <button
                            type="button"
                            className="btn-gold-primary"
                            onClick={() => setIsCompareModalOpen(true)}
                          >
                            <Scale size={16} /> So sánh 2 lần scan này
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Floating Notification Bar when 1 or 2 scans selected */}
                  {selectedScanIds.length > 0 && (
                    <div className="compare-selection-bar" role="status">
                      <div className="compare-bar-info">
                        <Scale size={18} />
                        <span>
                          {selectedScanIds.length === 1
                            ? "Đã chọn 1 lần scan. Hãy tích chọn thêm 1 lần scan nữa để so sánh."
                            : "Đã chọn đủ 2 lần scan để đối chiếu sự thay đổi số đo."}
                        </span>
                      </div>
                      <div className="compare-bar-actions">
                        {selectedScanIds.length === 2 && (
                          <button
                            type="button"
                            className="btn-compare-trigger"
                            onClick={() => setIsCompareModalOpen(true)}
                          >
                            Mở bảng so sánh <ArrowRight size={14} />
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn-clear-selection"
                          onClick={() => setSelectedScanIds([])}
                        >
                          Hủy chọn
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Cards List */}
                  <div className="history-cards-list">
                    {scans.map((scan) => {
                      const isSelected = selectedScanIds.includes(scan.id);
                      const km = scan.key_measurements;

                      return (
                        <div
                          key={`scan-card-${scan.id}`}
                          className={`scan-history-card ${isSelected ? "is-selected-for-compare" : ""}`}
                        >
                          {/* Selection Checkbox */}
                          <div className="scan-card-select-col">
                            <input
                              type="checkbox"
                              className="custom-checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelectForCompare(scan.id)}
                              aria-label={`Chọn lần scan ngày ${formatScanDateTime(scan.captured_at)} để so sánh`}
                            />
                          </div>

                          {/* Card Content */}
                          <div className="scan-card-content">
                            <div className="scan-card-top-row">
                              <span className="scan-card-time">
                                {formatScanDateTime(scan.captured_at)}
                              </span>
                              <span className="scan-card-meta-pill">
                                {getModeLabel(scan.capture_mode)}
                              </span>
                              <span className="scan-card-meta-pill">
                                Engine {scan.engine_version}
                              </span>
                              {scan.note && (
                                <span className="scan-card-note">
                                  &quot;{scan.note}&quot;
                                </span>
                              )}
                            </div>

                            {/* Key Measurements Row */}
                            <div className="scan-card-metrics-row">
                              <span className="scan-card-metric-badge">
                                Ngực: <strong>{km?.chest_cm ? `${km.chest_cm} cm` : "--"}</strong>
                              </span>
                              <span className="scan-card-metric-badge">
                                Eo: <strong>{km?.waist_cm ? `${km.waist_cm} cm` : "--"}</strong>
                              </span>
                              <span className="scan-card-metric-badge">
                                Mông:{" "}
                                <strong>
                                  {scan.capture_mode === "upper_body"
                                    ? "Mẫu 3D"
                                    : km?.hip_cm
                                    ? `${km.hip_cm} cm`
                                    : "--"}
                                </strong>
                              </span>
                              <span className="scan-card-metric-badge">
                                Rộng vai:{" "}
                                <strong>
                                  {km?.shoulder_width_cm ? `${km.shoulder_width_cm} cm` : "--"}
                                </strong>
                              </span>
                              <span className="scan-card-metric-badge">
                                Cao: <strong>{scan.height_input_cm} cm</strong>
                              </span>
                            </div>
                          </div>

                          {/* Actions Column */}
                          <div className="scan-card-actions-col">
                            <button
                              type="button"
                              className="btn-action-icon"
                              title="Thử áp dụng số đo lần này để chọn size trang phục"
                              aria-label="Thử áp dụng số đo chọn size"
                              onClick={() => handleApplyScanSummary(scan)}
                            >
                              <ShoppingBag size={16} />
                            </button>
                            <Link
                              href={`/account/body-profile/scans/${scan.id}`}
                              className="btn-action-icon"
                              title="Xem chi tiết lần scan"
                              aria-label="Xem chi tiết"
                            >
                              <ExternalLink size={16} />
                            </Link>
                            <button
                              type="button"
                              className="btn-action-icon"
                              title="Chỉnh sửa ghi chú"
                              aria-label="Chỉnh sửa ghi chú"
                              onClick={() => {
                                setScanToEditNote(scan);
                                setNoteInput(scan.note || "");
                              }}
                            >
                              <Edit3 size={16} />
                            </button>
                            <button
                              type="button"
                              className="btn-action-icon is-danger"
                              title="Xóa lần scan này"
                              aria-label="Xóa lần scan"
                              onClick={() => setScanToDelete(scan)}
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              </>
            )}
          </>
        )}
      </main>

      <Footer />

      {/* =================================================================
          MODAL: So sánh 2 lần scan
         ================================================================= */}
      <ScanCompareModal
        isOpen={isCompareModalOpen}
        onClose={() => setIsCompareModalOpen(false)}
        scanAId={selectedScanIds[0] || null}
        scanBId={selectedScanIds[1] || null}
      />

      {/* =================================================================
          MODAL: Xác nhận xóa lần scan
         ================================================================= */}
      {scanToDelete && (
        <div className="compare-modal-backdrop" onClick={() => !deleting && setScanToDelete(null)}>
          <div className="confirm-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="confirm-icon-danger">
              <Trash2 size={28} />
            </div>
            <h3>Xóa bản ghi scan?</h3>
            <p>
              Bạn có chắc chắn muốn xóa bản ghi scan ngày{" "}
              <strong>{formatScanDateTime(scanToDelete.captured_at)}</strong> không? Toàn bộ số đo
              và lịch sử của lần quét này sẽ bị xóa khỏi hồ sơ vĩnh viễn.
            </p>

            {deleteError && (
              <p style={{ color: "#9E2A2B", fontSize: 13, marginBottom: 16 }}>{deleteError}</p>
            )}

            <div className="confirm-actions-row">
              <button
                type="button"
                className="btn-gold-secondary"
                onClick={() => setScanToDelete(null)}
                disabled={deleting}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className="btn-danger-outline"
                style={{ backgroundColor: "#9E2A2B", color: "#FFFFFF", borderColor: "#9E2A2B" }}
                onClick={confirmDelete}
                disabled={deleting}
              >
                {deleting ? <LoaderCircle size={15} className="spin-gold" /> : <Trash2 size={15} />} Xác nhận xóa
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================
          MODAL: Chỉnh sửa ghi chú cá nhân
         ================================================================= */}
      {scanToEditNote && (
        <div className="compare-modal-backdrop" onClick={() => !savingNote && setScanToEditNote(null)}>
          <div className="confirm-modal-box" style={{ maxWidth: 480, textAlign: "left" }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: 4 }}>Ghi chú lần scan</h3>
            <p style={{ fontSize: 13, color: "var(--account-text-secondary)", marginBottom: 16 }}>
              Lần quét: {formatScanDateTime(scanToEditNote.captured_at)}
            </p>

            <form onSubmit={handleSaveNote}>
              <textarea
                className="note-textarea"
                value={noteInput}
                onChange={(e) => setNoteInput(e.target.value)}
                placeholder="Ví dụ: Đo sau khi tập gym, đo buổi sáng sớm, mặc áo thun ôm sát…"
                rows={3}
                disabled={savingNote}
                autoFocus
              />

              {noteError && (
                <p style={{ color: "#9E2A2B", fontSize: 12, margin: "0 0 12px 0" }}>{noteError}</p>
              )}

              <div className="confirm-actions-row" style={{ justifyContent: "flex-end" }}>
                <button
                  type="button"
                  className="btn-gold-secondary"
                  onClick={() => setScanToEditNote(null)}
                  disabled={savingNote}
                >
                  Hủy
                </button>
                <button type="submit" className="btn-gold-primary" disabled={savingNote}>
                  {savingNote ? <LoaderCircle size={15} className="spin-gold" /> : <Check size={15} />} Lưu ghi chú
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
