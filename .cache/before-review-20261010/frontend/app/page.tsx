"use client";

import dynamic from "next/dynamic";
import { Component, type ErrorInfo, type ReactNode, useEffect, useRef, useState } from "react";
import { ArrowRight, Box, Camera, Check, CheckCircle2, Download, Info, LoaderCircle, Maximize, Mouse, RotateCcw, Ruler, ScanLine, ShieldCheck, Sparkles, Sun, Trash2, Upload, X } from "lucide-react";
import CameraCapture from "../components/CameraCapture";

const BodyViewer = dynamic(() => import("../components/BodyViewer"), { ssr: false, loading: () => <div className="viewer-loading"><LoaderCircle className="spin" size={24} /> Đang mở không gian 3D…</div> });
type Health = { ready: boolean; engine: string; message: string };
type Measurements = { height_cm?: number; chest_cm?: number; waist_cm?: number; hip_cm?: number; shoulder_width_cm?: number; inseam_cm?: number };
type BodyProfile = { shape?: string; shape_description?: string; top_size?: string; bottom_size?: string; fit_type?: string };
type Job = { id: string; status: "queued" | "processing" | "completed" | "failed"; stage: string; error?: string; model_url?: string; warnings?: string[]; measurements?: Measurements; body_profile?: BodyProfile; elapsed_seconds?: number };
type Slot = "front" | "side";

class ViewerBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) {}
  render() { return this.state.failed ? <div className="viewer-loading">Không mở được mô hình 3D. Hãy tải lại trang hoặc tải file GLB để xem.</div> : this.props.children; }
}

function PhotoInput({ side, file, disabled, onFile, onCamera }: { side: boolean; file: File | null; disabled: boolean; onFile: (file: File | null) => void; onCamera: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState("");
  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  return <div className="photo-slot">
    <div className="slot-label"><span>{side ? "Góc nghiêng" : "Chính diện"}</span><span className="slot-number">{side ? "02" : "01"}</span></div>
    <input ref={input} aria-label={`Ảnh ${side ? "góc nghiêng" : "chính diện"}`} type="file" accept="image/jpeg,image/png,image/webp" hidden disabled={disabled} onChange={e => { const next = e.target.files?.[0]; if (next) onFile(next); e.target.value = ""; }} />
    <button type="button" disabled={disabled} className={`upload-area ${preview ? "has-photo" : ""}`} onClick={() => input.current?.click()} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (!disabled && e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]); }} aria-label={`${preview ? "Thay" : "Chọn"} ảnh ${side ? "góc nghiêng" : "chính diện"}`}>
      {preview ? <img src={preview} alt={`Ảnh ${side ? "góc nghiêng" : "chính diện"} đã chọn`} /> : <><div className="photo-guide"><ScanLine size={52} strokeWidth={1} /><span>{side ? "Xoay nghiêng 90°" : "Đứng thẳng, thấy toàn thân"}</span></div><Upload size={21} /><strong>Chọn ảnh</strong><small>JPG, PNG, WebP · tối đa 10 MB</small></>}
      {preview && <span className="replace-label"><Check size={14} /> Đã chọn · bấm để thay</span>}
    </button>
    <div className="slot-actions"><button type="button" className="text-button" disabled={disabled} onClick={onCamera}><Camera size={15} /> Chụp ảnh</button>{file && <button type="button" className="icon-button" disabled={disabled} onClick={() => onFile(null)} aria-label={`Xóa ảnh ${side ? "nghiêng" : "chính diện"}`}><X size={15} /></button>}</div>
  </div>;
}

export default function Page() {
  const [front, setFront] = useState<File | null>(null);
  const [side, setSide] = useState<File | null>(null);
  const [height, setHeight] = useState("170");
  const [consent, setConsent] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [camera, setCamera] = useState<Slot | null>(null);
  const [wireframe, setWireframe] = useState(false);
  const [rotation, setRotation] = useState(false);
  const [showRings, setShowRings] = useState(true);
  const [reset, setReset] = useState(0);
  const [privacy, setPrivacy] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pollRetry, setPollRetry] = useState(0);
  const viewport = useRef<HTMLDivElement>(null);
  const busy = submitting || job?.status === "queued" || job?.status === "processing";
  const complete = job?.status === "completed";

  async function checkHealth() {
    try { const r = await fetch("/api/health"); if (!r.ok) throw new Error(); setHealth(await r.json()); }
    catch { setHealth({ ready: false, engine: "offline", message: "Chưa kết nối backend. Chạy start-backend.ps1 rồi bấm Kiểm tra lại." }); }
  }
  useEffect(() => { void checkHealth(); }, []);
  useEffect(() => {
    if (!job || !["queued", "processing"].includes(job.status)) return;
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    async function poll() {
      try {
        const r = await fetch(`/api/scans/${job!.id}`);
        if (r.status === 404) {
          if (alive) { setJob(null); setError("Phiên đã hết hạn hoặc backend đã khởi động lại. Hãy tạo mô hình mới."); }
          return;
        }
        if (!r.ok) throw new Error("Không đọc được trạng thái scan.");
        const data: Job = await r.json();
        if (!alive) return;
        failures = 0; setJob(data);
        if (data.status === "failed") setError(data.error || "Chưa dựng được hình. Hãy thử ảnh khác.");
        if (["queued", "processing"].includes(data.status)) timer = setTimeout(poll, 1200);
      } catch {
        if (!alive) return;
        failures += 1;
        if (failures < 5) timer = setTimeout(poll, 2000);
        else { setError("Mất kết nối backend. Kết quả có thể vẫn đang xử lý; kiểm tra backend rồi bấm Kiểm tra kết quả."); }
      }
    }
    timer = setTimeout(poll, 500);
    return () => { alive = false; clearTimeout(timer); };
  }, [job?.id, job?.status, pollRetry]);

  function choose(slot: Slot, file: File | null) {
    if (file) {
      if (/\.(heic|heif)$/i.test(file.name) || /image\/(heic|heif)/i.test(file.type)) {
        setError("Ảnh HEIC (iPhone) chưa được hỗ trợ trực tiếp. Hãy đổi đuôi/xuất thành JPG hoặc vào Cài đặt > Camera > Định dạng chọn 'Tương thích nhất'.");
        return;
      }
      if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size > 10 * 1024 * 1024) {
        setError("Hãy chọn ảnh JPG, PNG hoặc WebP, tối đa 10 MB.");
        return;
      }
    }
    setError(""); (slot === "front" ? setFront : setSide)(file);
  }
  async function scan() {
    if (!front || !side || !consent) { setError("Chọn đủ hai ảnh và đồng ý xử lý ảnh trước khi tạo mô hình."); return; }
    if (Number(height) < 100 || Number(height) > 230) { setError("Chiều cao cần nằm trong khoảng 100–230 cm."); return; }
    setError(""); setSubmitting(true);
    try {
      if (job) {
        const deleted = await fetch(`/api/scans/${job.id}`, { method: "DELETE" });
        if (!deleted.ok && deleted.status !== 404) throw new Error("Chưa xóa được phiên cũ. Kiểm tra kết nối rồi thử lại.");
        setJob(null);
      }
      const body = new FormData(); body.append("front", front); body.append("side", side); body.append("height_cm", height); body.append("consent", "true");
      const r = await fetch("/api/scans", { method: "POST", body });
      const data = await r.json();
      if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Không gửi được ảnh. Hãy kiểm tra dữ liệu và thử lại.");
      setJob(data); setRotation(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Không kết nối được backend."); }
    finally { setSubmitting(false); }
  }
  async function clear() {
    setDeleting(true);
    try {
      if (job) { const r = await fetch(`/api/scans/${job.id}`, { method: "DELETE" }); if (!r.ok && r.status !== 404) throw new Error(); }
      setJob(null); setFront(null); setSide(null); setConsent(false); setError(""); setReset(n => n + 1);
    } catch { setError("Chưa xóa được dữ liệu trên backend. Hãy kiểm tra kết nối rồi thử lại."); }
    finally { setDeleting(false); }
  }

  return <>
    <header className="site-header"><a className="wordmark" href="/" aria-label="MORPH AI trang chủ">MORPH<span>AI</span><i /></a><nav aria-label="Điều hướng chính"><a href="#scan" className="active">Phòng scan</a><a href="#guide">Hướng dẫn</a></nav><span className="demo-badge">DEMO</span></header>
    <main>
      <div className="intro"><div><h1>Cơ thể bạn.<br className="mobile-break" /> Trong không gian 3D.</h1><p>Bắt đầu từ hai góc chụp. Khám phá hình thể theo một cách trực quan hơn.</p></div><ol className="steps" aria-label="Tiến trình"><li className={!busy && !complete ? "current" : "done"}><span>{complete ? <Check size={16} /> : "1"}</span>Chuẩn bị ảnh</li><li className={busy ? "current" : complete ? "done" : ""}><span>2</span>Dựng hình</li><li className={complete ? "current" : ""}><span>3</span>Khám phá</li></ol></div>
      <section id="scan" className="workspace" aria-label="Phòng scan cơ thể">
        <div className="input-panel"><h2>Bắt đầu từ ảnh của bạn</h2><p className="panel-description">Cùng một người, cùng trang phục, hai góc chụp.</p>
          <div className="photo-inputs"><PhotoInput side={false} file={front} disabled={!!busy} onFile={file => choose("front", file)} onCamera={() => setCamera("front")} /><PhotoInput side file={side} disabled={!!busy} onFile={file => choose("side", file)} onCamera={() => setCamera("side")} /></div>
          <label className="height-field" htmlFor="height"><span>Chiều cao</span><div><input id="height" type="number" inputMode="decimal" min="100" max="230" step="0.1" value={height} disabled={!!busy} onChange={e => setHeight(e.target.value)} /><span>cm</span></div></label>
          <div className="capture-tip"><Sun size={19} /><span>Mặc đồ ôm sát, đủ sáng. Thấy rõ đầu và cả hai bàn chân.</span></div>
          <label className="consent"><input type="checkbox" checked={consent} disabled={!!busy} onChange={e => setConsent(e.target.checked)} /><span>Tôi đồng ý xử lý ảnh để tạo mô hình trong demo này. <button type="button" className="inline-link" onClick={() => setPrivacy(!privacy)} aria-expanded={privacy}>Cách xử lý dữ liệu</button></span></label>
          {privacy && <div className="privacy-note"><ShieldCheck size={17} /><p>Ảnh được gửi tới backend đang cấu hình để xử lý. File upload có thể được ghi tạm xuống ổ đĩa và được đóng sau tiếp nhận; ứng dụng không lưu hồ sơ ảnh. Kết quả lưu tạm tối đa 1 giờ sau xử lý. Bấm “Xóa phiên” để xóa sớm. Ảnh không dùng để huấn luyện.</p></div>}
          <button className="primary" onClick={scan} disabled={!front || !side || !consent || !health?.ready || !!busy || deleting}>{busy ? <><LoaderCircle size={19} className="spin" />Đang dựng hình…</> : <>Tạo mô hình 3D<ArrowRight size={20} /></>}</button>
          <div className={`connection ${health?.ready ? "online" : ""}`}><span className="status-dot" /><span>{health ? health.ready ? "Backend sẵn sàng" : "Backend chưa sẵn sàng" : "Đang kết nối backend…"}</span>{!health?.ready && <button className="inline-link" onClick={checkHealth}>Kiểm tra lại</button>}</div>
          {health && !health.ready && <p className="backend-note">{health.message}</p>}
          {error && <div className="error-message" role="alert"><Info size={17} /><div>{error}{busy && <button className="inline-link" onClick={() => { setError(""); setPollRetry(n => n + 1); }}>Kiểm tra kết quả</button>}</div></div>}
        </div>
        <div className="result-panel"><div className="viewport" ref={viewport}><div className="viewer-top"><span className="model-label">{complete ? <CheckCircle2 size={15} /> : <Info size={15} />}{complete ? "Kết quả từ ảnh của bạn" : "Mô hình minh họa"}</span><div className="view-modes" aria-label="Chế độ hiển thị"><button className={!wireframe ? "selected" : ""} aria-label="Khối đặc" aria-pressed={!wireframe} onClick={() => setWireframe(false)}><Box size={16} /><span>Khối đặc</span></button><button className={wireframe ? "selected" : ""} aria-label="Khung lưới" aria-pressed={wireframe} onClick={() => setWireframe(true)}><ScanLine size={16} /><span>Khung lưới</span></button></div></div>
          <ViewerBoundary key={job?.model_url || "sample"}><BodyViewer url={complete ? job.model_url : undefined} wireframe={wireframe} reset={reset} autoRotate={rotation} targetHeightCm={Number(height) || 170} showRings={showRings} measurements={job?.measurements} /></ViewerBoundary>
          <div className="viewer-tools"><button className={`icon-button ${showRings ? "selected" : ""}`} onClick={() => setShowRings(!showRings)} title="Vòng đo 3D" aria-label="Bật tắt vòng đo 3D" aria-pressed={showRings}><Ruler size={18} /></button><button className="icon-button" onClick={() => setReset(n => n + 1)} title="Đặt lại góc nhìn" aria-label="Đặt lại góc nhìn"><RotateCcw size={18} /></button><button className={`icon-button ${rotation ? "selected" : ""}`} onClick={() => setRotation(!rotation)} title="Tự xoay" aria-label="Tự xoay mô hình" aria-pressed={rotation}><Box size={18} /></button><button className="icon-button" onClick={() => { if (document.fullscreenElement) void document.exitFullscreen(); else void viewport.current?.requestFullscreen().catch(() => setError("Trình duyệt không hỗ trợ toàn màn hình.")); }} title="Toàn màn hình" aria-label="Toàn màn hình"><Maximize size={18} /></button></div>
          {busy && <div className="processing-overlay" role="status"><div><LoaderCircle size={32} className="spin" /><h3>{job?.stage || "Đang gửi ảnh…"}</h3><p>Giữ trang này mở. Thời gian tùy ảnh và cấu hình máy.</p></div></div>}
          <div className="viewer-bottom"><span><Mouse size={16} />Kéo để xoay · Cuộn để phóng to</span><span className="estimate-note">Hình thể ước lượng</span></div>
        </div><div className="result-footer"><div><ShieldCheck size={17} /><span>Demo hình thể · Chưa được kiểm chứng để may đo</span></div>{complete && <a className="download-button" href={job.model_url} download="morph-body.glb"><Download size={16} />Tải GLB</a>}</div>
        {complete && <div className="result-notes" role="status"><strong>Đã dựng mô hình{job.elapsed_seconds ? ` trong ${job.elapsed_seconds.toFixed(1)} giây` : ""}.</strong>{job.warnings?.map((warning, i) => <p key={i}>{warning}</p>)}</div>}
        {complete && job?.measurements && Object.keys(job.measurements).length > 0 && (
          <div className="measurements-card">
            <div className="measurements-header">
              <h3><ScanLine size={16} /> Thông số hình thể ước lượng</h3>
              <span className="measurements-badge">3D Mesh Slicing</span>
            </div>
            <div className="measurements-grid">
              <div className="measure-item"><span className="measure-label">Chiều cao</span><span className="measure-value">{job.measurements.height_cm}<small>cm</small></span></div>
              <div className="measure-item"><span className="measure-label">Vòng ngực</span><span className="measure-value">{job.measurements.chest_cm}<small>cm</small></span></div>
              <div className="measure-item"><span className="measure-label">Vòng eo</span><span className="measure-value">{job.measurements.waist_cm}<small>cm</small></span></div>
              <div className="measure-item"><span className="measure-label">Vòng mông</span><span className="measure-value">{job.measurements.hip_cm}<small>cm</small></span></div>
              <div className="measure-item"><span className="measure-label">Rộng vai</span><span className="measure-value">{job.measurements.shoulder_width_cm}<small>cm</small></span></div>
              <div className="measure-item"><span className="measure-label">Dài chân (Inseam)</span><span className="measure-value">{job.measurements.inseam_cm}<small>cm</small></span></div>
            </div>
            <p className="measure-note">* Các thông số được tính toán bằng cách cắt lát hình học không gian 3D tại các cao độ giải phẫu; mang tính tham khảo trực quan, chưa qua kiểm chứng may đo.</p>

            {job?.body_profile && (
              <div className="fashion-card">
                <div className="fashion-header">
                  <div className="shape-badge">
                    <Sparkles size={14} />
                    <span>Dáng người: <strong>{job.body_profile.shape}</strong></span>
                  </div>
                  <span className="fit-badge">{job.body_profile.fit_type}</span>
                </div>
                <p className="shape-desc">{job.body_profile.shape_description}</p>
                <div className="size-recommendations">
                  <div className="size-box">
                    <span className="size-type">Size Áo đề xuất</span>
                    <span className="size-number">{job.body_profile.top_size}</span>
                    <small>Áo thun / Sơ mi</small>
                  </div>
                  <div className="size-box">
                    <span className="size-type">Size Quần đề xuất</span>
                    <span className="size-number">{job.body_profile.bottom_size}</span>
                    <small>Quần âu / Jeans</small>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        </div>
      </section>
      <div className="session-row"><span>Ảnh rõ hơn, hình thể tốt hơn.</span><button className="text-button" disabled={!!busy || deleting || (!front && !side && !job)} onClick={clear}><Trash2 size={15} />{deleting ? "Đang xóa…" : "Xóa phiên & bắt đầu lại"}</button></div>
      <section className="guide" id="guide" aria-label="Hướng dẫn chụp ảnh"><article><Camera size={27} strokeWidth={1.5} /><div><h3>1. Hai ảnh rõ toàn thân</h3><p>Chính diện với tay tách thân. Ảnh nghiêng xoay 90°, tránh tay che bụng.</p></div></article><article><Sun size={29} strokeWidth={1.5} /><div><h3>2. Điều kiện chụp đồng nhất</h3><p>Đồ ôm sát, nền đơn giản, máy đặt cố định. Không dùng ảnh gương.</p></div></article><article><Box size={29} strokeWidth={1.5} /><div><h3>3. Khám phá hình thể</h3><p>Xoay, xem khung lưới và tải mô hình. Khuôn mặt chưa được tái tạo.</p></div></article></section>
    </main><footer className="site-footer"><span className="footer-brand">MORPH AI</span><span>Một góc nhìn mới về hình thể.</span><span className="footer-right">Bản demo · Không dùng để may đo</span></footer>
    {camera && <CameraCapture side={camera === "side"} onCapture={file => choose(camera, file)} onClose={() => setCamera(null)} />}
  </>;
}
