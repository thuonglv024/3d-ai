"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Camera,
  Check,
  LoaderCircle,
  Maximize2,
  Minimize2,
  RotateCcw,
  ScanLine,
  X,
} from "lucide-react";
import CustomSelect from "./CustomSelect";
import PoseGuide from "./PoseGuide";
import {
  CAMERA_QUALITY_THRESHOLDS,
  computePixelQualityMetrics,
  evaluateClientFrameQuality,
  extractGeometryPreservingFrame,
  mapCameraDeviceError,
  pushCandidateFrame,
  resolveThresholds,
  selectBestFrameFromWindow,
  type CameraQualityThresholds,
  type CandidateFrame,
  type CaptureCheckFeedback,
  type ClientFrameQualityEvaluation,
} from "../../lib/captureQuality";

type Pair = { front: File; side: File };

type CaptureWindowTestHooks = {
  __MORPH_TEST_CAMERA_THRESHOLDS__?: Partial<CameraQualityThresholds>;
  __MORPH_TEST_TURN_DURATION_MS__?: number;
  __TEST_CAMERA_CONTROL__?: {
    onCandidateBuffered?: (info: {
      view: "front" | "side";
      candidateCount: number;
      remainingMs: number;
      frameQualityScore: number;
      brightness: number;
      sharpness: number;
      motion: number;
    }) => void;
  };
};

function getActiveThresholds(): CameraQualityThresholds {
  if (typeof window !== "undefined") {
    const win = window as unknown as CaptureWindowTestHooks;
    if (win.__MORPH_TEST_CAMERA_THRESHOLDS__) {
      return resolveThresholds(win.__MORPH_TEST_CAMERA_THRESHOLDS__);
    }
  }
  return CAMERA_QUALITY_THRESHOLDS;
}

export default function CaptureSession({
  mode,
  aiMode = false,
  onComplete,
  onCancel,
}: {
  mode: "upper_body" | "full_body";
  aiMode?: boolean;
  onComplete: (pair: Pair) => void;
  onCancel: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const front = useRef<File | null>(null);
  const frontLandmarks = useRef<number[][] | null>(null);
  const candidateBufferRef = useRef<Array<CandidateFrame<Blob>>>([]);
  const alive = useRef(true);
  const captureLock = useRef(false);
  const run = useRef(0);
  const activeStream = useRef<MediaStream | null>(null);

  const [view, setView] = useState<"front" | "side">("front");
  const [phase, setPhase] = useState<"ready" | "running" | "turn">("ready");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [device, setDevice] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [count, setCount] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<CaptureCheckFeedback | null>(null);
  const [qualityEval, setQualityEval] = useState<ClientFrameQualityEvaluation | null>(null);
  const [statusNotice, setStatusNotice] = useState("");
  const [size, setSize] = useState({ w: 1280, h: 720 });
  const [expanded, setExpanded] = useState(false);

  const upper = mode === "upper_body";

  const toggleExpand = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  useEffect(() => {
    if (!expanded) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        setExpanded(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown, true);
    return () => window.removeEventListener("keydown", handleKeyDown, true);
  }, [expanded]);

  const clearSessionBuffers = useCallback(() => {
    candidateBufferRef.current = [];
  }, []);

  const stopTracks = useCallback(() => {
    clearSessionBuffers();
    if (activeStream.current) {
      activeStream.current.getTracks().forEach((t) => {
        t.onended = null;
        t.stop();
      });
      activeStream.current = null;
    }
    if (video.current?.srcObject) {
      const ms = video.current.srcObject as MediaStream;
      ms.getTracks().forEach((t) => {
        t.onended = null;
        t.stop();
      });
      video.current.srcObject = null;
    }
  }, [clearSessionBuffers]);

  const handleCancel = useCallback(() => {
    front.current = null;
    frontLandmarks.current = null;
    stopTracks();
    onCancel();
  }, [stopTracks, onCancel]);

  const handleDeviceChange = useCallback(
    (nextDeviceId: string) => {
      if (nextDeviceId === device) return;
      stopTracks();
      front.current = null;
      frontLandmarks.current = null;
      setCount(null);
      setFeedback(null);
      setQualityEval(null);
      setStatusNotice("");
      setView("front");
      setPhase("ready");
      setDevice(nextDeviceId);
    },
    [device, stopTracks]
  );

  const handleRetryCamera = useCallback(() => {
    stopTracks();
    front.current = null;
    frontLandmarks.current = null;
    setCount(null);
    setFeedback(null);
    setQualityEval(null);
    setStatusNotice("");
    setError("");
    setAttempt((n) => n + 1);
  }, [stopTracks]);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      stopTracks();
    };
  }, [stopTracks]);

  useEffect(() => {
    let stream: MediaStream | undefined;
    let stopped = false;
    run.current++;
    captureLock.current = false;
    clearSessionBuffers();
    setReady(false);
    setError("");
    setStatusNotice("");
    setPhase("ready");
    setView("front");
    front.current = null;
    frontLandmarks.current = null;
    setCount(null);
    setFeedback(null);
    setQualityEval(null);

    (async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("Camera cần localhost hoặc HTTPS.");
        }
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            ...(device ? { deviceId: { exact: device } } : { facingMode: "user" }),
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });

        if (stopped) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        activeStream.current = stream;
        const el = video.current;
        if (!el) return;
        el.srcObject = stream;
        await el.play();

        if (stopped) return;
        if (el.videoWidth > 0 && el.videoHeight > 0) {
          setSize({ w: el.videoWidth, h: el.videoHeight });
        }
        setReady(true);

        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
          videoTrack.onended = () => {
            if (!stopped && alive.current) {
              clearSessionBuffers();
              front.current = null;
              frontLandmarks.current = null;
              setCount(null);
              setReady(false);
              setPhase("ready");
              setQualityEval(null);
              setError("Camera đã ngắt kết nối giữa chừng. Hãy kiểm tra dây cáp/thiết bị và bấm Thử lại camera.");
            }
          };
        }

        try {
          const devs = await navigator.mediaDevices.enumerateDevices();
          if (!stopped) {
            setDevices(devs.filter((d) => d.kind === "videoinput"));
          }
        } catch {}
      } catch (e) {
        if (!stopped) {
          const mapped = mapCameraDeviceError(e);
          setError(mapped.message);
        }
      }
    })();

    return () => {
      stopped = true;
      run.current++;
      stream?.getTracks().forEach((t) => {
        t.onended = null;
        t.stop();
      });
      stopTracks();
    };
  }, [device, attempt, stopTracks, clearSessionBuffers]);

  useEffect(() => {
    if (phase !== "turn") return;
    const win = typeof window !== "undefined" ? (window as unknown as CaptureWindowTestHooks) : null;
    const turnDurationMs =
      typeof win?.__MORPH_TEST_TURN_DURATION_MS__ === "number"
        ? win.__MORPH_TEST_TURN_DURATION_MS__
        : 3000;
    const timer = setTimeout(() => {
      clearSessionBuffers();
      setPhase("running");
      setFeedback(null);
      setQualityEval(null);
      setStatusNotice("");
    }, turnDurationMs);
    return () => clearTimeout(timer);
  }, [phase, clearSessionBuffers]);

  useEffect(() => {
    if (!ready || phase !== "running") return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let abort: AbortController | undefined;
    let previous: number[][] | null = null;
    let stable = 0;
    let deadline = 0;
    candidateBufferRef.current = [];
    const version = run.current;

    async function check() {
      const el = video.current;
      if (stopped || !el || captureLock.current) return;
      try {
        if (el.videoWidth <= 0 || el.videoHeight <= 0) {
          if (!stopped) timer = setTimeout(check, 250);
          return;
        }

        // Synchronize live preview container aspect ratio with actual camera stream dimensions
        setSize((prev) =>
          prev.w === el.videoWidth && prev.h === el.videoHeight
            ? prev
            : { w: el.videoWidth, h: el.videoHeight }
        );

        // Extract geometry-preserving 720p frame for /api/capture-check (aspectRatioDelta < 0.002)
        const previewExtracted = extractGeometryPreservingFrame(el, { maxDimension: 720 });
        if (!previewExtracted.geometryValid) {
          throw new Error("Tỷ lệ khung hình camera không đồng nhất. Hãy thử lại.");
        }

        const pixelMetrics = computePixelQualityMetrics(previewExtracted.canvas);

        const blob = await new Promise<Blob | null>((r) =>
          previewExtracted.canvas.toBlob(r, "image/jpeg", 0.82)
        );
        if (!blob || stopped) return;

        const body = new FormData();
        body.set("photo", blob, "frame.jpg");
        body.set("view", view);
        body.set("capture_mode", mode);
        body.set("consent", "true");

        abort = new AbortController();
        const timeout = setTimeout(() => abort?.abort(), 5000);
        let response: Response;
        try {
          response = await fetch("/api/capture-check", {
            method: "POST",
            body,
            signal: abort.signal,
          });
        } finally {
          clearTimeout(timeout);
        }

        const data = await response.json();
        if (stopped) return;
        if (!response.ok) {
          throw new Error(
            typeof data.detail === "string" ? data.detail : "Không kiểm tra được tư thế."
          );
        }

        const result = data as CaptureCheckFeedback;
        setFeedback(result);
        setError("");

        const activeThresholds = getActiveThresholds();
        const evaluation = evaluateClientFrameQuality(
          {
            pixelMetrics,
            feedback: result,
            previousLandmarks: previous,
            frontLandmarks: view === "side" ? frontLandmarks.current : null,
            mode,
            view,
          },
          activeThresholds
        );
        setQualityEval(evaluation);

        // Update previous landmarks whenever pose is detected so subsequent frame measures inter-frame motion
        previous =
          result.ready && Array.isArray(result.landmarks) && result.landmarks.length > 0
            ? result.landmarks
            : null;

        if (evaluation.ok) {
          stable++;
          setStatusNotice("");
          const now = Date.now();
          if (stable >= activeThresholds.minStableFramesBeforeCountdown && !deadline) {
            deadline = now + activeThresholds.countdownDurationMs;
            candidateBufferRef.current = [];
          }

          if (deadline) {
            const remainingMs = deadline - now;
            setCount(Math.max(1, Math.ceil(remainingMs / 1000)));

            // Within the final bestFrameWindowMs (1.6s), buffer full-resolution candidate frames
            if (remainingMs <= activeThresholds.bestFrameWindowMs) {
              const fullExtracted = extractGeometryPreservingFrame(el, { maxDimension: null });
              const candidateBlob = await new Promise<Blob | null>((r) =>
                fullExtracted.canvas.toBlob(r, "image/jpeg", 0.92)
              );
              if (stopped || !alive.current || version !== run.current) return;
              if (candidateBlob && fullExtracted.geometryValid) {
                candidateBufferRef.current = pushCandidateFrame(
                  candidateBufferRef.current,
                  {
                    timestampMs: Date.now(),
                    frameQualityScore: evaluation.frameQualityScore,
                    motion: evaluation.motion,
                    sharpness: evaluation.sharpness,
                    meanVisibility: evaluation.meanVisibility,
                    brightness: evaluation.brightness,
                    ready: true,
                    landmarks: result.landmarks,
                    payload: candidateBlob,
                  },
                  deadline,
                  activeThresholds
                );
                if (typeof window !== "undefined") {
                  (window as unknown as CaptureWindowTestHooks).__TEST_CAMERA_CONTROL__?.onCandidateBuffered?.({
                    view,
                    candidateCount: candidateBufferRef.current.length,
                    remainingMs,
                    frameQualityScore: evaluation.frameQualityScore,
                    brightness: evaluation.brightness,
                    sharpness: evaluation.sharpness,
                    motion: evaluation.motion,
                  });
                }
              }
            }

            if (Date.now() >= deadline) {
              captureLock.current = true;
              const bestCandidate = selectBestFrameFromWindow(candidateBufferRef.current, {
                nowMs: Date.now(),
                deadlineMs: deadline,
                overrides: activeThresholds,
              });

              let captured: Blob | null = bestCandidate?.payload ?? null;
              const chosenLandmarks = bestCandidate?.landmarks ?? result.landmarks;

              if (!captured) {
                const fullFallback = extractGeometryPreservingFrame(el, { maxDimension: null });
                captured = await new Promise<Blob | null>((r) =>
                  fullFallback.canvas.toBlob(r, "image/jpeg", 0.92)
                );
              }
              candidateBufferRef.current = [];

              if (stopped || !alive.current || version !== run.current) return;
              if (!captured) throw new Error("Chưa chụp được ảnh. Hãy thử lại.");

              const file = new File([captured], view + ".jpg", { type: "image/jpeg" });
              setCount(null);
              if (view === "front") {
                front.current = file;
                frontLandmarks.current = chosenLandmarks;
                setView("side");
                setFeedback(null);
                setQualityEval(null);
                setStatusNotice("");
                setPhase("turn");
                captureLock.current = false;
              } else if (front.current) {
                stopTracks();
                onComplete({ front: front.current, side: file });
              }
              return;
            }
          }
        } else {
          // Immediately cancel countdown and clear candidate buffer if any condition is lost
          const wasCountingDown = deadline > 0;
          stable = 0;
          deadline = 0;
          candidateBufferRef.current = [];
          setCount(null);
          setStatusNotice((prev) =>
            wasCountingDown || prev.startsWith("Đã tạm dừng đếm ngược:")
              ? `Đã tạm dừng đếm ngược: ${evaluation.message}`
              : evaluation.message
          );
        }
      } catch (e) {
        if (stopped) return;
        captureLock.current = false;
        stable = 0;
        deadline = 0;
        previous = null;
        candidateBufferRef.current = [];
        setCount(null);
        setError(e instanceof Error ? e.message : "Mất kết nối kiểm tra tư thế.");
      }
      if (!stopped) timer = setTimeout(check, 400);
    }

    void check();
    return () => {
      stopped = true;
      abort?.abort();
      clearTimeout(timer);
      candidateBufferRef.current = [];
    };
  }, [ready, phase, view, mode, upper, onComplete, stopTracks]);

  const isPoseAndQualityReady = Boolean(feedback?.ready && qualityEval?.ok);

  return (
    <section
      className={`capture-session ${expanded ? "is-expanded" : ""}`}
      aria-label="Quét hai góc liên tục"
    >
      <header className="capture-session-head">
        <div className="capture-session-head-left">
          <strong>Camera trực tiếp</strong>
          <span>{view === "front" ? "01 · Chính diện" : "02 · Góc nghiêng"}</span>
          <span className="capture-mode-tag">{upper ? "Thân trên" : "Toàn thân"}</span>
          {aiMode && <span className="capture-mode-tag is-ai">AI Vision</span>}
        </div>
        <div className="capture-session-head-right">
          <CustomSelect
            ariaLabel="Chọn camera"
            value={device}
            disabled={captureLock.current}
            onChange={handleDeviceChange}
            options={[
              { value: "", label: "Camera mặc định" },
              ...devices.map((d, i) => ({
                value: d.deviceId,
                label: d.label || `Camera ${i + 1}`,
              })),
            ]}
            size="sm"
            variant="header"
            className="capture-device-select"
          />
          <button
            type="button"
            className="capture-expand-btn"
            onClick={toggleExpand}
            aria-label={expanded ? "Thu nhỏ camera" : "Mở rộng camera"}
            title={expanded ? "Thu nhỏ (Esc)" : "Mở rộng camera"}
          >
            {expanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
          <button
            type="button"
            className="capture-close-btn"
            onClick={handleCancel}
            aria-label="Đóng camera"
            title="Đóng camera"
          >
            <X size={19} />
          </button>
        </div>
      </header>

      <div className="capture-session-body">
        <div className="capture-stage-wrapper">
          <div
            className={`capture-live ${isPoseAndQualityReady ? "pose-ready" : ""}`}
            style={{ aspectRatio: `${size.w}/${size.h}` }}
          >
            <video
              ref={video}
              playsInline
              muted
              onLoadedMetadata={(e) => {
                const v = e.currentTarget;
                if (v.videoWidth > 0 && v.videoHeight > 0) {
                  setSize({ w: v.videoWidth, h: v.videoHeight });
                }
              }}
            />
            <PoseGuide upper={upper} ready={isPoseAndQualityReady} />
            <div className="capture-frame-mark" aria-hidden="true" />
            <div className="capture-view-pill" aria-hidden="true">
              <span className="capture-view-pill-dot" />
              <span>{view === "front" ? "01 · Chính diện" : "02 · Góc nghiêng 90°"}</span>
            </div>
            {!ready && !error && (
              <div className="capture-overlay">
                <LoaderCircle className="spin" size={28} />
                <p>Đang mở camera…</p>
              </div>
            )}
            {!ready && error && (
              <div className="capture-overlay capture-overlay-error" role="alert">
                <AlertTriangle size={28} />
                <strong>Không thể truy cập camera</strong>
                <p>{error}</p>
                <button
                  className="capture-primary"
                  type="button"
                  onClick={handleRetryCamera}
                  style={{ maxWidth: 220, marginTop: 12 }}
                >
                  <RotateCcw size={16} />
                  Thử lại camera
                </button>
              </div>
            )}
            {count !== null && (
              <div className="capture-count" aria-live="polite">
                {count}
              </div>
            )}
            {phase === "turn" && (
              <div className="capture-turn" role="status">
                <Check size={26} />
                <strong>Đã chụp chính diện</strong>
                <RotateCcw size={44} />
                <h2>Xoay người 90°</h2>
                <p>Giữ nguyên vị trí đứng. Camera sẽ tự đếm ngược khi bạn đứng đúng góc và giữ yên.</p>
              </div>
            )}
          </div>
        </div>

        <aside className="capture-sidebar">
          <div className="capture-progress" aria-label="Tiến độ chụp">
            <span className={view === "front" ? "active" : "done"}>
              {view === "side" ? <Check size={15} /> : "01"} Chính diện
            </span>
            <i />
            <span className={view === "side" ? "active" : ""}>02 Góc nghiêng</span>
          </div>

          <div className="capture-instruction capture-guide-card">
            <span className="capture-guide-step">
              {view === "front" ? "Bước 01 / 02" : "Bước 02 / 02"}
              {aiMode ? " · AI Vision" : ""}
            </span>
            <h2>{view === "front" ? "Hướng hai vai về camera" : "Xoay nghiêng người 90°"}</h2>
            <p>
              {upper
                ? "Thấy rõ đầu, hai vai, eo và cạp quần · Khoảng cách 1.5–2m"
                : "Giữ toàn bộ đầu và bàn chân trong khung · Khoảng cách 2–2.5m"}
            </p>
          </div>

          <div
            className={`capture-status capture-status-card ${
              statusNotice && phase === "running" && !isPoseAndQualityReady ? "has-warning" : ""
            }`}
            role="status"
          >
            <span className="capture-status-badge-title">Trạng thái nhận diện & chất lượng</span>
            <div className="capture-status-message">
              {error ||
                (phase === "ready"
                  ? "Sẵn sàng? Bấm bắt đầu, sau đó đứng vào giữa khung."
                  : phase === "turn"
                  ? "Đang chuyển sang góc nghiêng 90°…"
                  : count !== null
                  ? `Giữ yên · Đang chọn khung hình nét nhất (${count}s)`
                  : statusNotice || feedback?.message || "Đang kiểm tra tư thế và ánh sáng…")}
            </div>
            {phase === "running" && qualityEval && (
              <div className="capture-quality-pills" aria-label="Chỉ báo chất lượng khung hình">
                <span
                  className={`capture-quality-pill ${
                    qualityEval.issue === "too_dark" || qualityEval.issue === "too_bright"
                      ? "is-warn"
                      : "is-ok"
                  }`}
                >
                  Ánh sáng:{" "}
                  {qualityEval.issue === "too_dark"
                    ? "Thiếu sáng"
                    : qualityEval.issue === "too_bright"
                    ? "Ngược sáng"
                    : "Đạt"}
                </span>
                <span
                  className={`capture-quality-pill ${
                    qualityEval.issue === "too_blurry" || qualityEval.issue === "excessive_motion"
                      ? "is-warn"
                      : "is-ok"
                  }`}
                >
                  Độ nét: {qualityEval.ok ? "Ổn định" : "Cần giữ yên"}
                </span>
                {view === "side" && (
                  <span
                    className={`capture-quality-pill ${
                      qualityEval.issue === "cross_view_drift" ? "is-warn" : "is-ok"
                    }`}
                  >
                    Khoảng cách: {qualityEval.crossViewCompatible ? "Khớp góc 01" : "Lệch vị trí"}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="capture-posture-tips">
            <strong>Mẹo nhận diện tối ưu:</strong>
            <p>
              {upper
                ? "Đặt máy cao ngang ngực hoặc eo, đứng thẳng tự nhiên, không để áo dài trùm che mất cạp quần."
                : "Đứng thẳng tự nhiên, hai tay thả lỏng, giữ nguyên khoảng cách đứng giữa hai góc chụp."}
            </p>
          </div>

          <footer className="capture-session-actions">
            {!ready && error ? (
              <button
                className="capture-primary"
                type="button"
                onClick={handleRetryCamera}
              >
                <RotateCcw size={18} />
                Thử lại camera
              </button>
            ) : phase === "ready" ? (
              <button
                className="capture-primary"
                type="button"
                disabled={!ready}
                onClick={() => setPhase("running")}
              >
                <Camera size={18} />
                Bắt đầu quét
                <ArrowRight size={18} />
              </button>
            ) : (
              <p className="capture-auto-info">
                <ScanLine size={18} />
                Tự chọn frame nét nhất · Không cần bấm thêm
              </p>
            )}
            <button className="capture-cancel" type="button" onClick={handleCancel}>
              Hủy phiên
            </button>
          </footer>
        </aside>
      </div>
    </section>
  );
}


