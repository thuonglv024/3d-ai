"""Thí nghiệm A–E: v1 (1 lượt gọi) so với v2 (3 lượt + hình học), trên cùng ảnh + tape.

Mục tiêu: giải thích vì sao v1 ra số sát hơn, và tách xem phần nào của v2 gây lệch
(head-unit, ép trả width/depth, fusion hình học, ensemble 3 role).

Chạy:
    backend/.venv/Scripts/python.exe scripts/eval/ab_ai_v1_v2.py

Kết quả ghi ra output/measure-debug/ab_v1_v2.json (output/ đã gitignore).
Ảnh P01b là người thật: chỉ gửi tới Gemini để đo, không lưu ở đâu khác.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import statistics
import sys
import time
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402
from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: E402

from app.ai_scan import prompts as v2_prompts  # noqa: E402
from app.ai_scan import service as v2_service  # noqa: E402
from app.ai_scan.config import configured_model, google_api_key, is_configured  # noqa: E402
from app.ai_scan.geometry import run_geometric_estimate  # noqa: E402
from app.ai_scan.schemas import VisionMeasurementEstimate  # noqa: E402

PILOT = ROOT / "backend" / "data" / "pilot_selfie"
OUT = ROOT / "output" / "measure-debug"
SYNTHETIC = ROOT / "verification" / "scripts" / "qa"

# Tape P01b (ground_truth.json): ngực 80, eo 60, hông 92; cao 156.
CASES = [
    {
        "name": "P01b (người thật)",
        "front": PILOT / "P01b_front.png",
        "side": PILOT / "P01b_second.png",
        "height_cm": 156.0,
        "capture_mode": "full_body",
        "tape": {"chest_cm": 80.0, "waist_cm": 60.0, "hip_cm": 92.0},
    },
    {
        "name": "mannequin (tổng hợp)",
        "front": SYNTHETIC / "upper-front.png",
        "side": SYNTHETIC / "upper-side.png",
        "height_cm": 170.0,
        "capture_mode": "upper_body",
        "tape": {},
    },
]

# --- v1 (chép nguyên văn từ commit d3399b9) --------------------------------

V1_SYSTEM = """You are an experimental body-measurement estimator inside a fitting-room prototype.

You will receive two photos of the same consenting adult: a frontal view and a
90-degree side view. The person's self-reported height is a scale hint, not a
measurement to repeat back.

Estimate only these body dimensions in centimetres:
- chest/bust circumference
- natural waist circumference
- hip circumference
- biacromial shoulder width

Rules:
1. Do not identify the person. Do not infer ethnicity, health, age, gender identity,
   or any other sensitive attribute.
2. Use visible anatomical landmarks (shoulders, armpits, waist crease, hip
   prominence) and the height hint to calibrate scale.
3. Loose clothing, heavy occlusion, blur, poor lighting, cropped body regions and
   strong camera angles make estimates unreliable. Say so via confidence,
   pose_quality and image_quality.
4. If a body region is not visible, or you cannot support a number, return null for
   that measurement. A null is always better than an invented value.
5. In upper_body mode, do not estimate hip circumference; return null for hip_cm.
6. Never claim clinical, medical or certified anthropometric accuracy. This is a
   visual estimate.
7. Return only the structured schema requested by the caller.

Measurement convention:
- chest: widest circumference around the chest.
- waist: narrowest circumference around the natural waist, not the trouser waistband.
- hip: widest circumference around the buttocks.
- shoulder width: straight-line distance between the acromion points.
"""


def v1_user_prompt(height_cm: float, capture_mode: str) -> str:
    mode_note = (
        "upper_body: estimate chest, waist and shoulder width; hip must be null."
        if capture_mode == "upper_body"
        else "full_body: estimate chest, waist, hip and shoulder width."
    )
    return (
        f"Self-reported height: {height_cm:.1f} cm.\n"
        f"Capture mode: {capture_mode} ({mode_note})\n\n"
        "Image 1 is the frontal view. Image 2 is the 90-degree side view. "
        "Estimate each dimension and return the structured result."
    )


class V1Estimate(BaseModel):
    """Schema tối giản: chỉ 4 vòng + độ tin cậy, không width/depth, không head."""

    chest_cm: float | None = None
    waist_cm: float | None = None
    hip_cm: float | None = None
    shoulder_width_cm: float | None = None
    confidence: float = 0.0
    pose_quality: str = "fair"
    image_quality: str = ""
    notes: str = ""


def data_url(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def model(temperature: float) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=configured_model(), api_key=google_api_key(), temperature=temperature, max_retries=1
    )


async def one_call(system: str, user: str, schema, case: dict, temperature: float = 0.0) -> dict:
    structured = model(temperature).with_structured_output(schema)
    messages = [
        SystemMessage(content=system),
        HumanMessage(
            content=[
                {"type": "text", "text": user},
                {"type": "text", "text": "Front view:"},
                {"type": "image_url", "image_url": {"url": data_url(case["front"])}},
                {"type": "text", "text": "Side view (90 degrees):"},
                {"type": "image_url", "image_url": {"url": data_url(case["side"])}},
            ]
        ),
    ]
    started = time.time()
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            result = await asyncio.wait_for(structured.ainvoke(messages), timeout=150)
            break
        except Exception as exc:  # noqa: BLE001 - 503/429/timeout cần thử lại
            last_error = exc
            message = str(exc)
            retryable = (
                "503" in message or "429" in message or "UNAVAILABLE" in message or "TimeoutError" in message
            )
            print(f"   [{schema.__name__}] lần {attempt + 1} lỗi: {message[:90]}", flush=True)
            if attempt == 2 or not retryable:
                raise
            await asyncio.sleep(3 * (attempt + 1))
    else:  # pragma: no cover - vòng lặp luôn break hoặc raise
        raise last_error if last_error else RuntimeError("không gọi được model")
    print(f"   [{schema.__name__}] xong sau {round(time.time() - started, 1)}s", flush=True)
    if isinstance(result, dict):
        payload = dict(result)
    else:
        payload = result.model_dump()
    payload["_elapsed_s"] = round(time.time() - started, 1)
    return payload


def strip_head_unit(system: str) -> str:
    start = system.find("Scale calibration procedure (do this before answering):")
    if start < 0:
        raise SystemExit("Không tìm thấy khối head-unit để bỏ")
    end = system.find("Clothing rule:", start)
    if end < 0:
        raise SystemExit("Không tìm thấy mốc kết thúc khối head-unit")
    return system[:start] + system[end:]


def strip_width_depth(system: str) -> str:
    lines = [
        line
        for line in system.splitlines()
        if "chest width (side-to-side)" not in line
        and "waist width and waist depth" not in line
        and "hip width and hip depth" not in line
        and "Breadth means the frontal width" not in line
        and "depth means the front-to-back" not in line
        and "- width/depth: measured at the same level" not in line
    ]
    return "\n".join(lines)


def metrics_of(payload: dict, keys=("chest_cm", "waist_cm", "hip_cm")) -> dict:
    return {key: payload.get(key) for key in keys}


async def run_case(case: dict, *, repeats: bool = True, nongeo: bool = True) -> dict:
    tape = case["tape"]
    height = case["height_cm"]
    mode = case["capture_mode"]
    report: dict = {"case": case["name"], "height_cm": height, "tape": tape, "configs": {}}

    # A: v1 một lượt, temp 0
    report["configs"]["A_v1_single"] = await one_call(
        V1_SYSTEM, v1_user_prompt(height, mode), V1Estimate, case, 0.0
    )

    # A3: v1 × 3, temp 0.3 → trung vị + độ tán
    if repeats:
        runs = [await one_call(V1_SYSTEM, v1_user_prompt(height, mode), V1Estimate, case, 0.3) for _ in range(3)]
        report["configs"]["A3_v1_threeruns"] = {"runs": runs, "median": {}, "spread": {}}
        for key in ("chest_cm", "waist_cm", "hip_cm"):
            values = [r[key] for r in runs if r.get(key) is not None]
            if values:
                report["configs"]["A3_v1_threeruns"]["median"][key] = round(statistics.median(values), 1)
                report["configs"]["A3_v1_threeruns"]["spread"][key] = round(max(values) - min(values), 1)

    # C0: v2 prompt đầy đủ, MỘT lượt, temp 0 (giữ head-unit) → xem head_length
    v2_user = v2_prompts.build_user_prompt(height, mode, "auto", None)
    report["configs"]["C0_v2_single_with_head"] = await one_call(
        v2_prompts.SYSTEM_PROMPT, v2_user, VisionMeasurementEstimate, case, 0.0
    )

    # C1: bỏ head-unit
    report["configs"]["C1_v2_no_head_unit"] = await one_call(
        strip_head_unit(v2_prompts.SYSTEM_PROMPT), v2_user, VisionMeasurementEstimate, case, 0.0
    )

    # C2: bỏ yêu cầu width/depth (schema tối giản)
    report["configs"]["C2_v2_no_width_depth"] = await one_call(
        strip_width_depth(v2_prompts.SYSTEM_PROMPT), v2_user, V1Estimate, case, 0.0
    )

    # Geometry thô trên cùng ảnh
    geo = await asyncio.to_thread(
        run_geometric_estimate,
        case["front"].read_bytes(),
        case["side"].read_bytes(),
        height,
        mode,
        None,
    )
    report["geometry"] = {k: geo.get(k) for k in ("available", "reason", "measurements", "warnings")}

    # C-service: pipeline v2 đầy đủ (3 role + fusion + prior guard)
    os.environ.pop("MORPH_AI_GEOMETRY_CHECK", None)
    report["configs"]["C_v2_service_full"] = await v2_service.run_ai_scan(
        case["front"].read_bytes(), case["side"].read_bytes(), height, mode, "image/png", "image/png", "auto"
    )

    # C-nogeo: tắt fusion hình học
    if nongeo:
        os.environ["MORPH_AI_GEOMETRY_CHECK"] = "0"
        try:
            report["configs"]["C_v2_service_nogeo"] = await v2_service.run_ai_scan(
                case["front"].read_bytes(), case["side"].read_bytes(), height, mode, "image/png", "image/png", "auto"
            )
        finally:
            os.environ.pop("MORPH_AI_GEOMETRY_CHECK", None)

    # Bảng sai số
    table = []
    configs = report["configs"]
    rows = {
        "A_v1_single": metrics_of(configs.get("A_v1_single", {})),
        "C0_v2_single_with_head": metrics_of(configs.get("C0_v2_single_with_head", {})),
        "C1_v2_no_head_unit": metrics_of(configs.get("C1_v2_no_head_unit", {})),
        "C2_v2_no_width_depth": metrics_of(configs.get("C2_v2_no_width_depth", {})),
        "C_v2_service_full": metrics_of((configs.get("C_v2_service_full") or {}).get("measurements", {})),
        "C_v2_service_nogeo": metrics_of((configs.get("C_v2_service_nogeo") or {}).get("measurements", {})),
        "geometry": metrics_of((report.get("geometry") or {}).get("measurements", {})),
    }
    if "A3_v1_threeruns" in configs:
        rows["A3_v1_median"] = configs["A3_v1_threeruns"]["median"]
    for name, values in rows.items():
        row = {"config": name}
        for key, value in values.items():
            row[key] = value
            if key in tape and value is not None:
                row[f"{key}_err"] = round(float(value) - tape[key], 1)
        table.append(row)
    report["table"] = table
    return report


async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="all", choices=["all", "p01", "mannequin"])
    parser.add_argument("--repeats", action="store_true", help="chạy thêm A3 (3 lượt, temp 0.3)")
    parser.add_argument("--nogeo", action="store_true", help="chạy thêm C tắt fusion hình học")
    args = parser.parse_args()

    if not is_configured():
        print("GOOGLE_API_KEY chưa cấu hình — không chạy được thí nghiệm.")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    selected = {
        "p01": [CASES[0]],
        "mannequin": [CASES[1]],
        "all": CASES,
    }[args.case]
    results = []
    for case in selected:
        if not case["front"].is_file() or not case["side"].is_file():
            print(f"thiếu ảnh cho {case['name']}: {case['front']} / {case['side']}")
            continue
        print(f"== {case['name']} (cao {case['height_cm']} cm, tape {case['tape']}) ==")
        results.append(await run_case(case, repeats=args.repeats, nongeo=args.nogeo))

    payload = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": results}
    (OUT / "ab_v1_v2.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for result in results:
        print(f"\n### {result['case']} — tape {result['tape']}")
        header = f"{'config':26s} {'chest':>7s} {'err':>6s} {'waist':>7s} {'err':>6s} {'hip':>7s} {'err':>6s}"
        print(header)
        for row in result["table"]:
            def fmt(key, err_key):
                value = row.get(key)
                err = row.get(err_key)
                v = f"{value:7.1f}" if isinstance(value, (int, float)) else f"{'—':>7s}"
                e = f"{err:+6.1f}" if isinstance(err, (int, float)) else f"{'':>6s}"
                return v, e
            c_v, c_e = fmt("chest_cm", "chest_cm_err")
            w_v, w_e = fmt("waist_cm", "waist_cm_err")
            h_v, h_e = fmt("hip_cm", "hip_cm_err")
            print(f"{row['config']:26s} {c_v} {c_e} {w_v} {w_e} {h_v} {h_e}")
        head = result["configs"]["C0_v2_single_with_head"].get("head_length_cm")
        print(f"head_length_cm (v2, người thật): {head}")
        print(f"geometry: {result['geometry'].get('measurements')}")
    print(f"\nJSON: {OUT / 'ab_v1_v2.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
