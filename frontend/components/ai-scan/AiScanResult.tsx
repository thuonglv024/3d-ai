"use client";

import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { computeClientSizeAdvice } from "../../lib/ScanContext";
import type { Product } from "../../lib/catalog";
import type { AiScanResultData } from "../../lib/useAiScan";

const POSE_LABEL: Record<string, string> = {
  good: "Tư thế tốt",
  fair: "Tư thế trung bình",
  poor: "Tư thế chưa đạt",
};

function valueText(value: number | null): string {
  return value == null ? "—" : value.toFixed(1);
}

export default function AiScanResult({
  result,
  product,
  onSelectSize,
  onReset,
  onSwitchTo3D,
  onOpenSizeChart,
}: {
  result: AiScanResultData;
  product: Product;
  onSelectSize: (size: string) => void;
  onReset: () => void;
  onSwitchTo3D: () => void;
  onOpenSizeChart?: () => void;
}) {
  const upper = result.capture_mode === "upper_body";
  const advice = computeClientSizeAdvice(result.measurements, product.chart);
  const confidence = Math.round(result.confidence * 100);
  const confidenceTone = confidence >= 70 ? "is-high" : confidence >= 45 ? "is-mid" : "is-low";
  const isBottom = product.chart.garment === "bottom";

  return (
    <div className="scan-result ai-scan-result">
      <header className="scan-result-heading">
        <div>
          <h2>Số đo ước lượng bằng AI</h2>
          <p>
            {result.measurements.height_cm.toFixed(0)} cm ·{" "}
            {upper ? "Thân trên" : "Toàn thân"} · {result.model}
          </p>
        </div>
        <div className="scan-header-actions">
          <span className={`ai-confidence-badge ${confidenceTone}`}>
            Độ tin cậy {confidence}%
          </span>
          <button className="scan-btn-subtle" type="button" onClick={onReset}>
            <RotateCcw size={15} />
            Quét lại
          </button>
        </div>
      </header>

      <p className="scan-source-note">
        AI Vision ước lượng số đo trực tiếp từ hai ảnh chính diện và nghiêng. Đây là
        tính năng thử nghiệm, <strong>chưa kiểm chứng trên người thật</strong> và không
        dùng cho may đo. Ảnh chỉ được xử lý trong bộ nhớ, không lưu trên máy chủ MORPH.
      </p>

      <div className="ai-scan-meta">
        <span className={`ai-pose-pill ${result.pose_quality === "good" ? "is-good" : ""}`}>
          <CheckCircle2 size={14} />
          {POSE_LABEL[result.pose_quality] || "Chất lượng tư thế: " + result.pose_quality}
        </span>
        <span className="ai-source-pill">
          <ShieldCheck size={14} />
          Nguồn: AI vision estimate
        </span>
      </div>

      <section className="scan-size-panel" aria-label="Gợi ý size từ số đo AI">
        <div className="scan-size-panel-info">
          <div className="scan-size-panel-title-row">
            <Sparkles size={20} className="scan-panel-gold-icon" />
            <h3>Gợi ý kích thước cho {product.name}</h3>
          </div>
          <p>
            {isBottom
              ? "Đối chiếu vòng eo và mông do AI ước lượng với bảng size của sản phẩm."
              : "Đối chiếu vòng ngực và eo do AI ước lượng với bảng size của sản phẩm."}{" "}
            Kết quả chỉ mang tính tham khảo.
          </p>
        </div>

        <div className="scan-size-panel-content">
          {advice.status === "matched" && advice.candidates.length > 0 ? (
            <div className="scan-advice-success" role="region" aria-label="Size gợi ý">
              <div className="scan-advice-success-info">
                <span className="scan-advice-badge">
                  <Sparkles size={16} /> Gợi ý: Size {advice.candidates.join(", ")}
                </span>
                <span className="scan-advice-subnote">
                  Số đo AI nằm trong khoảng của bảng size đã chọn.
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
                  <button type="button" className="scan-btn-subtle" onClick={onOpenSizeChart}>
                    Xem bảng size chi tiết
                  </button>
                )}
              </div>
            </div>
          ) : advice.status === "insufficient_measurements" ? (
            <div className="scan-advice-insufficient" role="region" aria-label="Thiếu số đo">
              <div className="scan-insufficient-header">
                <AlertCircle size={18} />
                <h4>{advice.message}</h4>
              </div>
              <p>
                {upper && isBottom
                  ? "Chế độ thân trên không ước lượng vòng mông. Hãy quét toàn thân hoặc chuyển về chế độ 3D để đối chiếu."
                  : "AI chưa thấy đủ vùng cơ thể cần đo. Hãy quét lại với ánh sáng tốt hơn."}
              </p>
              <div className="scan-advice-actions">
                <button className="scan-size-apply-btn" type="button" onClick={onReset}>
                  <RotateCcw size={15} />
                  Quét lại
                </button>
                {onOpenSizeChart && (
                  <button className="scan-btn-subtle" type="button" onClick={onOpenSizeChart}>
                    Xem bảng size & chọn thủ công
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="scan-advice-nomatch" role="region" aria-label="Không khớp size">
              <div className="scan-nomatch-header">
                <AlertCircle size={18} />
                <p>
                  Không có size nào khớp tất cả số đo AI ước lượng. Hãy xem bảng size
                  hoặc chọn size thủ công.
                </p>
              </div>
              <div className="scan-advice-actions">
                {onOpenSizeChart && (
                  <button className="scan-btn-subtle" type="button" onClick={onOpenSizeChart}>
                    Xem bảng size & chọn thủ công
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

      <div className="scan-data-grid ai-measurement-grid">
        {result.details.map((detail) => (
          <div key={detail.key}>
            <span>{detail.label}</span>
            <strong>
              {valueText(detail.value_cm)}
              <small>{detail.value_cm == null ? "" : "cm"}</small>
            </strong>
            <small>{detail.value_cm == null ? "AI không ước lượng" : "AI Vision"}</small>
          </div>
        ))}
      </div>

      {result.notes && <p className="ai-scan-notes">{result.notes}</p>}

      {result.warnings.length > 0 && (
        <details className="scan-limitations" open>
          <summary>Cảnh báo & giới hạn của lần ước lượng này</summary>
          {result.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </details>
      )}

      <div className="ai-scan-actions">
        <button className="scan-btn-subtle" type="button" onClick={onReset}>
          <RotateCcw size={15} />
          Quét lại bằng AI
        </button>
        <button className="scan-btn-subtle" type="button" onClick={onSwitchTo3D}>
          <ScanLine size={15} />
          Chuyển sang quét 3D
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
