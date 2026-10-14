"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, CheckCircle2, Sparkles, Volume2, VolumeX, X } from "lucide-react";

function playBeep(freq = 600, duration = 0.12, type: OscillatorType = "sine") {
  try {
    const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) return;
    const ctx = new AudioContextClass();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.18, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch {
    // Audio autoplay policy fallback
  }
}

export default function CameraCapture({ side, onCapture, onClose }: { side: boolean; onCapture: (file: File) => void; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const motionCanvas = useRef<HTMLCanvasElement | null>(null);
  const prevFrame = useRef<Uint8Array | null>(null);

  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [count, setCount] = useState<number | null>(null);
  const [autoCapture, setAutoCapture] = useState(true);
  const [sound, setSound] = useState(true);
  const [isStable, setIsStable] = useState(false);
  const [flashing, setFlashing] = useState(false);
  const stableCount = useRef(0);

  // Initialize camera stream with fallback
  useEffect(() => {
    let stopped = false;
    dialog.current?.showModal();

    (async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("Camera cần localhost hoặc kết nối HTTPS. Bạn có thể tải ảnh thay thế.");
        }
        let media: MediaStream;
        try {
          media = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment", width: { ideal: 1080 }, height: { ideal: 1440 } },
            audio: false,
          });
        } catch {
          media = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 1080 }, height: { ideal: 1440 } },
            audio: false,
          });
        }
        if (stopped) {
          media.getTracks().forEach(t => t.stop());
          return;
        }
        stream.current = media;
        if (video.current) {
          video.current.srcObject = media;
          await video.current.play();
          setReady(true);
        }
      } catch (e) {
        setError(e instanceof Error ? `Không mở được camera. ${e.message}` : "Hãy cho phép truy cập camera hoặc tải ảnh có sẵn.");
      }
    })();

    return () => {
      stopped = true;
      stream.current?.getTracks().forEach(t => t.stop());
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  // Trigger snapshot logic
  function performSnap() {
    setFlashing(true);
    if (sound) playBeep(880, 0.25, "triangle");

    setTimeout(() => {
      const el = video.current;
      if (!el?.videoWidth) {
        setError("Camera chưa sẵn sàng. Hãy thử lại.");
        setCount(null);
        setFlashing(false);
        return;
      }
      const canvas = document.createElement("canvas");
      canvas.width = el.videoWidth;
      canvas.height = el.videoHeight;
      canvas.getContext("2d")?.drawImage(el, 0, 0);
      canvas.toBlob(blob => {
        if (blob) {
          onCapture(new File([blob], side ? "side.jpg" : "front.jpg", { type: "image/jpeg" }));
          onClose();
        } else {
          setError("Không chụp được ảnh. Hãy thử lại.");
          setCount(null);
          setFlashing(false);
        }
      }, "image/jpeg", 0.92);
    }, 100);
  }

  // Countdown controller
  function startCountdown(seconds = 3) {
    if (count !== null) return;
    setCount(seconds);
    if (sound) playBeep(520, 0.12);

    let remaining = seconds;
    timer.current = setInterval(() => {
      remaining -= 1;
      if (remaining > 0) {
        setCount(remaining);
        if (sound) playBeep(remaining === 1 ? 650 : 520, 0.14);
        return;
      }
      if (timer.current) clearInterval(timer.current);
      setCount(null);
      performSnap();
    }, 1000);
  }

  // Real-time Motion & Stability Detector (Smart Auto-Capture)
  useEffect(() => {
    if (!ready || !autoCapture || count !== null) return;

    if (!motionCanvas.current) {
      const c = document.createElement("canvas");
      c.width = 48;
      c.height = 64;
      motionCanvas.current = c;
    }

    const checkInterval = setInterval(() => {
      const el = video.current;
      const cvs = motionCanvas.current;
      if (!el || !cvs || el.readyState < 2) return;

      const ctx = cvs.getContext("2d", { willReadFrequently: true });
      if (!ctx) return;

      ctx.drawImage(el, 0, 0, cvs.width, cvs.height);
      const imgData = ctx.getImageData(0, 0, cvs.width, cvs.height).data;
      const currentGray = new Uint8Array(cvs.width * cvs.height);

      let totalBrightness = 0;
      for (let i = 0; i < currentGray.length; i++) {
        const val = (imgData[i * 4] * 299 + imgData[i * 4 + 1] * 587 + imgData[i * 4 + 2] * 114) / 1000;
        currentGray[i] = val;
        totalBrightness += val;
      }
      const avgBrightness = totalBrightness / currentGray.length;

      if (prevFrame.current) {
        let diffSum = 0;
        for (let i = 0; i < currentGray.length; i++) {
          diffSum += Math.abs(currentGray[i] - prevFrame.current[i]);
        }
        const avgMotion = diffSum / currentGray.length;

        // Condition: Adequate lighting (> 35) and low movement (standing still)
        if (avgBrightness > 35 && avgMotion < 8.5) {
          stableCount.current += 1;
          if (stableCount.current >= 4) {
            setIsStable(true);
            if (stableCount.current === 5 && count === null) {
              startCountdown(3);
            }
          }
        } else {
          stableCount.current = 0;
          setIsStable(false);
        }
      }
      prevFrame.current = currentGray;
    }, 250);

    return () => clearInterval(checkInterval);
  }, [ready, autoCapture, count, sound]);

  return (
    <dialog ref={dialog} className="camera-dialog" onCancel={onClose}>
      <div className="dialog-title">
        <h2>Chụp {side ? "góc nghiêng (02)" : "chính diện (01)"}</h2>
        <button className="icon-button" onClick={onClose} aria-label="Đóng camera">
          <X size={20} />
        </button>
      </div>
      <p>
        {side
          ? "Đặt máy cố định, lùi xa thấy đủ đầu và chân. Xoay người 90°, giữ tay hơi áp phía sau thân."
          : "Đặt máy cố định, lùi xa thấy đủ đầu và chân. Đứng thẳng, hai tay hơi tách khỏi thân."}
      </p>

      <div className="smart-controls">
        <label className="smart-toggle">
          <input
            type="checkbox"
            checked={autoCapture}
            onChange={e => {
              setAutoCapture(e.target.checked);
              setIsStable(false);
              stableCount.current = 0;
            }}
          />
          <Sparkles size={14} />
          <span>Tự động bắt hình khi đứng yên</span>
        </label>
        <button
          type="button"
          className="text-button sound-badge"
          onClick={() => setSound(!sound)}
          aria-label={sound ? "Tắt âm thanh" : "Bật âm thanh"}
        >
          {sound ? <Volume2 size={15} /> : <VolumeX size={15} />}
          <span>{sound ? "Âm thanh: Bật" : "Âm thanh: Tắt"}</span>
        </button>
      </div>

      <div className="camera-frame">
        <video ref={video} playsInline muted />
        <div className={`capture-guide ${side ? "side" : ""} ${isStable ? "aligned" : ""}`} aria-hidden="true" />
        <span className="frame-hint">Giữ toàn thân trong khung viền</span>

        {/* Dynamic status badge */}
        {ready && count === null && (
          <div className={`guide-badge ${isStable ? "ready" : ""}`}>
            {isStable ? <CheckCircle2 size={13} /> : <Sparkles size={13} />}
            <span>
              {isStable
                ? "Tư thế chuẩn · Chuẩn bị chụp..."
                : autoCapture
                  ? "Hãy đứng thẳng và giữ yên trong khung hình"
                  : "Căn người vào khung rồi bấm Chụp"}
            </span>
          </div>
        )}

        {/* Countdown display */}
        {count !== null && <span className="countdown" aria-live="assertive">{count}</span>}

        {/* Shutter flash animation */}
        {flashing && <div className="camera-flash" />}
      </div>

      {error && <p role="alert" className="error-message">{error}</p>}

      <button
        className="primary"
        disabled={!ready || count !== null}
        onClick={() => startCountdown(3)}
      >
        <Camera size={18} /> {count !== null ? `Đang đếm ngược (${count})` : "Chụp ảnh (Đếm 3s)"}
      </button>
    </dialog>
  );
}
