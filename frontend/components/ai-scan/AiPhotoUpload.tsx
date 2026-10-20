"use client";

import { useEffect, useState } from "react";
import { ImagePlus, LoaderCircle, ShieldCheck, Sparkles, Upload, X } from "lucide-react";

export type AiUploadPair = { front: File | null; side: File | null };

const MAX_BYTES = 10 * 1024 * 1024;

function validateFile(file: File): string {
  if (/\.(heic|heif)$/i.test(file.name) || /image\/(heic|heif)/i.test(file.type)) {
    return "Ảnh HEIC/HEIF chưa được hỗ trợ. Hãy chuyển sang JPG, PNG hoặc WebP.";
  }
  if (!/^image\/(jpeg|png|webp)$/i.test(file.type)) {
    return "Chỉ hỗ trợ ảnh JPG, PNG hoặc WebP.";
  }
  if (file.size > MAX_BYTES) {
    return "Mỗi ảnh tối đa 10 MB.";
  }
  return "";
}

function Slot({
  slot,
  label,
  hint,
  file,
  preview,
  disabled,
  onPick,
  onClear,
}: {
  slot: "front" | "side";
  label: string;
  hint: string;
  file: File | null;
  preview: string;
  disabled: boolean;
  onPick: (slot: "front" | "side", file: File | null) => void;
  onClear: (slot: "front" | "side") => void;
}) {
  const [dragging, setDragging] = useState(false);
  const inputId = `ai-upload-${slot}`;

  return (
    <div
      className={`ai-upload-slot ${file ? "has-file" : ""} ${dragging ? "is-drag" : ""}`}
      onDragOver={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragging(false);
        const dropped = e.dataTransfer.files?.[0];
        if (dropped) onPick(slot, dropped);
      }}
    >
      <input
        id={inputId}
        className="ai-upload-input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        disabled={disabled}
        onChange={(e) => {
          const picked = e.target.files?.[0] || null;
          onPick(slot, picked);
          e.target.value = "";
        }}
      />
      <label className="ai-upload-hit" htmlFor={inputId} aria-disabled={disabled}>
        {preview ? (
          <img src={preview} alt={label} />
        ) : (
          <span className="ai-upload-placeholder">
            {slot === "front" ? <ImagePlus size={26} /> : <Upload size={26} />}
            <strong>{label}</strong>
            <small>{hint}</small>
            <small className="ai-upload-cta">Chọn hoặc kéo ảnh vào đây</small>
          </span>
        )}
        <span className="ai-upload-label">
          {slot === "front" ? "01" : "02"} · {label}
        </span>
      </label>
      {file && !disabled && (
        <button
          type="button"
          className="ai-upload-clear"
          aria-label={`Xóa ảnh ${label}`}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onClear(slot);
          }}
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

export default function AiPhotoUpload({
  pair,
  onChange,
  canAnalyze,
  ready,
  analyzing,
  error,
  onRetry,
}: {
  pair: AiUploadPair;
  onChange: (pair: AiUploadPair) => void;
  canAnalyze: boolean;
  ready: boolean;
  analyzing: boolean;
  error: string;
  onRetry: () => void;
}) {
  const [localError, setLocalError] = useState("");
  const [previews, setPreviews] = useState({ front: "", side: "" });

  useEffect(() => {
    const front = pair.front ? URL.createObjectURL(pair.front) : "";
    const side = pair.side ? URL.createObjectURL(pair.side) : "";
    setPreviews({ front, side });
    return () => {
      if (front) URL.revokeObjectURL(front);
      if (side) URL.revokeObjectURL(side);
    };
  }, [pair.front, pair.side]);

  function pick(slot: "front" | "side", file: File | null) {
    if (!file) {
      onChange({ ...pair, [slot]: null });
      return;
    }
    const problem = validateFile(file);
    if (problem) {
      setLocalError(problem);
      return;
    }
    setLocalError("");
    onChange({ ...pair, [slot]: file });
  }

  function clear(slot: "front" | "side") {
    setLocalError("");
    onChange({ ...pair, [slot]: null });
  }

  const complete = Boolean(pair.front && pair.side);

  return (
    <section className="ai-upload-panel" aria-label="Tải ảnh để phân tích bằng AI">
      <div className="ai-upload-head">
        <Upload size={18} />
        <div>
          <strong>Hoặc tải ảnh có sẵn</strong>
          <span>
            Chọn hai ảnh của cùng một người: chính diện và nghiêng 90°. Ảnh chỉ được gửi
            tới AI để ước lượng, không lưu trên máy chủ MORPH.
          </span>
        </div>
      </div>

      <div className="ai-upload-grid">
        <Slot
          slot="front"
          label="Chính diện"
          hint="Đứng thẳng, thấy đầu đến cạp quần"
          file={pair.front}
          preview={previews.front}
          disabled={!ready}
          onPick={pick}
          onClear={clear}
        />
        <Slot
          slot="side"
          label="Góc nghiêng 90°"
          hint="Xoay thân, giữ cùng khoảng cách"
          file={pair.side}
          preview={previews.side}
          disabled={!ready}
          onPick={pick}
          onClear={clear}
        />
      </div>

      {(localError || error) && (
        <p className="fit-error" role="alert">
          {localError || error}
        </p>
      )}

      <div className="ai-upload-status" role="status">
        {analyzing ? (
          <>
            <LoaderCircle size={15} className="spin" />
            AI đang phân tích hai ảnh…
          </>
        ) : !ready ? (
          <>
            <ShieldCheck size={15} />
            AI chưa sẵn sàng. Kiểm tra cấu hình GOOGLE_API_KEY của backend.
          </>
        ) : complete && canAnalyze ? (
          <>
            <Sparkles size={15} />
            Đủ hai ảnh — AI sẽ tự phân tích ngay.
          </>
        ) : complete ? (
          <>
            <ShieldCheck size={15} />
            Nhập chiều cao và đồng ý xử lý ảnh để AI tự phân tích.
          </>
        ) : (
          <>
            <ShieldCheck size={15} />
            Cần đủ ảnh chính diện và ảnh nghiêng 90°.
          </>
        )}
      </div>

      {error && complete && ready && !analyzing && (
        <button type="button" className="scan-btn-subtle" onClick={onRetry}>
          <Sparkles size={14} />
          Thử phân tích lại
        </button>
      )}
    </section>
  );
}
