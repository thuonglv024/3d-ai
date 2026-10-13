"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { ArrowRight, Camera, Check, LoaderCircle, Maximize2, Minimize2, RotateCcw, ScanLine, X } from "lucide-react";
import CustomSelect, { type SelectOption } from "./CustomSelect";

type Feedback = { ready: boolean; message: string; landmarks: number[][] };
type Pair = { front: File; side: File };

export default function CaptureSession({
  mode,
  onComplete,
  onCancel,
}: {
  mode: "upper_body" | "full_body";
  onComplete: (pair: Pair) => void;
  onCancel: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const front = useRef<File | null>(null);
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
  const [feedback, setFeedback] = useState<Feedback | null>(null);
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

  const stopTracks = useCallback(() => {
    if (activeStream.current) {
      activeStream.current.getTracks().forEach((t) => t.stop());
      activeStream.current = null;
    }
    if (video.current?.srcObject) {
      const ms = video.current.srcObject as MediaStream;
      ms.getTracks().forEach((t) => t.stop());
      video.current.srcObject = null;
    }
  }, []);

  const handleCancel = useCallback(() => {
    stopTracks();
    onCancel();
  }, [stopTracks, onCancel]);

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
    setReady(false);
    setError("");
    setPhase("ready");
    setView("front");
    front.current = null;
    setCount(null);
    setFeedback(null);

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
        setSize({ w: el.videoWidth, h: el.videoHeight });
        setReady(true);

        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
          videoTrack.onended = () => {
            if (!stopped) {
              setReady(false);
              setPhase("ready");
              setError("Camera đã ngắt. Kết nối lại và bắt đầu phiên mới.");
            }
          };
        }

        try {
          const devs = await navigator.mediaDevices.enumerateDevices();
          setDevices(devs.filter((d) => d.kind === "videoinput"));
        } catch {}
      } catch (e) {
        if (!stopped) {
          setError(
            e instanceof DOMException && e.name === "NotAllowedError"
              ? "Chưa được cấp quyền camera. Cho phép camera trong trình duyệt rồi thử lại."
              : "Không mở được camera. Đóng ứng dụng đang dùng camera rồi thử lại."
          );
        }
      }
    })();

    return () => {
      stopped = true;
      run.current++;
      stream?.getTracks().forEach((t) => t.stop());
      stopTracks();
    };
  }, [device, attempt, stopTracks]);

  useEffect(() => {
    if (phase !== "turn") return;
    const timer = setTimeout(() => {
      setPhase("running");
      setFeedback(null);
    }, 4000);
    return () => clearTimeout(timer);
  }, [phase]);

  useEffect(() => {
    if (!ready || phase !== "running") return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let abort: AbortController | undefined;
    let previous: number[][] | null = null;
    let stable = 0;
    let deadline = 0;
    const version = run.current;

    async function check() {
      const el = video.current;
      if (stopped || !el || captureLock.current) return;
      try {
        const canvas = document.createElement("canvas");
        const scale = Math.min(1, 720 / Math.max(el.videoWidth, el.videoHeight));
        canvas.width = Math.round(el.videoWidth * scale);
        canvas.height = Math.round(el.videoHeight * scale);
        canvas.getContext("2d")?.drawImage(el, 0, 0, canvas.width, canvas.height);

        const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.8));
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
          response = await fetch("/api/capture-check", { method: "POST", body, signal: abort.signal });
        } finally {
          clearTimeout(timeout);
        }

        const data = await response.json();
        if (stopped) return;
        if (!response.ok) {
          throw new Error(typeof data.detail === "string" ? data.detail : "Không kiểm tra được tư thế.");
        }

        const result = data as Feedback;
        setFeedback(result);
        setError("");

        const visible = (upper ? [0, 11, 12, 23, 24] : [11, 12, 23, 24, 25, 26, 27, 28]).filter(
          (i) => result.landmarks[i]?.[2] > 0.55 && (previous?.[i]?.[2] || 0) > 0.55
        );
        const motion =
          previous && visible.length >= 4
            ? visible.reduce(
                (n, i) =>
                  n +
                  Math.hypot(
                    result.landmarks[i][0] - previous![i][0],
                    result.landmarks[i][1] - previous![i][1]
                  ),
                0
              ) / visible.length
            : Infinity;

        previous = result.ready ? result.landmarks : null;

        if (result.ready && motion < 0.018) {
          stable++;
          if (stable >= 3 && !deadline) deadline = Date.now() + 5000;
          if (deadline) {
            setCount(Math.max(1, Math.ceil((deadline - Date.now()) / 1000)));
            if (Date.now() >= deadline) {
              captureLock.current = true;
              const full = document.createElement("canvas");
              full.width = el.videoWidth;
              full.height = el.videoHeight;
              full.getContext("2d")?.drawImage(el, 0, 0);
              const captured = await new Promise<Blob | null>((r) => full.toBlob(r, "image/jpeg", 0.92));
              if (stopped || !alive.current || version !== run.current) return;
              if (!captured) throw new Error("Chưa chụp được ảnh. Hãy thử lại.");

              const file = new File([captured], view + ".jpg", { type: "image/jpeg" });
              setCount(null);
              if (view === "front") {
                front.current = file;
                setView("side");
                setFeedback(null);
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
          stable = 0;
          deadline = 0;
          setCount(null);
        }
      } catch (e) {
        if (stopped) return;
        captureLock.current = false;
        stable = 0;
        deadline = 0;
        previous = null;
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
    };
  }, [ready, phase, view, mode, upper, onComplete, stopTracks]);

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
        </div>
        <div className="capture-session-head-right">
          <CustomSelect
            ariaLabel="Chọn camera"
            value={device}
            disabled={phase !== "ready"}
            onChange={(val) => setDevice(val)}
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
            className={`capture-live ${feedback?.ready ? "pose-ready" : ""}`}
            style={{ aspectRatio: `${size.w}/${size.h}` }}
          >
            <video ref={video} playsInline muted />
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
                <p>Giữ nguyên vị trí. Camera sẽ tự đếm ngược khi bạn đứng đúng góc.</p>
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
            </span>
            <h2>{view === "front" ? "Hướng hai vai về camera" : "Xoay nghiêng người 90°"}</h2>
            <p>
              {upper
                ? "Thấy rõ đầu, hai vai, eo và cạp quần · Khoảng cách 1.5–2m"
                : "Giữ toàn bộ đầu và bàn chân trong khung · Khoảng cách 2–2.5m"}
            </p>
          </div>

          <div className="capture-status capture-status-card" role="status">
            <span className="capture-status-badge-title">Trạng thái nhận diện AI</span>
            <div className="capture-status-message">
              {error ||
                (phase === "ready"
                  ? "Sẵn sàng? Bấm bắt đầu, sau đó đứng vào giữa khung."
                  : phase === "turn"
                  ? "Đang chuyển sang góc nghiêng…"
                  : count !== null
                  ? `Giữ yên · Chụp sau ${count} giây`
                  : feedback?.message || "Đang nhận diện tư thế…")}
            </div>
          </div>

          <div className="capture-posture-tips">
            <strong>Mẹo nhận diện tối ưu:</strong>
            <p>
              {upper
                ? "Đặt máy cao ngang ngực hoặc eo, đứng thẳng tự nhiên, không để áo dài trùm che mất cạp quần."
                : "Đứng thẳng tự nhiên, hai tay thả lỏng, đảm bảo đủ ánh sáng phòng."}
            </p>
          </div>

          <footer className="capture-session-actions">
            {!ready && error ? (
              <button
                className="capture-primary"
                type="button"
                onClick={() => setAttempt((n) => n + 1)}
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
                Tự chụp hai góc · Không cần bấm thêm
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
