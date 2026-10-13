"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  type ScanComparisonResponse,
  fetchScanComparison,
  formatScanDateTime,
  getModeLabel,
  getSourceLabel,
} from "../../lib/userScansApi";
import { useDrawerA11y } from "../../lib/useDrawerA11y";
import { X, ArrowRight, AlertTriangle, Scale, LoaderCircle, CheckCircle2, Info } from "lucide-react";

interface ScanCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  scanAId: string | null;
  scanBId: string | null;
}

export default function ScanCompareModal({
  isOpen,
  onClose,
  scanAId,
  scanBId,
}: ScanCompareModalProps) {
  const [data, setData] = useState<ScanComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sheetRef = useRef<HTMLDivElement>(null);

  useDrawerA11y(isOpen, onClose, sheetRef);

  useEffect(() => {
    if (!isOpen || !scanAId || !scanBId) {
      setData(null);
      setError(null);
      return;
    }

    let aborted = false;
    setLoading(true);
    setError(null);

    fetchScanComparison(scanAId, scanBId)
      .then((res) => {
        if (!aborted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!aborted) {
          setError(err?.message || "Không thể tải dữ liệu so sánh hai lần scan.");
          setLoading(false);
        }
      });

    return () => {
      aborted = true;
    };
  }, [isOpen, scanAId, scanBId]);

  if (!isOpen) return null;

  return (
    <div
      className="compare-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="compare-modal-title"
      aria-describedby="compare-modal-desc"
    >
      <div
        ref={sheetRef}
        tabIndex={-1}
        className="compare-modal-sheet"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="compare-modal-header">
          <div className="header-title-row">
            <div className="header-badge">
              <Scale size={18} strokeWidth={2.2} />
              <span id="compare-modal-title">Đối chiếu số đo hai lần scan</span>
            </div>
            <button
              type="button"
              className="close-icon-btn"
              onClick={onClose}
              aria-label="Đóng hộp thoại"
            >
              <X size={20} />
            </button>
          </div>
          <p id="compare-modal-desc" className="header-desc">
            So sánh biến thiên số đo ước lượng giữa hai lần chụp. Mọi thay đổi đều được ghi nhận
            dưới dạng toán học trung tính, không kết luận thể trạng hay sức khỏe.
          </p>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="compare-loading-state">
            <LoaderCircle size={36} className="spin-gold" />
            <p>Đang đối chiếu dữ liệu hai lần scan…</p>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="compare-error-box">
            <AlertTriangle size={24} className="error-icon" />
            <div className="error-content">
              <strong>Không thể đối chiếu</strong>
              <p>{error}</p>
            </div>
            <button type="button" className="btn-retry" onClick={() => onClose()}>
              Đóng
            </button>
          </div>
        )}

        {/* Data Loaded */}
        {!loading && !error && data && (
          <div className="compare-modal-body">
            {/* Compatibility Warning if any */}
            {data.compatibility_warnings && data.compatibility_warnings.length > 0 && (
              <div className="compare-warning-banner" role="alert">
                <AlertTriangle size={20} className="warning-icon" />
                <div className="warning-text">
                  <strong>Lưu ý về độ tương thích:</strong>
                  <ul>
                    {data.compatibility_warnings.map((w, idx) => (
                      <li key={`warn-${idx}`}>{w}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Scan Sessions Overview Cards */}
            <div className="compare-sessions-grid">
              {/* Scan A */}
              <div className="session-card card-a">
                <div className="session-card-badge">Lần chụp 1 (Cũ hơn)</div>
                <div className="session-time">{formatScanDateTime(data.scan_a.captured_at)}</div>
                <div className="session-meta">
                  <span className="meta-pill">Chế độ: {getModeLabel(data.scan_a.capture_mode)}</span>
                  <span className="meta-pill">Engine: {data.scan_a.engine_version}</span>
                </div>
                {data.scan_a.note && (
                  <div className="session-note">
                    <em>&quot;{data.scan_a.note}&quot;</em>
                  </div>
                )}
              </div>

              {/* Arrow Indicator */}
              <div className="compare-arrow-divider" aria-hidden="true">
                <ArrowRight size={22} />
              </div>

              {/* Scan B */}
              <div className="session-card card-b">
                <div className="session-card-badge is-gold">Lần chụp 2 (Mới hơn)</div>
                <div className="session-time">{formatScanDateTime(data.scan_b.captured_at)}</div>
                <div className="session-meta">
                  <span className="meta-pill">Chế độ: {getModeLabel(data.scan_b.capture_mode)}</span>
                  <span className="meta-pill">Engine: {data.scan_b.engine_version}</span>
                </div>
                {data.scan_b.note && (
                  <div className="session-note">
                    <em>&quot;{data.scan_b.note}&quot;</em>
                  </div>
                )}
              </div>
            </div>

            {/* Comparison Table */}
            <div className="compare-table-wrapper">
              <table className="compare-metrics-table">
                <thead>
                  <tr>
                    <th scope="col">Chỉ số số đo</th>
                    <th scope="col">Lần chụp 1</th>
                    <th scope="col">Lần chụp 2</th>
                    <th scope="col">Độ biến thiên (Delta)</th>
                    <th scope="col">Nhận định trung tính</th>
                  </tr>
                </thead>
                <tbody>
                  {data.comparisons.map((c) => {
                    const isUpperIncompatible =
                      (data.scan_a.capture_mode === "upper_body" || data.scan_b.capture_mode === "upper_body") &&
                      (c.metric_key === "hip_cm" || c.metric_key === "thigh_cm" || c.metric_key === "calf_cm");

                    return (
                      <tr key={`cmp-${c.metric_key}`} className={!c.is_comparable ? "is-incomparable" : ""}>
                        <td className="cell-metric-name">
                          <strong>{c.label}</strong>
                          {isUpperIncompatible && (
                            <span className="inline-incompatible-pill" title="Chụp thân trên không đo mông/chân thực tế">
                              Khác chế độ chụp
                            </span>
                          )}
                        </td>

                        <td className="cell-old-val">
                          {c.value_a_cm !== null ? (
                            <>
                              <span className="val-number">{c.value_a_cm} cm</span>
                              <span className="source-tag">({getSourceLabel(c.source_a)})</span>
                            </>
                          ) : (
                            <span className="text-muted">--</span>
                          )}
                        </td>

                        <td className="cell-new-val">
                          {c.value_b_cm !== null ? (
                            <>
                              <span className="val-number">{c.value_b_cm} cm</span>
                              <span className="source-tag">({getSourceLabel(c.source_b)})</span>
                            </>
                          ) : (
                            <span className="text-muted">--</span>
                          )}
                        </td>

                        <td className="cell-delta">
                          {c.is_comparable && c.delta_cm !== null ? (
                            <span
                              className={`delta-badge ${
                                c.delta_cm > 0
                                  ? "delta-positive"
                                  : c.delta_cm < 0
                                  ? "delta-negative"
                                  : "delta-zero"
                              }`}
                            >
                              {c.delta_cm > 0 ? `+${c.delta_cm}` : c.delta_cm} cm
                            </span>
                          ) : (
                            <span className="delta-badge delta-na">Không đối chiếu</span>
                          )}
                        </td>

                        <td className="cell-statement">
                          <p className="statement-text">{c.summary_text}</p>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Disclaimer in Modal */}
            <div className="compare-disclaimer-note">
              <Info size={16} className="disclaimer-icon" />
              <span>{data.disclaimer}</span>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="compare-modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Đóng bảng đối chiếu
          </button>
        </div>
      </div>
    </div>
  );
}
