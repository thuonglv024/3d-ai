"use client";

/**
 * Nút "Test API": kiểm tra đúng thứ đang hỏng khi quét AI.
 *
 * 1. GET /api/ai-scan/health → máy chủ có key và model nào.
 * 2. POST /api/ai-scan/analyze với hai ảnh 1x1 khác nhau → chứng minh route
 *    sống và cho biết mã trả về thật. Ảnh rỗng sẽ bị từ chối ở bước đọc ảnh
 *    (400), đó là kết quả ĐÚNG của một lần test kết nối: route trả lời, không
 *    treo, không 504. Muốn test cả model thì bấm "Quét bằng AI" như bình thường.
 */
import { useState } from "react";

type Probe = { ok: boolean; status: number; ms: number; text: string };

const PNG_A =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";
const PNG_B =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

function dataUrlToBlob(dataUrl: string): Blob {
  const [head, body] = dataUrl.split(",");
  const mime = head.slice(head.indexOf(":") + 1, head.indexOf(";"));
  const bytes = Uint8Array.from(atob(body), (char) => char.charCodeAt(0));
  return new Blob([bytes], { type: mime });
}

async function readDetail(response: Response): Promise<string> {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text);
    const detail = parsed?.detail;
    if (Array.isArray(detail)) return detail.map((item) => item?.msg ?? String(item)).join("; ");
    if (typeof detail === "string") return detail;
    return text.slice(0, 200);
  } catch {
    return text.slice(0, 200);
  }
}

export function AiApiTestButton({ onResult }: { onResult?: (probe: Probe) => void }) {
  const [probe, setProbe] = useState<Probe | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setProbe(null);
    const started = Date.now();
    try {
      const health = await fetch("/api/ai-scan/health", { cache: "no-store" });
      const healthText = await readDetail(health);
      if (!health.ok) {
        const result = { ok: false, status: health.status, ms: Date.now() - started, text: `health: ${healthText}` };
        setProbe(result);
        onResult?.(result);
        return;
      }
      const form = new FormData();
      form.append("front", dataUrlToBlob(PNG_A), "front.png");
      form.append("side", dataUrlToBlob(PNG_B), "side.png");
      form.append("height_cm", "170");
      form.append("capture_mode", "upper_body");
      form.append("consent", "true");
      const analyze = await fetch("/api/ai-scan/analyze", { method: "POST", body: form });
      const analyzeText = await readDetail(analyze);
      const result = {
        ok: analyze.status < 500,
        status: analyze.status,
        ms: Date.now() - started,
        text: `${healthText} → analyze ${analyze.status}: ${analyzeText}`,
      };
      setProbe(result);
      onResult?.(result);
    } catch (error) {
      const result = { ok: false, status: 0, ms: Date.now() - started, text: String(error) };
      setProbe(result);
      onResult?.(result);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-api-test" data-ok={probe ? String(probe.ok) : undefined}>
      <button type="button" onClick={run} disabled={busy}>
        {busy ? "Đang test API…" : "Test API AI"}
      </button>
      {busy && <small>Đang gọi health rồi thử một request analyze…</small>}
      {probe && !busy && (
        <small role="status">
          {probe.ok ? "Route AI phản hồi" : "Route AI lỗi"} · mã {probe.status} · {probe.ms} ms
          <br />
          {probe.text.slice(0, 240)}
        </small>
      )}
    </div>
  );
}
