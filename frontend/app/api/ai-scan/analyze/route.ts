/**
 * Server-side passthrough for the AI analyze call.
 *
 * The browser used to reach FastAPI through `rewrites()`. An AI scan can take
 * 20-180 s on a free-tier model, and the dev proxy drops long requests with
 * `socket hang up`, which the UI could only report as "chưa quét được". A route
 * handler owns the upstream fetch, so no proxy timeout applies and a real
 * failure keeps FastAPI's own message.
 *
 * Filesystem routes win over `rewrites()` for the same path, so this only
 * replaces `/api/ai-scan/analyze`; the rest of `/api` stays proxied.
 */
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

const BACKEND = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const started = Date.now();
  const contentType = request.headers.get("content-type") || "";
  const body = await request.arrayBuffer();
  try {
    const upstream = await fetch(`${BACKEND}/api/ai-scan/analyze`, {
      method: "POST",
      headers: { "content-type": contentType },
      body,
      cache: "no-store",
    });
    const text = await upstream.text();
    console.log("[ai-proxy] analyze", upstream.status, `${Date.now() - started}ms`, `${body.byteLength}B`);
    return new Response(text, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") || "application/json", "cache-control": "no-store" },
    });
  } catch (error) {
    console.error("[ai-proxy] analyze failed", `${Date.now() - started}ms`, String(error));
    return Response.json(
      { detail: "Không kết nối được backend để phân tích AI. Kiểm tra backend đang chạy rồi thử lại." },
      { status: 502 }
    );
  }
}
