import { useEffect, useRef, useState, useCallback } from "react";
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
import AiScanResult from "../ai-scan/AiScanResult";
import AiPhotoUpload, { type AiUploadPair } from "../ai-scan/AiPhotoUpload";
import { useAiScan } from "../../lib/useAiScan";

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
  const [scanMode, setScanMode] = useState<"classic" | "ai">("ai");
  const [uploadPair, setUploadPair] = useState<AiUploadPair>({ front: null, side: null });
  const lastUploadSignature = useRef("");
  const aiPairRef = useRef<{ front: File; side: File } | null>(null);
  const ai = useAiScan();
  const aiUnavailable = ai.health !== null && !ai.health.ready;
  const validHeight =
    Number.isFinite(Number(s.height)) && Number(s.height) >= 100 && Number(s.height) <= 230;

  const resetAiUpload = useCallback(() => {
    setUploadPair({ front: null, side: null });
    lastUploadSignature.current = "";
  }, []);

  // Uploaded photos are analyzed automatically as soon as the pair is complete,
  // the height is valid and the user has consented. The signature prevents the
  // effect from firing twice for the same pair.
  const uploadSignature =
    scanMode === "ai" && uploadPair.front && uploadPair.side
      ? [
          uploadPair.front.name,
          uploadPair.front.size,
          uploadPair.front.lastModified,
          uploadPair.side.name,
          uploadPair.side.size,
          uploadPair.side.lastModified,
        ].join("|")
      : "";

  useEffect(() => {
    if (!uploadSignature || ai.busy) return;
    if (!s.consent || !validHeight || ai.health?.ready !== true) return;
    if (lastUploadSignature.current === uploadSignature) return;
    if (!uploadPair.front || !uploadPair.side) return;
    lastUploadSignature.current = uploadSignature;
    aiPairRef.current = { front: uploadPair.front, side: uploadPair.side };
    void ai.analyze({ front: uploadPair.front, side: uploadPair.side }, s.height, s.captureMode);
  }, [
    uploadSignature,
    ai.busy,
    ai.analyze,
    ai.health?.ready,
    s.consent,
    s.height,
    s.captureMode,
    validHeight,
    uploadPair.front,
    uploadPair.side,
  ]);

  // Set default captureMode based on product requirement
  useEffect(() => {
    if (isFullBodyRequired) {
      s.setCaptureMode("full_body");
    } else {
      s.setCaptureMode("upper_body");
    }
  }, [product.id, isFullBodyRequired]);

  // Sync active job from local hook to shared ScanContext.
  // Depend on the stable setter instead of the whole context value: the context
  // object is recreated on every provider render, so using it as a dependency
  // made this effect run continuously and triggered a maximum-update-depth loop.
  useEffect(() => {
    if (s.job) {
      scanContext.setJob(s.job);
    }
  }, [s.job, scanContext.setJob]);

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
    resetAiUpload();
    await s.clear();
    await scanContext.clearScanSession();
  }, [s, scanContext, resetAiUpload]);

  const handleResetFullBody = useCallback(async () => {
    s.setJob(null);
    scanContext.setJob(null);
    resetAiUpload();
    await s.clear();
    await scanContext.clearScanSession();
    s.setCaptureMode("full_body");
    setCapturing(false);
  }, [s, scanContext, resetAiUpload]);

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

  if (scanMode === "ai" && ai.result) {
    return (
      <div className="fit-experience">
        {renderProductContextBar()}
        <AiScanResult
          result={ai.result}
          product={product}
          onSelectSize={onSelectSize}
          onReset={() => {
            ai.reset();
            resetAiUpload();
          }}
          onSwitchTo3D={() => {
            ai.reset();
            resetAiUpload();
            setScanMode("classic");
          }}
          onBuild3D={() => {
            const pair = aiPairRef.current;
            if (!pair) return;
            s.choose("front", pair.front);
            s.choose("side", pair.side);
            void (async () => {
              const ok = await s.scan(pair);
              if (!ok) return; // keep the AI result visible; s.error explains why
              ai.reset();
              resetAiUpload();
              setScanMode("classic");
            })();
          }}
          onOpenSizeChart={onOpenSizeChart}
        />
        {s.error && (
          <p className="fit-error" role="alert" style={{ margin: "0 24px 16px" }}>
            {s.error}
          </p>
        )}
      </div>
    );
  }

  if (scanMode === "ai" && ai.busy) {
    return (
      <div className="fit-experience">
        {renderProductContextBar()}
        <div className="scan-processing-screen" role="status">
          <div className="scan-processing-icon">
            <Sparkles size={42} />
            <LoaderCircle size={72} className="spin" />
          </div>
          <h2>AI đang đọc hai góc chụp</h2>
          <p>
            Gemini ước lượng số đo từ ảnh chính diện và nghiêng. Quá trình có thể mất
            10–30 giây.
          </p>
          <div>
            <span>
              <Check size={16} /> Chính diện
            </span>
            <span>
              <Check size={16} /> Góc nghiêng 90°
            </span>
          </div>
          <p className="scan-processing-note">
            Bạn đã có thể rời camera. Kết quả AI sẽ hiện ngay tại đây.
          </p>
        </div>
      </div>
    );
  }

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
          aiMode={scanMode === "ai"}
          onCancel={() => setCapturing(false)}
          onComplete={(pair) => {
            setCapturing(false);
            if (scanMode === "ai") {
              aiPairRef.current = pair;
              void ai.analyze(pair, s.height, s.captureMode);
              return;
            }
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

  return (
    <div className="fit-experience">
      {renderProductContextBar()}
      <section className="scan-onboarding">
        <div className="scan-intro">
          <div className="scan-intro-icon">
            {scanMode === "ai" ? <Sparkles size={27} /> : <ScanLine size={27} />}
          </div>
          <h1>{scanMode === "ai" ? "Quét số đo bằng AI." : "Tìm size từ hình thể của bạn."}</h1>
          <p>
            {scanMode === "ai" ? (
              <>
                AI Vision gửi hai ảnh chính diện và nghiêng tới Gemini để ước lượng số đo,
                rồi đối chiếu size cho <strong>{product.name}</strong>. Đây là chế độ thử nghiệm.
              </>
            ) : (
              <>
                Chỉ cần camera và chiều cao. MORPH tự chụp hai góc, dựng hình thể 3D và giúp bạn đối
                chiếu size cho <strong>{product.name}</strong>.
              </>
            )}
          </p>
        </div>
        <div className="scan-mode-switch" role="group" aria-label="Chọn chế độ quét">
          <button
            type="button"
            className={scanMode === "ai" ? "is-active" : ""}
            aria-pressed={scanMode === "ai"}
            disabled={aiUnavailable}
            title={aiUnavailable ? ai.health?.message : undefined}
            onClick={() => {
              setScanMode("ai");
              s.setError("");
              ai.reset();
              resetAiUpload();
            }}
          >
            <Sparkles size={16} />
            <span>
              <strong>AI Vision · Beta</strong>
              <small>
                {ai.health === null
                  ? "Đang kiểm tra dịch vụ AI…"
                  : ai.health.ready
                  ? `${ai.health.provider} · ${ai.health.model}`
                  : "Chưa cấu hình GOOGLE_API_KEY"}
              </small>
            </span>
          </button>
          <button
            type="button"
            className={scanMode === "classic" ? "is-active" : ""}
            aria-pressed={scanMode === "classic"}
            onClick={() => {
              setScanMode("classic");
              s.setError("");
              resetAiUpload();
            }}
          >
            <ScanLine size={16} />
            <span>
              <strong>Quét 3D</strong>
              <small>MediaPipe · mô hình 3D tương tác</small>
            </span>
          </button>
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
              <strong>{scanMode === "ai" ? "Nhận số đo AI & size" : "Xem hình thể & size"}</strong>
              <p>
                {scanMode === "ai"
                  ? "AI ước lượng số đo và đối chiếu bảng size."
                  : "Nhận kết quả ngay khi xử lý xong."}
              </p>
            </div>
          </li>
        </ol>
        <div className="scan-setup">
          <div className="scan-setup-title">
            <h2>Chuẩn bị trước khi quét</h2>
            <span>
              {scanMode === "ai" ? "AI Vision · 2 ảnh · Beta" : "Hai góc · Một phiên camera"}
            </span>
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
            {scanMode !== "ai" && (
              <div className="scan-framing-field scan-setup-wide">
                <span className="scan-field-label">Dáng cơ thể cho mô hình 3D</span>
                <CustomSelect
                  id="scan-sex"
                  value={s.sex}
                  onChange={(val) => s.setSex(val as "auto" | "female" | "male")}
                  ariaLabel="Dáng cơ thể cho mô hình 3D"
                  options={[
                    { value: "auto", label: "Tự động", sublabel: "Ước lượng từ tỉ lệ số đo" },
                    { value: "female", label: "Nữ", sublabel: "Vai hẹp hơn, ngực và hông nữ" },
                    { value: "male", label: "Nam", sublabel: "Vai rộng hơn, ngực phẳng" },
                  ]}
                />
              </div>
            )}
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
              {scanMode === "ai" ? (
                <>
                  Tôi đồng ý gửi hai ảnh chụp tới dịch vụ AI (Google Gemini) để ước lượng số đo.
                  Ảnh chỉ được xử lý trong bộ nhớ và không lưu trên máy chủ MORPH. Kết quả là ước
                  lượng tham khảo, chưa kiểm chứng trên người thật.
                </>
              ) : (
                <>
                  Tôi đồng ý gửi khung hình kiểm tra tư thế và hai ảnh chụp tới máy chủ MORPH để phân tích
                  hình thể 3D (không lưu trữ lâu dài hồ sơ ảnh thô; mô hình tạm thời tự động xóa sau tối đa
                  1 giờ hoặc xóa ngay khi bấm &ldquo;Chụp lại&rdquo; / &ldquo;Xóa&rdquo;).
                </>
              )}
            </span>
          </label>
          <button
            className="shop-primary scan-start"
            type="button"
            disabled={
              !s.consent ||
              !validHeight ||
              !s.health?.ready ||
              s.deleting ||
              (scanMode === "ai" && aiUnavailable)
            }
            onClick={() => {
              s.setError("");
              scanContext.setJobError("");
              ai.reset();
              resetAiUpload();
              setCapturing(true);
            }}
          >
            <Camera size={20} />
            {scanMode === "ai" ? "Mở camera & quét bằng AI" : "Mở camera & bắt đầu"}
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
          {scanMode === "ai" && aiUnavailable && (
            <p className="scan-service ai-service-note" role="status">
              {ai.health?.message || "Dịch vụ AI chưa sẵn sàng."}
              <button className="shop-inline" type="button" onClick={() => void ai.checkHealth()}>
                Kiểm tra lại
              </button>
              <button
                className="shop-inline"
                type="button"
                onClick={() => {
                  resetAiUpload();
                  setScanMode("classic");
                }}
              >
                Chuyển sang quét 3D
              </button>
            </p>
          )}
          {scanMode === "ai" && (
            <>
              <div className="ai-upload-divider">
                <span>hoặc tải ảnh có sẵn</span>
              </div>
              <AiPhotoUpload
                pair={uploadPair}
                onChange={setUploadPair}
                canAnalyze={Boolean(s.consent && validHeight)}
                ready={ai.health?.ready === true}
                analyzing={ai.busy}
                error={uploadPair.front || uploadPair.side ? ai.error : ""}
                onRetry={() => {
                  if (!uploadPair.front || !uploadPair.side) return;
                  lastUploadSignature.current = "";
                  void ai.analyze(
                    { front: uploadPair.front, side: uploadPair.side },
                    s.height,
                    s.captureMode
                  );
                }}
              />
            </>
          )}
          {(s.error || scanContext.jobError) && (
            <p className="fit-error" role="alert">
              {s.error || scanContext.jobError}
            </p>
          )}
          {scanMode === "ai" && ai.error && !uploadPair.front && !uploadPair.side && (
            <p className="fit-error" role="alert">
              {ai.error}
            </p>
          )}
          <div className="scan-privacy">
            <ShieldCheck size={16} />
            <p>
              {scanMode === "ai"
                ? "Quyền riêng tư: hai ảnh chụp được gửi tới Google Gemini qua backend MORPH để ước lượng số đo. Backend không ghi ảnh ra đĩa và không lưu kết quả AI vào hồ sơ hình thể. Kết quả chỉ tồn tại trong phiên trình duyệt hiện tại."
                : "Quyền riêng tư & vòng đời dữ liệu: Khung hình kiểm tra tư thế và hai ảnh chụp được gửi tới máy chủ MORPH để phân tích hình thể 3D, không lưu trữ lâu dài hồ sơ ảnh thô. Mô hình tạm thời tự động xóa sau tối đa 1 giờ (hoặc xóa ngay khi bấm “Chụp lại” / “Xóa”)."}
            </p>
          </div>
        </div>
        <p className="scan-estimate-note">
          {scanMode === "ai"
            ? "AI Vision ước lượng số đo trực tiếp từ hai ảnh bằng Gemini. Chưa kiểm chứng trên người thật; không dùng cho may đo."
            : s.captureMode === "upper_body"
            ? "Ngực/eo ước lượng từ ảnh và tỷ lệ mẫu theo chiều cao; phần mông/chân theo mẫu 3D. Chưa kiểm chứng độ chính xác trên người thật; không dùng cho may đo."
            : "Ngực/eo/mông ước lượng từ hai góc chụp. Chưa kiểm chứng độ chính xác trên người thật; không dùng cho may đo."}
        </p>
      </section>
    </div>
  );
}
