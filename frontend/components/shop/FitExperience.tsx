import { useEffect, useState, useCallback } from "react";
import {
  AlertCircle,
  ArrowRight,
  Camera,
  Check,
  Laptop,
  LoaderCircle,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Sun,
} from "lucide-react";
import { useBodyScan, type Job } from "../../lib/useBodyScan";
import { money, type Product } from "../../lib/catalog";
import { useScan, type SizeAdviceResult } from "../../lib/ScanContext";
import ScanResult from "./ScanResult";
import CaptureSession from "./CaptureSession";
import CustomSelect from "./CustomSelect";

export default function FitExperience({
  product,
  active,
  onSelectSize,
  onOpenSizeChart,
  onClose,
}: {
  product: Product;
  active: boolean;
  onSelectSize: (size: string) => void;
  onOpenSizeChart?: () => void;
  onClose?: () => void;
}) {
  const requiresHipMeasurement = Boolean(
    product.chart?.rows?.some((row) => Boolean(row.hip_cm))
  );
  const isFullBodyRequired = Boolean(
    requiresHipMeasurement ||
    product.chart?.garment === "bottom" ||
    (product.chart?.garment as string) === "dress" ||
    ["cat-quan", "cat-vay", "quan", "vay"].includes(product.category) ||
    product.slug.includes("quan") ||
    product.slug.includes("dam") ||
    product.slug.includes("chan-vay")
  );

  const scanContext = useScan();
  const s = useBodyScan(scanContext.job, isFullBodyRequired ? "full_body" : "upper_body");
  const [capturing, setCapturing] = useState(false);
  const [advice, setAdvice] = useState<SizeAdviceResult | null>(null);
  const [adviceError, setAdviceError] = useState("");
  const [retry, setRetry] = useState(0);

  // Set default captureMode based on product requirement
  useEffect(() => {
    if (isFullBodyRequired) {
      s.setCaptureMode("full_body");
    } else {
      s.setCaptureMode("upper_body");
    }
  }, [product.id, isFullBodyRequired]);

  // Sync active job from local hook to shared ScanContext
  useEffect(() => {
    if (s.job) {
      scanContext.setJob(s.job);
    }
  }, [s.job, scanContext]);

  // Populate local hook with shared ScanContext job if available and not yet loaded
  useEffect(() => {
    if (scanContext.job && !s.job) {
      s.setJob(scanContext.job);
    }
  }, [scanContext.job, s.job, s.setJob]);

  useEffect(() => {
    if (scanContext.jobError) {
      s.setError(scanContext.jobError);
    }
  }, [scanContext.jobError, s.setError]);

  const currentJob: Job | null = s.job || scanContext.job;
  const isBusy = s.busy || currentJob?.status === "queued" || currentJob?.status === "processing";

  useEffect(() => {
    if (!active) setCapturing(false);
  }, [active]);

  // Query size advice whenever active job or product changes
  useEffect(() => {
    if (!currentJob || currentJob.status !== "completed") return;

    let aborted = false;
    setAdvice(null);
    setAdviceError("");

    scanContext
      .fetchAdviceForProduct(product, currentJob)
      .then((data) => {
        if (!aborted) {
          if (data.status === "error") {
            setAdviceError(data.message);
            setAdvice(null);
          } else {
            setAdvice(data);
          }
        }
      })
      .catch((err) => {
        if (!aborted) {
          setAdviceError(err?.message || "Chưa đối chiếu được bảng size.");
          setAdvice(null);
        }
      });

    return () => {
      aborted = true;
    };
  }, [currentJob?.id, currentJob?.status, product.id, retry, scanContext.fetchAdviceForProduct]);

  const handleReset = useCallback(async () => {
    s.setJob(null);
    scanContext.setJob(null);
    await s.clear();
    await scanContext.clearScanSession();
  }, [s, scanContext]);

  const handleResetFullBody = useCallback(async () => {
    s.setJob(null);
    scanContext.setJob(null);
    await s.clear();
    await scanContext.clearScanSession();
    s.setCaptureMode("full_body");
    setCapturing(false);
  }, [s, scanContext]);

  const renderProductContextBar = () => {
    if (!product) return null;
    return (
      <div
        className={`fit-product-context ${capturing && active ? "is-capturing" : ""}`}
        aria-label={`Sản phẩm đang chọn: ${product.name}`}
      >
        <div className="fit-product-thumb">
          <img src={product.image} alt={product.name} />
        </div>
        <div className="fit-product-meta">
          <span className="fit-product-category">{product.categoryName} · Tìm size phù hợp cho</span>
          <strong className="fit-product-name">{product.name}</strong>
        </div>
        <div className="fit-product-price">
          <span>{money(product.price)}</span>
        </div>
      </div>
    );
  };

  if (currentJob && currentJob.status === "completed") {
    return (
      <div className="fit-experience">
        {renderProductContextBar()}
        <ScanResult
          job={currentJob}
          active={active}
          onReset={handleReset}
          onResetFullBody={handleResetFullBody}
          deleting={s.deleting}
          onSelectSize={onSelectSize}
          onOpenSizeChart={onOpenSizeChart}
          advice={advice}
          adviceError={adviceError}
          onRetry={() => setRetry((n) => n + 1)}
          error={s.error || scanContext.jobError}
          product={product}
        />
      </div>
    );
  }

  if (capturing && active) {
    return (
      <div className="fit-experience fit-experience-capturing">
        {renderProductContextBar()}
        <CaptureSession
          mode={s.captureMode}
          onCancel={() => setCapturing(false)}
          onComplete={(pair) => {
            setCapturing(false);
            s.choose("front", pair.front);
            s.choose("side", pair.side);
            void s.scan(pair);
          }}
        />
      </div>
    );
  }

  if (isBusy) {
    return (
      <div className="fit-experience">
        {renderProductContextBar()}
        <div className="scan-processing-screen" role="status">
          <div className="scan-processing-icon">
            <ScanLine size={42} />
            <LoaderCircle size={72} className="spin" />
          </div>
          <h2>Đang dựng hình thể của bạn</h2>
          <p>{currentJob?.stage || s.job?.stage || scanContext.job?.stage || "Đang gửi hai góc chụp…"}</p>
          <div>
            <span>
              <Check size={16} /> Chính diện
            </span>
            <span>
              <Check size={16} /> Góc nghiêng 90°
            </span>
          </div>
          <p className="scan-processing-note">
            Bạn đã có thể rời camera. Kết quả sẽ hiện ngay tại đây.
          </p>
          {(s.error || scanContext.jobError) && (
            <div role="alert" style={{ marginTop: 16 }}>
              <p>{s.error || scanContext.jobError}</p>
              <button
                className="shop-secondary"
                type="button"
                onClick={() => {
                  s.setError("");
                  scanContext.setJobError("");
                  s.setPollRetry((n) => n + 1);
                }}
              >
                Kiểm tra kết quả
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  const validHeight =
    Number.isFinite(Number(s.height)) && Number(s.height) >= 100 && Number(s.height) <= 230;

  return (
    <div className="fit-experience">
      {renderProductContextBar()}
      <section className="scan-onboarding">
        <div className="scan-intro">
          <div className="scan-intro-icon">
            <ScanLine size={27} />
          </div>
          <h1>Tìm size từ hình thể của bạn.</h1>
          <p>
            Chỉ cần camera và chiều cao. MORPH tự chụp hai góc, dựng hình thể 3D và giúp bạn đối
            chiếu size cho <strong>{product.name}</strong>.
          </p>
        </div>
        <ol className="scan-journey">
          <li>
            <span>01</span>
            <div>
              <strong>Nhìn thẳng</strong>
              <p>Đếm ngược và tự chụp chính diện.</p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <strong>Xoay người 90°</strong>
              <p>Tự chuyển bước, đếm ngược lần nữa.</p>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <strong>Xem hình thể & size</strong>
              <p>Nhận kết quả ngay khi xử lý xong.</p>
            </div>
          </li>
        </ol>
        <div className="scan-setup">
          <div className="scan-setup-title">
            <h2>Chuẩn bị trước khi quét</h2>
            <span>Hai góc · Một phiên camera</span>
          </div>

          {/* Full Body Requirement Card for Pants / Skirts / Dresses */}
          {isFullBodyRequired && (
            <div className="scan-fullbody-requirement-card" role="region" aria-label="Yêu cầu chụp toàn thân">
              <div className="requirement-header">
                <Sparkles size={18} className="requirement-gold-icon" />
                <h3>Khuyên chọn Camera · toàn thân (full_body) cho quần, chân váy & đầm</h3>
              </div>
              <p className="requirement-desc">
                Sản phẩm này cần số đo phần dưới (vòng eo & vòng mông). Hãy chọn chế độ{" "}
                <strong>Camera · toàn thân (full_body)</strong> ngay từ bước chuẩn bị để MORPH đo trực
                tiếp vòng mông từ hai góc chụp. Chế độ webcam thân trên chỉ quét từ đầu đến cạp quần.
              </p>
              <div className="requirement-tips-box">
                <strong className="requirement-tips-title">Gợi ý góc đặt thiết bị:</strong>
                <ul className="requirement-tips-list">
                  <li>
                    <span className="tip-device"><Laptop size={15} /> Laptop:</span> Đặt laptop trên bàn/ghế cách 2m – 2.5m, nghiêng nhẹ màn hình xuống để camera thấy đủ từ đỉnh đầu đến bàn chân.
                  </li>
                  <li>
                    <span className="tip-device"><Smartphone size={15} /> Điện thoại:</span> Tựa điện thoại hoặc dùng giá đỡ ngang ngực, lùi xa 2m.
                  </li>
                </ul>
              </div>
            </div>
          )}

          {/* Amber Warning if User switches to upper_body on full-body products */}
          {isFullBodyRequired && s.captureMode === "upper_body" && (
            <div className="scan-upperbody-warning-card" role="alert">
              <div className="warning-card-head">
                <AlertCircle size={18} />
                <strong>Cảnh báo trên Laptop: Chế độ thân trên không đo được vòng mông</strong>
              </div>
              <p>
                Chế độ <strong>Webcam · thân trên (upper_body)</strong> sẽ không đo được vòng mông thực tế
                và <strong>hệ thống sẽ từ chối tự động gợi ý size quần/váy từ số đo mẫu 3D</strong>{" "}
                (<code>template_model</code>). Bạn cần chuyển sang quét toàn thân (<code>full_body</code>)
                hoặc tự đối chiếu bảng size của sản phẩm.
              </p>
              <div className="scan-warning-actions">
                <button
                  type="button"
                  className="scan-switch-mode-btn"
                  onClick={() => s.setCaptureMode("full_body")}
                >
                  Chuyển lại sang Camera · toàn thân (full_body) →
                </button>
                {onOpenSizeChart && (
                  <button
                    type="button"
                    className="scan-switch-mode-btn is-secondary"
                    onClick={onOpenSizeChart}
                  >
                    Tự đối chiếu bảng size
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="scan-setup-fields">
            <label htmlFor="scan-height">
              Chiều cao của bạn
              <div className="scan-height-input">
                <input
                  id="scan-height"
                  type="number"
                  inputMode="decimal"
                  min="100"
                  max="230"
                  step=".1"
                  value={s.height}
                  onChange={(e) => s.setHeight(e.target.value)}
                  aria-invalid={!validHeight}
                />
                <span>cm</span>
              </div>
              {!validHeight && <small>Nhập chiều cao từ 100 đến 230 cm.</small>}
            </label>
            <div className="scan-framing-field">
              <span className="scan-field-label">Khung chụp</span>
              <CustomSelect
                id="scan-framing"
                value={s.captureMode}
                onChange={(val) => s.setCaptureMode(val as "upper_body" | "full_body")}
                ariaLabel="Khung chụp"
                options={
                  isFullBodyRequired
                    ? [
                        {
                          value: "full_body",
                          label: "Camera · toàn thân",
                          sublabel: "Khuyên dùng cho sản phẩm này",
                        },
                        {
                          value: "upper_body",
                          label: "Webcam · từ đầu đến cạp quần",
                          sublabel: "Không đo mông",
                        },
                      ]
                    : [
                        {
                          value: "upper_body",
                          label: "Webcam · từ đầu đến cạp quần",
                          sublabel: "Đầu, hai vai, eo & cạp quần",
                        },
                        {
                          value: "full_body",
                          label: "Camera · toàn thân",
                          sublabel: "Từ đầu đến gót chân",
                        },
                      ]
                }
              />
            </div>
          </div>
          <div className="scan-preparation">
            <Sun size={20} />
            <p>
              Mặc đồ ôm sát, đủ sáng, tay hơi tách thân.{" "}
              {s.captureMode === "upper_body"
                ? "Giữ đầu, vai, eo và cạp quần trong khung; không cần thấy chân."
                : "Giữ đủ đầu và bàn chân trong khung."}
            </p>
          </div>
          <label className="scan-camera-consent">
            <input
              type="checkbox"
              checked={s.consent}
              onChange={(e) => s.setConsent(e.target.checked)}
            />
            <span>
              Tôi đồng ý gửi khung hình kiểm tra tư thế và hai ảnh chụp tới máy chủ MORPH để phân tích
              hình thể 3D (không lưu trữ lâu dài hồ sơ ảnh thô; mô hình tạm thời tự động xóa sau tối đa
              1 giờ hoặc xóa ngay khi bấm &ldquo;Chụp lại&rdquo; / &ldquo;Xóa&rdquo;).
            </span>
          </label>
          <button
            className="shop-primary scan-start"
            type="button"
            disabled={!s.consent || !validHeight || !s.health?.ready || s.deleting}
            onClick={() => {
              s.setError("");
              scanContext.setJobError("");
              setCapturing(true);
            }}
          >
            <Camera size={20} />
            Mở camera & bắt đầu
            <ArrowRight size={18} />
          </button>
          {!s.health?.ready && (
            <p className="scan-service" role="status">
              {s.health ? "Dịch vụ scan chưa kết nối." : "Đang kết nối dịch vụ scan…"}
              {s.health && (
                <button className="shop-inline" type="button" onClick={s.checkHealth}>
                  Thử kết nối lại
                </button>
              )}
            </p>
          )}
          {(s.error || scanContext.jobError) && (
            <p className="fit-error" role="alert">
              {s.error || scanContext.jobError}
            </p>
          )}
          <div className="scan-privacy">
            <ShieldCheck size={16} />
            <p>
              Quyền riêng tư &amp; vòng đời dữ liệu: Khung hình kiểm tra tư thế và hai ảnh chụp được gửi
              tới máy chủ MORPH để phân tích hình thể 3D, không lưu trữ lâu dài hồ sơ ảnh thô. Mô hình
              tạm thời tự động xóa sau tối đa 1 giờ (hoặc xóa ngay khi bấm &ldquo;Chụp lại&rdquo; /
              &ldquo;Xóa&rdquo;).
            </p>
          </div>
        </div>
        <p className="scan-estimate-note">
          {s.captureMode === "upper_body"
            ? "Ngực/eo ước lượng từ ảnh và tỷ lệ mẫu theo chiều cao; phần mông/chân theo mẫu 3D."
            : "Ngực/eo/mông ước lượng từ hai góc chụp."}{" "}
          Chưa kiểm chứng độ chính xác trên người thật; không dùng cho may đo.
        </p>
      </section>
    </div>
  );
}
