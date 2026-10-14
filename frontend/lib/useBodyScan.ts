"use client";
import {useState,useEffect,useRef} from "react";
type Health = { ready: boolean; engine: string; message: string };
type Measurements = { height_cm?: number; chest_cm?: number; waist_cm?: number; hip_cm?: number; shoulder_width_cm?: number; inseam_cm?: number | null };
export type MeasurementDetail = {key:string;label:string;value_cm:number|null;source:"user_input"|"photo_estimate"|"photo_with_prior"|"template_model"|"unavailable";color:string;points_m:[number,number,number][]};
type BodyProfile = { capture_mode?:string; measurement_details?:MeasurementDetail[]; fit_status?: string; max_fit_error_cm?: number; note?: string; sections?: {key:string;label:string;target_cm:number;model_cm:number;fit_error_cm:number;points_m:[number,number,number][]}[] };
export type Job = { id: string; status: "queued" | "processing" | "completed" | "failed"; stage: string; error?: string; model_url?: string; warnings?: string[]; measurements?: Measurements; body_profile?: BodyProfile; elapsed_seconds?: number; guest_token?: string; user_id?: string | null };
type Slot = "front" | "side";

export function useBodyScan(initialJob?: Job | null, initialMode: "upper_body" | "full_body" = "upper_body") {
  const [captureMode,setCaptureMode]=useState<"upper_body"|"full_body">(initialMode);
  const [front, setFront] = useState<File | null>(null);
  const [side, setSide] = useState<File | null>(null);
  const [height, setHeight] = useState("170");
  const [consent, setConsent] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");
  const [job, setJob] = useState<Job | null>(initialJob || null);
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

  function getGuestHeaders(targetJob: Job): Record<string, string> {
    let token = targetJob.guest_token || "";
    if (!token && typeof window !== "undefined") {
      try {
        token = sessionStorage.getItem(`morph_scan_guest_token_${targetJob.id}`) || "";
      } catch {}
    }
    return token ? { "X-Guest-Token": token } : {};
  }

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
        const r = await fetch(`/api/scans/${job!.id}`, {
          headers: getGuestHeaders(job!),
          credentials: "include",
        });
        if (r.status === 404) {
          if (alive) { setJob(null); setError("Phiên đã hết hạn hoặc máy chủ đã khởi động lại. Vui lòng quét lại."); }
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
        setError("Ảnh HEIC (iPhone) chưa được hỗ trợ trực tiếp. Hãy xuất/chuyển đổi thành JPG hoặc vào Cài đặt > Camera > Định dạng chọn 'Tương thích nhất'.");
        return;
      }
      if (!/^image\/(jpeg|png|webp)$/.test(file.type) || file.size > 10 * 1024 * 1024) {
        setError("Hãy chọn ảnh JPG, PNG hoặc WebP, tối đa 10 MB.");
        return;
      }
    }
    setError(""); (slot === "front" ? setFront : setSide)(file);
  }
  async function scan(captured?: {front:File;side:File}) {
    const frontPhoto=captured?.front||front,sidePhoto=captured?.side||side;
    if (!frontPhoto || !sidePhoto || !consent) { setError("Chụp đủ hai góc và đồng ý xử lý ảnh trước khi tạo mô hình."); return; }
    if (!Number.isFinite(Number(height)) || Number(height) < 100 || Number(height) > 230) { setError("Chiều cao cần nằm trong khoảng 100–230 cm."); return; }
    setError(""); setSubmitting(true);
    try {
      if (job) {
        const deleted = await fetch(`/api/scans/${job.id}`, {
          method: "DELETE",
          headers: getGuestHeaders(job),
          credentials: "include",
        });
        if (!deleted.ok && deleted.status !== 404) throw new Error("Chưa xóa được phiên cũ. Kiểm tra kết nối rồi thử lại.");
        setJob(null);
      }
      const body = new FormData(); body.append("front", frontPhoto); body.append("side", sidePhoto); body.append("height_cm", height); body.append("consent", "true");
      body.append("capture_mode",captureMode);
      const r = await fetch("/api/scans", { method: "POST", body, credentials: "include" });
      const data = await r.json();
      if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Không gửi được ảnh. Hãy kiểm tra dữ liệu và thử lại.");
      if (typeof window !== "undefined" && data?.id && data?.guest_token) {
        try {
          sessionStorage.setItem(`morph_scan_guest_token_${data.id}`, data.guest_token);
        } catch {}
      }
      setJob(data); setRotation(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Không kết nối được backend."); }
    finally { setSubmitting(false); }
  }
  async function clear() {
    setDeleting(true);
    try {
      if (job) {
        const r = await fetch(`/api/scans/${job.id}`, {
          method: "DELETE",
          headers: getGuestHeaders(job),
          credentials: "include",
        });
        if (!r.ok && r.status !== 404) throw new Error();
      }
      setJob(null); setFront(null); setSide(null); setConsent(false); setError(""); setReset(n => n + 1);
    } catch { setError("Chưa xóa được dữ liệu trên backend. Hãy kiểm tra kết nối rồi thử lại."); }
    finally { setDeleting(false); }
  }

  return {captureMode,setCaptureMode,front,side,height,setHeight,consent,setConsent,health,error,setError,job,setJob,camera,setCamera,wireframe,setWireframe,rotation,setRotation,showRings,setShowRings,reset,setReset,privacy,setPrivacy,deleting,setPollRetry,viewport,busy,complete,choose,scan,clear,checkHealth};
}
