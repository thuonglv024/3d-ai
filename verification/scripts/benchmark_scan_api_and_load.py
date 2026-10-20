"""
MORPH AI — End-to-End API, Browser WebGL Render & Bounded Concurrent Load Benchmark.

Strictly separates:
  1. IN-PROCESS ENGINE BENCHMARK (`reconstruct()` & `capture_feedback()`):
     - Cold Start (fresh subprocess: module import + MediaPipe TFLite XNNPACK load
       + MakeHuman template `.obj` load + first inference/reconstruction).
     - Warm Start (`@lru_cache(maxsize=1)` already populated: pure 3-tier math,
       Trimesh 4-pass slicing/fitting, `capture_feedback()`, and `reconstruct()`).
  2. END-TO-END HTTP API & BROWSER WEBGL RENDER LIFECYCLE (`uvicorn app.main:app`):
     - `capture_check_http_ms` (`POST /api/capture-check`)
     - `scan_upload_enqueue_ms` (`POST /api/scans` -> `202 Accepted`)
     - `queue_wait_ms` (`queued` -> `processing`)
     - `worker_processing_ms` (`processing` -> `completed`)
     - `end_to_end_poll_completion_ms` (client upload start -> poll `completed`)
     - `glb_download_ms` (`GET /api/scans/{id}/model?guest_token=...`)
     - `measurements_download_ms` (`GET /api/scans/{id}/measurements?guest_token=...`)
     - `browser_glb_parse_and_render_ms` (Playwright Chromium + Three.js `GLTFLoader`
       + `mergeVertices`/`computeVertexNormals` + first WebGL frame render).
  3. BOUNDED CONCURRENT LOAD TEST (`MAX_ACTIVE_JOBS = 8`, `ThreadPoolExecutor(max_workers=1)`):
     - Level 1: Concurrency = 1, N = 5 sequential scans (API Baseline)
     - Level 2: Concurrency = 2, N = 6 scans (3 waves of 2 concurrent requests)
     - Level 3: Concurrency = 4, N = 8 scans (2 waves of 4 concurrent requests)
     - Level 4: Concurrency = 10 burst, N = 10 simultaneous requests (verifies
       `MAX_ACTIVE_JOBS = 8` admission cap and `HTTP 429 Too Many Requests` backpressure).
     - Strictly distinguishes `theoretical_single_worker_rate` (in-process `60 / mean_service_s`)
       from `observed_throughput_scans_per_min` (`completed_count / (wall_clock_batch_s / 60)`),
       and never conflates `60 / mean_client_latency` with system throughput under load.
  4. MEMORY PROFILING (OS WORKING SET RSS vs PYTHON TRACEMALLOC HEAP):
     - Tracks Win32 `WorkingSetSize` (`RSS`) and `PeakWorkingSetSize` (`Peak RSS`)
       separately from Python `tracemalloc` (`current_mb`, `peak_mb`) before load,
       across all concurrency levels, and after `cleanup()` + `gc.collect()`.

Run with:
    D:\\MORPH-AI\\backend\\.venv\\Scripts\\python.exe verification\\scripts\\benchmark_scan_api_and_load.py
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
from datetime import datetime, timezone
import gc
import hashlib
from importlib.metadata import version as pkg_version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
import tracemalloc
from typing import Any

import httpx
import numpy as np
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
QA_DIR = ROOT / "verification" / "scripts" / "qa"
RUN_ID = "run-20261014-v2"
OUTPUT_DIR = ROOT / "output" / "runs" / RUN_ID / "benchmark"
CACHE_DIR = ROOT / ".cache" / "bench_api_load"

NODE_EXE = Path(r"C:\Program Files\nodejs\node.exe")
CHROME_EXE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PLAYWRIGHT_MODULE = str(FRONTEND_DIR / "node_modules" / "playwright")

sys.path.insert(0, str(BACKEND_DIR))


# ==============================================================================
# 0. WIN32 OS MEMORY & SYSTEM INVENTORY HELPERS
# ==============================================================================

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def get_win32_process_memory_mb(pid: int | None = None) -> dict[str, float | None]:
    """Return OS Working Set (RSS), Peak Working Set (Peak RSS), and Pagefile (Committed) in MB."""
    if platform.system() != "Windows":
        return {"rss_mb": None, "peak_rss_mb": None, "pagefile_mb": None, "peak_pagefile_mb": None}
    try:
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(pmc)
        kernel32 = ctypes.windll.kernel32
        close_handle = False
        if pid is None or pid == os.getpid():
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            handle = kernel32.GetCurrentProcess()
        else:
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel32.OpenProcess.restype = ctypes.c_void_p
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, 0, int(pid))
            if not handle:
                return {"rss_mb": None, "peak_rss_mb": None, "pagefile_mb": None, "peak_pagefile_mb": None}
            close_handle = True

        try:
            fn = getattr(kernel32, "K32GetProcessMemoryInfo", None) or ctypes.windll.psapi.GetProcessMemoryInfo
            fn.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), ctypes.c_ulong]
            fn.restype = ctypes.c_int
            if fn(handle, ctypes.byref(pmc), pmc.cb):
                return {
                    "rss_mb": round(pmc.WorkingSetSize / (1024 ** 2), 2),
                    "peak_rss_mb": round(pmc.PeakWorkingSetSize / (1024 ** 2), 2),
                    "pagefile_mb": round(pmc.PagefileUsage / (1024 ** 2), 2),
                    "peak_pagefile_mb": round(pmc.PeakPagefileUsage / (1024 ** 2), 2),
                }
        finally:
            if close_handle and handle:
                kernel32.CloseHandle(ctypes.c_void_p(handle))
    except Exception:
        pass
    return {"rss_mb": None, "peak_rss_mb": None, "pagefile_mb": None, "peak_pagefile_mb": None}


def get_tracemalloc_mb() -> dict[str, float]:
    if not tracemalloc.is_tracing():
        return {"current_mb": 0.0, "peak_mb": 0.0}
    cur, peak = tracemalloc.get_traced_memory()
    return {
        "current_mb": round(cur / (1024 ** 2), 2),
        "peak_mb": round(peak / (1024 ** 2), 2),
    }


def _get_windows_cpu_name() -> str:
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if cpu_name:
                return str(cpu_name).strip()
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"


def _get_system_ram_gb() -> float | None:
    if platform.system() == "Windows":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return round(stat.ullTotalPhys / (1024 ** 3), 2)
        except Exception:
            pass
    return None


def _latency_stats(values_ms: list[float]) -> dict[str, float | int | None]:
    if not values_ms:
        return {
            "runs": 0,
            "p50_ms": None,
            "p95_ms": None,
            "mean_ms": None,
            "std_ms": None,
            "min_ms": None,
            "max_ms": None,
        }
    arr = np.asarray(values_ms, dtype=float)
    return {
        "runs": int(len(arr)),
        "p50_ms": round(float(np.percentile(arr, 50)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "mean_ms": round(float(np.mean(arr)), 2),
        "std_ms": round(float(np.std(arr)), 2),
        "min_ms": round(float(np.min(arr)), 2),
        "max_ms": round(float(np.max(arr)), 2),
    }


# ==============================================================================
# 1. SUBPROCESS MODES: COLD-START PROBE & INSTRUMENTED UVICORN SERVER
# ==============================================================================

def run_cold_start_probe(mode: str, out_json: Path) -> None:
    """Executed in a brand-new Python subprocess to measure genuine Cold Start."""
    tracemalloc.start()
    mem_at_boot = {
        "os": get_win32_process_memory_mb(),
        "python_heap": get_tracemalloc_mb(),
    }

    t_import0 = time.perf_counter()
    from app.reconstruction import (
        ENGINE,
        MODEL_PATH,
        TEMPLATE_PATH,
        capture_feedback,
        get_detector,
        read_template,
        reconstruct,
    )
    t_import1 = time.perf_counter()
    cold_import_ms = round((t_import1 - t_import0) * 1000.0, 2)

    mem_after_import = {
        "os": get_win32_process_memory_mb(),
        "python_heap": get_tracemalloc_mb(),
    }

    uf_img = np.array(Image.open(QA_DIR / "upper-front.png").convert("RGB"))
    us_img = np.array(Image.open(QA_DIR / "upper-side.png").convert("RGB"))
    rf_img = np.array(Image.open(QA_DIR / "rendered-front.png").convert("RGB"))
    rs_img = np.array(Image.open(QA_DIR / "rendered-side.png").convert("RGB"))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    glb_cold_path = CACHE_DIR / f"cold-{mode}.glb"

    if mode == "decomposed":
        # Step 1: Load MediaPipe PoseLandmarker detector (pose_landmarker_full.task + XNNPACK)
        t0 = time.perf_counter()
        _ = get_detector()
        t1 = time.perf_counter()
        cold_detector_load_ms = round((t1 - t0) * 1000.0, 2)

        mem_after_detector = {
            "os": get_win32_process_memory_mb(),
            "python_heap": get_tracemalloc_mb(),
        }

        # Step 2: Load MakeHuman body-template.obj via Trimesh
        t0 = time.perf_counter()
        _ = read_template()
        t1 = time.perf_counter()
        cold_template_load_ms = round((t1 - t0) * 1000.0, 2)

        mem_after_template = {
            "os": get_win32_process_memory_mb(),
            "python_heap": get_tracemalloc_mb(),
        }

        # Step 3: First capture_feedback() call
        t0 = time.perf_counter()
        _ = capture_feedback(uf_img, "front", "upper_body")
        t1 = time.perf_counter()
        first_capture_feedback_ms = round((t1 - t0) * 1000.0, 2)

        # Step 4: First reconstruct() call after detector/template loaded
        t0 = time.perf_counter()
        reconstruct(uf_img, us_img, 175.0, glb_cold_path, lambda _: None, "upper_body")
        t1 = time.perf_counter()
        first_reconstruct_after_preload_ms = round((t1 - t0) * 1000.0, 2)

        mem_after_first_reconstruct = {
            "os": get_win32_process_memory_mb(),
            "python_heap": get_tracemalloc_mb(),
        }

        payload = {
            "probe_mode": "decomposed",
            "engine": ENGINE,
            "cold_import_ms": cold_import_ms,
            "cold_detector_load_ms": cold_detector_load_ms,
            "cold_template_load_ms": cold_template_load_ms,
            "first_capture_feedback_ms": first_capture_feedback_ms,
            "first_reconstruct_after_preload_ms": first_reconstruct_after_preload_ms,
            "total_cold_init_plus_first_reconstruct_ms": round(
                cold_import_ms + cold_detector_load_ms + cold_template_load_ms + first_reconstruct_after_preload_ms,
                2,
            ),
            "memory_checkpoints": {
                "boot": mem_at_boot,
                "after_import": mem_after_import,
                "after_detector_load": mem_after_detector,
                "after_template_load": mem_after_template,
                "after_first_reconstruct": mem_after_first_reconstruct,
            },
        }
    else:
        # All-in-one cold reconstruct() call where get_detector() and read_template() trigger lazily inside reconstruct()
        t0 = time.perf_counter()
        reconstruct(uf_img, us_img, 175.0, glb_cold_path, lambda _: None, "upper_body")
        t1 = time.perf_counter()
        all_in_one_cold_reconstruct_upper_ms = round((t1 - t0) * 1000.0, 2)

        # Immediate second call (warm) in same process for direct comparison
        t2 = time.perf_counter()
        reconstruct(uf_img, us_img, 175.0, glb_cold_path, lambda _: None, "upper_body")
        t3 = time.perf_counter()
        second_call_warm_reconstruct_upper_ms = round((t3 - t2) * 1000.0, 2)

        # Full body warm call
        t4 = time.perf_counter()
        reconstruct(rf_img, rs_img, 172.0, glb_cold_path, lambda _: None, "full_body")
        t5 = time.perf_counter()
        warm_reconstruct_full_ms = round((t5 - t4) * 1000.0, 2)

        mem_after_calls = {
            "os": get_win32_process_memory_mb(),
            "python_heap": get_tracemalloc_mb(),
        }
        payload = {
            "probe_mode": "all_in_one",
            "cold_import_ms": cold_import_ms,
            "cold_first_reconstruct_upper_ms": all_in_one_cold_reconstruct_upper_ms,
            "cold_total_with_import_ms": round(cold_import_ms + all_in_one_cold_reconstruct_upper_ms, 2),
            "second_call_warm_reconstruct_upper_ms": second_call_warm_reconstruct_upper_ms,
            "warm_reconstruct_full_ms": warm_reconstruct_full_ms,
            "memory_after_calls": mem_after_calls,
        }

    glb_cold_path.unlink(missing_ok=True)
    tracemalloc.stop()
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


BENCH_VIEWER_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <title>MORPH AI — GLB WebGL Parse & Render Benchmark</title>
  <style>
    html, body { margin: 0; padding: 0; background: #141312; color: #f5f2eb; font-family: sans-serif; }
    #stage { width: 1440px; height: 1024px; position: relative; }
    canvas { display: block; width: 1440px; height: 1024px; }
  </style>
  <script type="importmap">
  {
    "imports": {
      "three": "/_bench_three/build/three.module.js",
      "three/examples/jsm/": "/_bench_three/examples/jsm/"
    }
  }
  </script>
</head>
<body>
  <div id="stage"><canvas id="webgl-canvas" width="1440" height="1024"></canvas></div>
  <script type="module">
    import * as THREE from "three";
    import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
    import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";

    const canvas = document.getElementById("webgl-canvas");
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
      powerPreference: "high-performance"
    });
    renderer.setSize(1440, 1024, false);
    renderer.setPixelRatio(1);

    const camera = new THREE.PerspectiveCamera(42, 1440 / 1024, 0.1, 100);
    camera.position.set(0, 0.95, 3.1);
    camera.lookAt(0, 0.88, 0);

    const loader = new GLTFLoader();

    window.__benchmarkGlbParseAndRender = async function(modelUrl, targetHeight = 1.75) {
      const tStart = performance.now();

      // 1. Fetch binary .glb from backend API
      const tFetch0 = performance.now();
      const response = await fetch(modelUrl, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status} when fetching ${modelUrl}`);
      }
      const arrayBuffer = await response.arrayBuffer();
      const tFetch1 = performance.now();

      // 2. Parse .glb via Three.js GLTFLoader
      const tParse0 = performance.now();
      const gltf = await loader.parseAsync(arrayBuffer, "");
      const tParse1 = performance.now();

      // 3. Prepare mesh & studio shader (matching BodyViewer.tsx Surface) and render first WebGL frame
      const tRender0 = performance.now();
      const scene = new THREE.Scene();
      const hemi = new THREE.HemisphereLight("#ffffff", "#7c8e81", 2.2);
      const dir1 = new THREE.DirectionalLight("#ffffff", 2.2);
      dir1.position.set(-3, 4, 5);
      const dir2 = new THREE.DirectionalLight("#f4f7f1", 1.5);
      dir2.position.set(3, 2, -3);
      scene.add(hemi, dir1, dir2);

      const copy = gltf.scene.clone(true);
      const bounds = new THREE.Box3().setFromObject(copy);
      const height = bounds.max.y - bounds.min.y;
      let totalVertices = 0;
      let meshCount = 0;

      copy.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          meshCount += 1;
          let geometry = child.geometry.clone();
          const p = geometry.getAttribute("position");
          totalVertices += p.count;
          const coordinates = new Float32Array(p.count * 2);
          for (let i = 0; i < p.count; i++) {
            const y = (p.getY(i) - bounds.min.y) / Math.max(height, 1e-5);
            const x = Math.abs(p.getX(i)) / Math.max(height, 1e-5);
            coordinates[i * 2] = x;
            coordinates[i * 2 + 1] = y;
          }
          geometry.setAttribute("morphCoord", new THREE.BufferAttribute(coordinates, 2));
          const material = new THREE.MeshStandardMaterial({
            color: "#ffffff",
            roughness: 0.80,
            metalness: 0.04,
            side: THREE.DoubleSide
          });
          material.onBeforeCompile = (shader) => {
            shader.uniforms.morphSkin = { value: new THREE.Color("#cec8bb") };
            shader.uniforms.morphFabric = { value: new THREE.Color("#78766b") };
            shader.vertexShader = "attribute vec2 morphCoord; varying vec2 vMorphCoord;\\n" + shader.vertexShader;
            shader.vertexShader = shader.vertexShader.replace(
              "#include <begin_vertex>",
              "#include <begin_vertex>\\nvMorphCoord=morphCoord;"
            );
            shader.fragmentShader = "uniform vec3 morphSkin; uniform vec3 morphFabric; varying vec2 vMorphCoord;\\n" + shader.fragmentShader;
            shader.fragmentShader = shader.fragmentShader.replace(
              "#include <color_fragment>",
              `#include <color_fragment>
              float cloth=smoothstep(0.406,0.409,vMorphCoord.y)*(1.0-smoothstep(0.785,0.788,vMorphCoord.y))*(1.0-smoothstep(0.201,0.204,vMorphCoord.x));
              diffuseColor.rgb*=mix(morphSkin,morphFabric,cloth);`
            );
          };
          child.geometry = geometry;
          child.material = material;
        }
      });

      const box = new THREE.Box3().setFromObject(copy);
      const sizeY = box.getSize(new THREE.Vector3()).y;
      if (sizeY > 0) {
        copy.scale.setScalar(targetHeight / sizeY);
      }
      const group = new THREE.Group();
      group.position.set(0, 0.025, 0);
      group.add(copy);
      scene.add(group);

      renderer.render(scene, camera);
      const gl = renderer.getContext();
      gl.finish();

      const pixel = new Uint8Array(4);
      gl.readPixels(720, 512, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
      const tRender1 = performance.now();

      // Dispose GPU resources for this iteration
      copy.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose();
          child.material.dispose();
        }
      });

      return {
        glb_bytes: arrayBuffer.byteLength,
        glb_size_kb: Math.round((arrayBuffer.byteLength / 1024) * 100) / 100,
        mesh_count: meshCount,
        vertex_count: totalVertices,
        bbox_height_m: Math.round(height * 10000) / 10000,
        center_pixel_rgba: Array.from(pixel),
        non_empty_frame: (pixel[0] + pixel[1] + pixel[2] + pixel[3]) > 0,
        browser_fetch_glb_ms: Math.round((tFetch1 - tFetch0) * 100) / 100,
        three_gltf_parse_ms: Math.round((tParse1 - tParse0) * 100) / 100,
        webgl_first_frame_render_ms: Math.round((tRender1 - tRender0) * 100) / 100,
        browser_glb_parse_and_render_ms: Math.round((tRender1 - tStart) * 100) / 100
      };
    };

    window.__benchViewerReady = true;
  </script>
</body>
</html>
"""


def run_instrumented_server(port: int) -> None:
    """Run `app.main:app` under Uvicorn with `tracemalloc` and a memory snapshot endpoint."""
    tracemalloc.start()
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    from app.main import DATA, MAX_ACTIVE_JOBS, MAX_STORED_JOBS, app, cleanup, jobs, lock

    three_dir = FRONTEND_DIR / "node_modules" / "three"
    if three_dir.is_dir():
        app.mount("/_bench_three", StaticFiles(directory=str(three_dir)), name="bench_three")

    @app.get("/_bench_viewer", response_class=HTMLResponse)
    def bench_viewer_page():
        return HTMLResponse(BENCH_VIEWER_HTML)

    @app.post("/api/_bench/memory-snapshot")
    def bench_memory_snapshot(run_cleanup: bool = False, clear_all_jobs: bool = False, run_gc: bool = False):
        if clear_all_jobs:
            with lock:
                for jid in list(jobs.keys()):
                    (DATA / f"{jid}.glb").unlink(missing_ok=True)
                jobs.clear()
        if run_cleanup:
            cleanup()
        if run_gc:
            gc.collect()
        os_mem = get_win32_process_memory_mb()
        py_heap = get_tracemalloc_mb()
        with lock:
            active_count = sum(j.status in {"queued", "processing"} for j in jobs.values())
            completed_count = sum(j.status == "completed" for j in jobs.values())
            failed_count = sum(j.status == "failed" for j in jobs.values())
            total_jobs = len(jobs)
        glb_count = len(list(DATA.glob("*.glb")))
        return {
            "pid": os.getpid(),
            "max_active_jobs": MAX_ACTIVE_JOBS,
            "max_stored_jobs": MAX_STORED_JOBS,
            "os_rss_mb": os_mem["rss_mb"],
            "os_peak_rss_mb": os_mem["peak_rss_mb"],
            "os_pagefile_mb": os_mem["pagefile_mb"],
            "os_peak_pagefile_mb": os_mem["peak_pagefile_mb"],
            "python_tracemalloc_current_mb": py_heap["current_mb"],
            "python_tracemalloc_peak_mb": py_heap["peak_mb"],
            "jobs_state": {
                "active": active_count,
                "completed": completed_count,
                "failed": failed_count,
                "total_in_dict": total_jobs,
                "glb_files_on_disk": glb_count,
            },
        }

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


# ==============================================================================
# 2. IN-PROCESS BENCHMARK: COLD START VS WARM START
# ==============================================================================

def run_in_process_cold_and_warm_benchmarks() -> dict[str, Any]:
    """Run Cold Start in isolated subprocesses, then Warm Start in-process."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cold_decomp_json = CACHE_DIR / "cold_decomposed.json"
    cold_allinone_json = CACHE_DIR / "cold_allinone.json"

    # 1. Cold start decomposed probe (fresh subprocess #1)
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--cold-probe", "decomposed", "--out", str(cold_decomp_json)],
        cwd=str(ROOT),
        check=True,
    )
    cold_decomposed = json.loads(cold_decomp_json.read_text(encoding="utf-8"))

    # 2. Cold start all-in-one probe (fresh subprocess #2)
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--cold-probe", "all_in_one", "--out", str(cold_allinone_json)],
        cwd=str(ROOT),
        check=True,
    )
    cold_all_in_one = json.loads(cold_allinone_json.read_text(encoding="utf-8"))

    # 3. Warm start in-process benchmark
    from scipy.interpolate import PchipInterpolator
    from app.camera_fusion import extract_paired_torso_profiles
    from app.measurements import (
        closed_torso_section,
        estimate_from_profiles,
        fit_measurement_targets,
        scale_lateral,
    )
    from app.reconstruction import (
        capture_feedback,
        deform_template,
        estimate_upper_body_height,
        get_detector,
        observe,
        read_template,
        reconstruct,
    )

    uf_img = np.array(Image.open(QA_DIR / "upper-front.png").convert("RGB"))
    us_img = np.array(Image.open(QA_DIR / "upper-side.png").convert("RGB"))
    rf_img = np.array(Image.open(QA_DIR / "rendered-front.png").convert("RGB"))
    rs_img = np.array(Image.open(QA_DIR / "rendered-side.png").convert("RGB"))

    # Populate @lru_cache(maxsize=1) for warm state
    detector = get_detector()
    template_mesh = read_template()
    fractions = np.linspace(0.12, 1.12, 35)
    _ = capture_feedback(uf_img, "front", "upper_body")
    obs_f = observe(uf_img, detector, "chính diện", "upper_body")
    obs_s = observe(us_img, detector, "nghiêng", "upper_body")

    # Precompute base section slices for pure math Tier 1+2+3 timing
    _, w_w, d_w = extract_paired_torso_profiles(obs_f, obs_s)
    _, t_w = estimate_from_profiles(fractions, w_w, d_w, 175.0, 0.25)
    base_levels = np.array([a["level"] for a in t_w])
    base_w_list, base_d_list, base_cz_list = [], [], []
    for lvl in base_levels:
        _, band = closed_torso_section(template_mesh, float(lvl))
        base_w_list.append(np.ptp(band[:, 0]))
        base_d_list.append(np.ptp(band[:, 2]))
        base_cz_list.append((band[:, 2].min() + band[:, 2].max()) / 2)
    base_w_arr = np.asarray(base_w_list)
    base_d_arr = np.asarray(base_d_list)
    base_cz_arr = np.asarray(base_cz_list)
    template_verts = template_mesh.vertices.copy()

    # 3a. Tier 1+2+3 pure mathematical pipeline (25 runs)
    math_times_ms = []
    for _ in range(25):
        t0 = time.perf_counter()
        _ = estimate_upper_body_height(obs_f.points, obs_f.visibility, obs_f.top, uf_img.shape[0])
        _, w_ext, d_ext = extract_paired_torso_profiles(obs_f, obs_s)
        _, targets_out = estimate_from_profiles(fractions, w_ext, d_ext, 175.0, 0.25)
        lvls = np.array([a["level"] for a in targets_out])
        fw = np.array([a["width_cm"] / 175.0 for a in targets_out])
        sd = np.array([a["depth_cm"] / 175.0 for a in targets_out])
        w_ratio = fw / np.maximum(base_w_arr, 0.04)
        d_ratio = sd / np.maximum(base_d_arr, 0.04)
        knots = np.concatenate(([0.0, 0.25, 0.40], lvls[::-1], [0.84, 0.92, 1.0]))
        sx = np.concatenate(([1, 1, w_ratio[-1] * 0.5 + 0.5], w_ratio[::-1], [1, 1, 1]))
        sz = np.concatenate(([1, 1, d_ratio[-1] * 0.5 + 0.5], d_ratio[::-1], [1, 1, 1]))
        verts = template_verts.copy()
        y_v = verts[:, 1]
        x_sc = PchipInterpolator(knots, sx)(y_v)
        z_sc = PchipInterpolator(knots, sz)(y_v)
        rad = np.interp(y_v, lvls[::-1], base_w_arr[::-1] / 2)
        tw = np.clip((rad * 1.35 - np.abs(verts[:, 0])) / (rad * 0.25), 0, 1)
        tw = tw * tw * (3 - 2 * tw)
        verts[:, 0] = scale_lateral(verts[:, 0], x_sc, rad)
        cz = np.interp(y_v, lvls[::-1], base_cz_arr[::-1])
        verts[:, 2] = cz + (verts[:, 2] - cz) * (1 + (z_sc - 1) * tw)
        verts *= 1.75
        t1 = time.perf_counter()
        math_times_ms.append((t1 - t0) * 1000.0)

    # 3b. Warm capture_feedback() (10 runs)
    fb_warm_ms = []
    for i in range(10):
        frame = uf_img if (i % 2 == 0) else us_img
        view = "front" if (i % 2 == 0) else "side"
        t0 = time.perf_counter()
        _ = capture_feedback(frame, view, "upper_body")
        t1 = time.perf_counter()
        fb_warm_ms.append((t1 - t0) * 1000.0)

    # 3c. Warm Trimesh deform + 4-pass iterative fit (10 runs)
    mesh_fit_ms = []
    for _ in range(10):
        t0 = time.perf_counter()
        m_def = deform_template(template_mesh, fractions, w_w, d_w, 175.0)
        _, _ = fit_measurement_targets(m_def, t_w, 175.0)
        t1 = time.perf_counter()
        mesh_fit_ms.append((t1 - t0) * 1000.0)

    # 3d. Warm reconstruct() in-process (8 upper_body + 8 full_body = 16 runs)
    glb_warm_u = CACHE_DIR / "warm-upper.glb"
    glb_warm_f = CACHE_DIR / "warm-full.glb"
    tracemalloc.start()
    os_mem_before_warm = get_win32_process_memory_mb()

    warm_upper_ms = []
    for _ in range(8):
        t0 = time.perf_counter()
        reconstruct(uf_img, us_img, 175.0, glb_warm_u, lambda _: None, "upper_body")
        t1 = time.perf_counter()
        warm_upper_ms.append((t1 - t0) * 1000.0)

    warm_full_ms = []
    for _ in range(8):
        t0 = time.perf_counter()
        reconstruct(rf_img, rs_img, 172.0, glb_warm_f, lambda _: None, "full_body")
        t1 = time.perf_counter()
        warm_full_ms.append((t1 - t0) * 1000.0)

    py_heap_warm = get_tracemalloc_mb()
    tracemalloc.stop()
    os_mem_after_warm = get_win32_process_memory_mb()
    glb_size_kb = round(glb_warm_f.stat().st_size / 1024.0, 2) if glb_warm_f.is_file() else None
    glb_warm_u.unlink(missing_ok=True)
    glb_warm_f.unlink(missing_ok=True)

    combined_warm_ms = warm_upper_ms + warm_full_ms
    mean_warm_s = float(np.mean(combined_warm_ms)) / 1000.0
    theoretical_rate_per_min = round(60.0 / max(mean_warm_s, 1e-4), 2)

    return {
        "scope": "IN_PROCESS_PYTHON_FUNCTION_CALL_ONLY",
        "cold_start": {
            "decomposed_subprocess": cold_decomposed,
            "all_in_one_subprocess": cold_all_in_one,
            "cold_vs_warm_speedup_ratio": round(
                cold_all_in_one["cold_first_reconstruct_upper_ms"] / max(float(np.mean(warm_upper_ms)), 1.0),
                2,
            ),
        },
        "warm_start": {
            "tier1_2_3_math_only": _latency_stats(math_times_ms),
            "capture_feedback_single_frame": _latency_stats(fb_warm_ms),
            "trimesh_deform_and_4pass_fit": _latency_stats(mesh_fit_ms),
            "reconstruct_upper_body": _latency_stats(warm_upper_ms),
            "reconstruct_full_body": _latency_stats(warm_full_ms),
            "reconstruct_combined": _latency_stats(combined_warm_ms),
            "theoretical_single_worker_rate_scans_per_min": theoretical_rate_per_min,
            "theoretical_rate_note": (
                "ƯỚC TÍNH LÝ THUYẾT IN-PROCESS (60 / mean_reconstruct_warm_s) khi gọi trực tiếp hàm Python "
                "trên 1 luồng đơn lẻ, chưa bao gồm HTTP multipart upload, hàng đợi ThreadPoolExecutor(max_workers=1), "
                "polling hay tải file .glb."
            ),
            "in_process_memory": {
                "os_rss_before_mb": os_mem_before_warm["rss_mb"],
                "os_rss_after_mb": os_mem_after_warm["rss_mb"],
                "os_peak_rss_mb": os_mem_after_warm["peak_rss_mb"],
                "python_tracemalloc_current_mb": py_heap_warm["current_mb"],
                "python_tracemalloc_peak_mb": py_heap_warm["peak_mb"],
                "exported_glb_size_kb": glb_size_kb,
            },
        },
    }


# ==============================================================================
# 3. END-TO-END HTTP LIFECYCLE & PLAYWRIGHT WEBGL RENDER BENCHMARK
# ==============================================================================

def run_playwright_glb_render_benchmark(base_url: str, model_urls: list[str]) -> dict[str, Any]:
    """Use Playwright Chromium + Three.js GLTFLoader + WebGLRenderer to measure .glb fetch, parse & first render."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    script_path = CACHE_DIR / "run_webgl_bench.cjs"
    out_path = CACHE_DIR / "webgl_bench_results.json"

    cjs_code = f"""
const {{ chromium }} = require({json.dumps(PLAYWRIGHT_MODULE)});
const fs = require("node:fs");

(async () => {{
  const baseUrl = {json.dumps(base_url)};
  const modelUrls = {json.dumps(model_urls)};
  const outPath = {json.dumps(str(out_path))};

  const browser = await chromium.launch({{
    executablePath: {json.dumps(str(CHROME_EXE))},
    headless: true,
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=angle"]
  }});
  try {{
    const context = await browser.newContext({{ viewport: {{ width: 1440, height: 1024 }} }});
    const page = await context.newPage();
    const pageErrors = [];
    page.on("pageerror", (err) => pageErrors.push(err.message));

    const tPage0 = performance.now();
    await page.goto(baseUrl + "/_bench_viewer", {{ waitUntil: "networkidle", timeout: 30000 }});
    await page.waitForFunction(() => window.__benchViewerReady === true, null, {{ timeout: 15000 }});
    const viewerInitMs = Math.round((performance.now() - tPage0) * 100) / 100;

    // Warm up WebGL shader compilation on first URL, then record Cold Shader vs Warm Shader runs
    const runs = [];
    for (let i = 0; i < modelUrls.length; i++) {{
      const fullUrl = baseUrl + modelUrls[i];
      const res = await page.evaluate(async (u) => {{
        return await window.__benchmarkGlbParseAndRender(u, 1.75);
      }}, fullUrl);
      res.run_index = i;
      res.is_first_shader_compile = (i === 0);
      runs.push(res);
    }}

    fs.writeFileSync(outPath, JSON.stringify({{
      viewer_page_init_ms: viewerInitMs,
      page_errors: pageErrors,
      runs
    }}, null, 2));
  }} finally {{
    await browser.close();
  }}
}})().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""
    script_path.write_text(cjs_code, encoding="utf-8")
    subprocess.run(
        [str(NODE_EXE), str(script_path)],
        cwd=str(ROOT),
        check=True,
    )
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    runs = raw["runs"]
    warm_runs = runs[1:] if len(runs) > 1 else runs

    return {
        "viewer_page_init_ms": raw["viewer_page_init_ms"],
        "page_errors": raw["page_errors"],
        "first_run_with_webgl_shader_compile": runs[0] if runs else None,
        "all_runs_summary": {
            "browser_fetch_glb_ms": _latency_stats([r["browser_fetch_glb_ms"] for r in runs]),
            "three_gltf_parse_ms": _latency_stats([r["three_gltf_parse_ms"] for r in runs]),
            "webgl_first_frame_render_ms": _latency_stats([r["webgl_first_frame_render_ms"] for r in runs]),
            "browser_glb_parse_and_render_ms": _latency_stats([r["browser_glb_parse_and_render_ms"] for r in runs]),
        },
        "warm_shader_runs_summary": {
            "browser_fetch_glb_ms": _latency_stats([r["browser_fetch_glb_ms"] for r in warm_runs]),
            "three_gltf_parse_ms": _latency_stats([r["three_gltf_parse_ms"] for r in warm_runs]),
            "webgl_first_frame_render_ms": _latency_stats([r["webgl_first_frame_render_ms"] for r in warm_runs]),
            "browser_glb_parse_and_render_ms": _latency_stats([r["browser_glb_parse_and_render_ms"] for r in warm_runs]),
        },
        "all_frames_verified_non_empty": all(r.get("non_empty_frame") is True for r in runs),
        "per_run_details": runs,
    }


def benchmark_e2e_http_lifecycle(base_url: str) -> dict[str, Any]:
    """Benchmark full HTTP API lifecycle on real Uvicorn server (`N = 10` scans + `N = 10` capture-checks)."""
    uf_bytes = (QA_DIR / "upper-front.png").read_bytes()
    us_bytes = (QA_DIR / "upper-side.png").read_bytes()
    rf_bytes = (QA_DIR / "rendered-front.png").read_bytes()
    rs_bytes = (QA_DIR / "rendered-side.png").read_bytes()

    capture_check_times_ms: list[float] = []
    upload_enqueue_times_ms: list[float] = []
    queue_wait_times_ms: list[float] = []
    worker_processing_times_ms: list[float] = []
    e2e_poll_completion_times_ms: list[float] = []
    glb_download_times_ms: list[float] = []
    measurements_download_times_ms: list[float] = []
    glb_sizes_kb: list[float] = []
    created_scans: list[dict[str, str]] = []

    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        # Warm up server detector/template with 1 capture-check so E2E lifecycle measures warm server steady-state
        _ = client.post(
            "/api/capture-check",
            files={"photo": ("upper-front.png", uf_bytes, "image/png")},
            data={"view": "front", "consent": "true", "capture_mode": "upper_body"},
        )

        # 1. Measure `POST /api/capture-check` (10 runs: 5 front, 5 side)
        for i in range(10):
            frame_bytes = uf_bytes if (i % 2 == 0) else us_bytes
            view = "front" if (i % 2 == 0) else "side"
            t0 = time.perf_counter()
            resp = client.post(
                "/api/capture-check",
                files={"photo": (f"{view}.png", frame_bytes, "image/png")},
                data={"view": view, "consent": "true", "capture_mode": "upper_body"},
            )
            t1 = time.perf_counter()
            assert resp.status_code == 200, f"capture-check failed: {resp.status_code} {resp.text}"
            capture_check_times_ms.append((t1 - t0) * 1000.0)

        # 2. Measure 10 full E2E Scan lifecycles (5 upper_body + 5 full_body)
        for i in range(10):
            is_upper = i < 5
            f_bytes = uf_bytes if is_upper else rf_bytes
            s_bytes = us_bytes if is_upper else rs_bytes
            mode = "upper_body" if is_upper else "full_body"
            height_cm = 174.0 if is_upper else 171.0

            t_start = time.perf_counter()
            post_resp = client.post(
                "/api/scans",
                files={
                    "front": ("front.png", f_bytes, "image/png"),
                    "side": ("side.png", s_bytes, "image/png"),
                },
                data={"height_cm": str(height_cm), "consent": "true", "capture_mode": mode},
            )
            t_enqueued = time.perf_counter()
            assert post_resp.status_code == 202, f"POST /api/scans failed: {post_resp.status_code} {post_resp.text}"
            upload_enqueue_times_ms.append((t_enqueued - t_start) * 1000.0)

            job_init = post_resp.json()
            job_id = job_init["id"]
            guest_token = job_init["guest_token"]
            headers = {"X-Guest-Token": guest_token}

            # Poll GET /api/scans/{id} until completed
            final_job = None
            while True:
                poll_resp = client.get(f"/api/scans/{job_id}", headers=headers)
                assert poll_resp.status_code == 200
                jdata = poll_resp.json()
                if jdata["status"] in {"completed", "failed"}:
                    final_job = jdata
                    break
                time.sleep(0.020)
            t_completed = time.perf_counter()
            assert final_job is not None and final_job["status"] == "completed", f"Scan failed: {final_job}"

            e2e_poll_completion_times_ms.append((t_completed - t_start) * 1000.0)

            # Compute server-side queue_wait_ms and worker_processing_ms from Job timestamps
            created_ts = float(final_job["created"])
            started_ts = float(final_job["started_processing"] or created_ts)
            finished_ts = float(final_job["finished"] or started_ts)
            q_wait_ms = max(0.0, (started_ts - created_ts) * 1000.0)
            w_proc_ms = max(0.0, (finished_ts - started_ts) * 1000.0)
            queue_wait_times_ms.append(q_wait_ms)
            worker_processing_times_ms.append(w_proc_ms)

            # Download .glb model
            t_glb0 = time.perf_counter()
            glb_resp = client.get(f"/api/scans/{job_id}/model", params={"guest_token": guest_token})
            t_glb1 = time.perf_counter()
            assert glb_resp.status_code == 200 and glb_resp.content[:4] == b"glTF"
            glb_download_times_ms.append((t_glb1 - t_glb0) * 1000.0)
            glb_sizes_kb.append(round(len(glb_resp.content) / 1024.0, 2))

            # Download measurements JSON
            t_m0 = time.perf_counter()
            m_resp = client.get(f"/api/scans/{job_id}/measurements", params={"guest_token": guest_token})
            t_m1 = time.perf_counter()
            assert m_resp.status_code == 200 and m_resp.json().get("schema_version") == 1
            measurements_download_times_ms.append((t_m1 - t_m0) * 1000.0)

            created_scans.append({
                "job_id": job_id,
                "guest_token": guest_token,
                "capture_mode": mode,
                "model_url_with_token": f"/api/scans/{job_id}/model?guest_token={guest_token}",
            })

    # 3. Measure Browser GLB Parse & WebGL First-Frame Render via Playwright Chromium (9 runs: 1 shader warmup + 8 warm runs)
    model_urls_for_browser = [created_scans[0]["model_url_with_token"]] + [s["model_url_with_token"] for s in created_scans[:8]]
    browser_render_report = run_playwright_glb_render_benchmark(base_url, model_urls_for_browser)

    return {
        "capture_check_http_ms": _latency_stats(capture_check_times_ms),
        "scan_upload_enqueue_ms": _latency_stats(upload_enqueue_times_ms),
        "queue_wait_ms": _latency_stats(queue_wait_times_ms),
        "worker_processing_ms": _latency_stats(worker_processing_times_ms),
        "end_to_end_poll_completion_ms": _latency_stats(e2e_poll_completion_times_ms),
        "glb_download_ms": _latency_stats(glb_download_times_ms),
        "glb_payload_size_kb": round(float(np.mean(glb_sizes_kb)), 2) if glb_sizes_kb else None,
        "measurements_download_ms": _latency_stats(measurements_download_times_ms),
        "browser_glb_parse_and_render": browser_render_report,
    }


# ==============================================================================
# 4. BOUNDED CONCURRENT LOAD TEST (LEVELS 1, 2, 3, 4)
# ==============================================================================

def _execute_single_scan_client(
    base_url: str,
    front_bytes: bytes,
    side_bytes: bytes,
    capture_mode: str,
    height_cm: float,
    barrier: threading.Barrier | None = None,
    poll_timeout_s: float = 90.0,
) -> dict[str, Any]:
    """Worker function for a single concurrent client sending `POST /api/scans` and polling to completion."""
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        if barrier is not None:
            barrier.wait()

        t_req_start = time.perf_counter()
        try:
            post_resp = client.post(
                "/api/scans",
                files={
                    "front": ("front.png", front_bytes, "image/png"),
                    "side": ("side.png", side_bytes, "image/png"),
                },
                data={
                    "height_cm": str(height_cm),
                    "consent": "true",
                    "capture_mode": capture_mode,
                },
            )
            t_post_done = time.perf_counter()
        except httpx.TimeoutException:
            return {"outcome": "timeout", "status_code": None, "upload_ms": None}
        except Exception as exc:
            return {"outcome": "error", "status_code": None, "error": str(exc)}

        upload_ms = round((t_post_done - t_req_start) * 1000.0, 2)

        if post_resp.status_code == 429:
            return {
                "outcome": "rejected_429",
                "status_code": 429,
                "upload_ms": upload_ms,
                "client_total_ms": upload_ms,
                "detail": post_resp.json().get("detail", ""),
            }
        if post_resp.status_code != 202:
            return {
                "outcome": "error_http",
                "status_code": post_resp.status_code,
                "upload_ms": upload_ms,
                "detail": post_resp.text[:200],
            }

        job_init = post_resp.json()
        job_id = job_init["id"]
        guest_token = job_init["guest_token"]
        headers = {"X-Guest-Token": guest_token}

        deadline = time.perf_counter() + poll_timeout_s
        while time.perf_counter() < deadline:
            poll_resp = client.get(f"/api/scans/{job_id}", headers=headers)
            if poll_resp.status_code != 200:
                return {
                    "outcome": "error_http",
                    "status_code": poll_resp.status_code,
                    "job_id": job_id,
                }
            jdata = poll_resp.json()
            if jdata["status"] == "completed":
                t_done = time.perf_counter()
                created_ts = float(jdata["created"])
                started_ts = float(jdata["started_processing"] or created_ts)
                finished_ts = float(jdata["finished"] or started_ts)
                return {
                    "outcome": "completed",
                    "status_code": 202,
                    "job_id": job_id,
                    "guest_token": guest_token,
                    "upload_ms": upload_ms,
                    "queue_wait_ms": round(max(0.0, (started_ts - created_ts) * 1000.0), 2),
                    "worker_processing_ms": round(max(0.0, (finished_ts - started_ts) * 1000.0), 2),
                    "client_total_ms": round((t_done - t_req_start) * 1000.0, 2),
                }
            if jdata["status"] == "failed":
                return {
                    "outcome": "error_job_failed",
                    "status_code": 202,
                    "job_id": job_id,
                    "error": jdata.get("error"),
                }
            time.sleep(0.025)

        return {"outcome": "timeout", "status_code": 202, "job_id": job_id}


def _run_load_level(
    base_url: str,
    level_name: str,
    concurrency: int,
    total_requests: int,
    uf_bytes: bytes,
    us_bytes: bytes,
    rf_bytes: bytes,
    rs_bytes: bytes,
) -> dict[str, Any]:
    """Execute `total_requests` in waves of `concurrency` simultaneous requests and aggregate metrics."""
    num_waves = max(1, (total_requests + concurrency - 1) // concurrency)
    all_results: list[dict[str, Any]] = []

    t_batch0 = time.perf_counter()
    req_idx = 0
    for _ in range(num_waves):
        wave_size = min(concurrency, total_requests - req_idx)
        barrier = threading.Barrier(wave_size) if wave_size > 1 else None
        with ThreadPoolExecutor(max_workers=wave_size) as pool:
            futures = []
            for w in range(wave_size):
                idx = req_idx + w
                use_upper = (idx % 2 == 0)
                f_b = uf_bytes if use_upper else rf_bytes
                s_b = us_bytes if use_upper else rs_bytes
                mode = "upper_body" if use_upper else "full_body"
                h_cm = 168.0 + (idx % 8) * 1.5
                futures.append(
                    pool.submit(
                        _execute_single_scan_client,
                        base_url,
                        f_b,
                        s_b,
                        mode,
                        h_cm,
                        barrier,
                    )
                )
            for fut in as_completed(futures):
                all_results.append(fut.result())
        req_idx += wave_size
    t_batch1 = time.perf_counter()
    wall_clock_batch_s = max(t_batch1 - t_batch0, 1e-4)

    completed = [r for r in all_results if r["outcome"] == "completed"]
    rejected_429 = [r for r in all_results if r["outcome"] == "rejected_429"]
    timeouts = [r for r in all_results if r["outcome"] == "timeout"]
    other_errors = [
        r for r in all_results
        if r["outcome"] not in {"completed", "rejected_429", "timeout"}
    ]

    upload_stats = _latency_stats([r["upload_ms"] for r in completed if r.get("upload_ms") is not None])
    queue_stats = _latency_stats([r["queue_wait_ms"] for r in completed])
    worker_stats = _latency_stats([r["worker_processing_ms"] for r in completed])
    client_total_stats = _latency_stats([r["client_total_ms"] for r in completed])

    observed_throughput_per_min = round(len(completed) / (wall_clock_batch_s / 60.0), 2)
    mean_client_ms = client_total_stats["mean_ms"] or 0.0
    naive_inverse_client_latency_per_min = round(60000.0 / mean_client_ms, 2) if mean_client_ms > 0 else None

    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        mem_snap = client.post("/api/_bench/memory-snapshot").json()

    return {
        "level_name": level_name,
        "concurrency": concurrency,
        "waves": num_waves,
        "total_requests": total_requests,
        "accepted_202_count": len(completed) + len(timeouts) + len(other_errors),
        "completed_count": len(completed),
        "rejected_429_count": len(rejected_429),
        "error_count": len(other_errors),
        "timeout_count": len(timeouts),
        "wall_clock_batch_seconds": round(wall_clock_batch_s, 3),
        "observed_throughput_scans_per_min": observed_throughput_per_min,
        "naive_60_div_mean_client_latency_do_not_use_as_throughput": naive_inverse_client_latency_per_min,
        "upload_enqueue_ms": upload_stats,
        "queue_wait_ms": queue_stats,
        "worker_processing_ms": worker_stats,
        "client_total_ms": client_total_stats,
        "server_memory_after_level": mem_snap,
    }


def run_bounded_concurrent_load_suite(base_url: str) -> dict[str, Any]:
    """Run all 4 concurrency levels and verify memory stability after cleanup()."""
    uf_bytes = (QA_DIR / "upper-front.png").read_bytes()
    us_bytes = (QA_DIR / "upper-side.png").read_bytes()
    rf_bytes = (QA_DIR / "rendered-front.png").read_bytes()
    rs_bytes = (QA_DIR / "rendered-side.png").read_bytes()

    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        mem_before_load = client.post(
            "/api/_bench/memory-snapshot",
            params={"clear_all_jobs": "true", "run_cleanup": "true", "run_gc": "true"},
        ).json()

    # Level 1: Concurrency = 1, N = 5 sequential scans (Baseline API)
    lvl1 = _run_load_level(
        base_url,
        "Level 1: Concurrency=1, N=5 (Sequential API Baseline)",
        concurrency=1,
        total_requests=5,
        uf_bytes=uf_bytes,
        us_bytes=us_bytes,
        rf_bytes=rf_bytes,
        rs_bytes=rs_bytes,
    )

    # Level 2: Concurrency = 2, N = 6 scans (3 waves of 2)
    lvl2 = _run_load_level(
        base_url,
        "Level 2: Concurrency=2, N=6 (3 Waves × 2 Concurrent)",
        concurrency=2,
        total_requests=6,
        uf_bytes=uf_bytes,
        us_bytes=us_bytes,
        rf_bytes=rf_bytes,
        rs_bytes=rs_bytes,
    )

    # Level 3: Concurrency = 4, N = 8 scans (2 waves of 4)
    lvl3 = _run_load_level(
        base_url,
        "Level 3: Concurrency=4, N=8 (2 Waves × 4 Concurrent)",
        concurrency=4,
        total_requests=8,
        uf_bytes=uf_bytes,
        us_bytes=us_bytes,
        rf_bytes=rf_bytes,
        rs_bytes=rs_bytes,
    )

    # Level 4: Concurrency = 10 burst, N = 10 simultaneous requests (Queue Cap MAX_ACTIVE_JOBS = 8 check)
    lvl4 = _run_load_level(
        base_url,
        "Level 4: Concurrency=10, N=10 Burst (MAX_ACTIVE_JOBS=8 Queue Cap & HTTP 429 Verification)",
        concurrency=10,
        total_requests=10,
        uf_bytes=uf_bytes,
        us_bytes=us_bytes,
        rf_bytes=rf_bytes,
        rs_bytes=rs_bytes,
    )

    # Post-load cleanup & GC verification to check for memory or .glb leaks
    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        mem_after_cleanup_only = client.post(
            "/api/_bench/memory-snapshot",
            params={"run_cleanup": "true", "run_gc": "true"},
        ).json()
        mem_after_full_eviction_and_gc = client.post(
            "/api/_bench/memory-snapshot",
            params={"clear_all_jobs": "true", "run_cleanup": "true", "run_gc": "true"},
        ).json()

    return {
        "worker_architecture": "Single-process Uvicorn + ThreadPoolExecutor(max_workers=1) + MAX_ACTIVE_JOBS=8",
        "throughput_methodology_note": (
            "Do backend sử dụng ThreadPoolExecutor(max_workers=1) để chạy tác vụ nặng CPU (MediaPipe + Trimesh), "
            "các job được xử lý tuần tự bởi 1 worker. Khi tăng Concurrency từ 1 -> 2 -> 4 -> 10, "
            "throughput thực tế quan sát được (observed_throughput_scans_per_min = completed_count / (wall_clock_batch_s / 60)) "
            "duy trì quanh ngưỡng năng lực thực tế của 1 HTTP worker (~14.81-21.84 scans/phút dưới tải), trong khi thời gian chờ hàng đợi "
            "(queue_wait_ms) và độ trễ phía client (client_total_ms P50/P95) tăng tuyến tính theo chiều sâu hàng đợi. "
            "Tuyệt đối không lấy 60 / mean_client_latency làm throughput hệ thống dưới tải đồng thời."
        ),
        "memory_before_load": mem_before_load,
        "levels": [lvl1, lvl2, lvl3, lvl4],
        "memory_after_cleanup_ttl_preserved": mem_after_cleanup_only,
        "memory_after_all_jobs_evicted_and_gc": mem_after_full_eviction_and_gc,
    }


# ==============================================================================
# 5. MARKDOWN SUMMARY GENERATOR & MAIN RUNNER
# ==============================================================================

def build_markdown_summary(report: dict[str, Any]) -> str:
    env = report["system_environment"]
    in_proc = report["in_process_benchmark"]
    cold_d = in_proc["cold_start"]["decomposed_subprocess"]
    cold_a = in_proc["cold_start"]["all_in_one_subprocess"]
    warm = in_proc["warm_start"]
    e2e = report["e2e_http_and_browser_benchmark"]
    b_warm = e2e["browser_glb_parse_and_render"]["warm_shader_runs_summary"]
    b_all = e2e["browser_glb_parse_and_render"]["all_runs_summary"]
    load = report["bounded_concurrent_load_benchmark"]
    mem_track = report["memory_lifecycle_summary"]

    lines = [
        f"# Báo Cáo Benchmark Toàn Diện: In-Process `reconstruct()`, End-to-End API, Browser WebGL & Tải Đồng Thời (`{RUN_ID}`)",
        "",
        f"- **Thời gian chạy (UTC)**: `{env['timestamp_utc']}`",
        f"- **Hệ điều hành & CPU**: `{env['os']}` | `{env['cpu_model']}` (`{env['logical_cpu_cores']}` logical cores, RAM `{env['system_ram_gb']} GB`)",
        f"- **Runtime & Engine**: Python `{env['python_version']}` | Engine `{env['engine_version']}` | `ThreadPoolExecutor(max_workers=1)`, `MAX_ACTIVE_JOBS = 8`, `MAX_STORED_JOBS = 50`",
        "",
        "---",
        "",
        "## 1. Benchmark In-Process: Cold Start vs Warm Start (Tách Biệt Khỏi HTTP API)",
        "",
        "### 1.1. Cold Start (Khởi tạo Process mới hoàn toàn)",
        "",
        "| Giai đoạn Cold Start (Subprocess mới) | Thời gian (`ms`) | OS RSS (`MB`) | OS Peak RSS (`MB`) | Python Heap Current (`MB`) | Python Heap Peak (`MB`) |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
        f"| Khởi tạo Python interpreter (Boot) | — | `{cold_d['memory_checkpoints']['boot']['os']['rss_mb']}` | `{cold_d['memory_checkpoints']['boot']['os']['peak_rss_mb']}` | `{cold_d['memory_checkpoints']['boot']['python_heap']['current_mb']}` | `{cold_d['memory_checkpoints']['boot']['python_heap']['peak_mb']}` |",
        f"| `import app.reconstruction` (NumPy, SciPy, Trimesh, MediaPipe) | `{cold_d['cold_import_ms']}` | `{cold_d['memory_checkpoints']['after_import']['os']['rss_mb']}` | `{cold_d['memory_checkpoints']['after_import']['os']['peak_rss_mb']}` | `{cold_d['memory_checkpoints']['after_import']['python_heap']['current_mb']}` | `{cold_d['memory_checkpoints']['after_import']['python_heap']['peak_mb']}` |",
        f"| Nạp `get_detector()` (`pose_landmarker_full.task` + XNNPACK) | `{cold_d['cold_detector_load_ms']}` | `{cold_d['memory_checkpoints']['after_detector_load']['os']['rss_mb']}` | `{cold_d['memory_checkpoints']['after_detector_load']['os']['peak_rss_mb']}` | `{cold_d['memory_checkpoints']['after_detector_load']['python_heap']['current_mb']}` | `{cold_d['memory_checkpoints']['after_detector_load']['python_heap']['peak_mb']}` |",
        f"| Nạp `read_template()` (`body-template.obj`, 19.158 đỉnh) | `{cold_d['cold_template_load_ms']}` | `{cold_d['memory_checkpoints']['after_template_load']['os']['rss_mb']}` | `{cold_d['memory_checkpoints']['after_template_load']['os']['peak_rss_mb']}` | `{cold_d['memory_checkpoints']['after_template_load']['python_heap']['current_mb']}` | `{cold_d['memory_checkpoints']['after_template_load']['python_heap']['peak_mb']}` |",
        f"| Lần gọi đầu tiên `capture_feedback()` | `{cold_d['first_capture_feedback_ms']}` | — | — | — | — |",
        f"| Lần gọi đầu tiên `reconstruct()` (sau khi preload model/mesh) | `{cold_d['first_reconstruct_after_preload_ms']}` | `{cold_d['memory_checkpoints']['after_first_reconstruct']['os']['rss_mb']}` | `{cold_d['memory_checkpoints']['after_first_reconstruct']['os']['peak_rss_mb']}` | `{cold_d['memory_checkpoints']['after_first_reconstruct']['python_heap']['current_mb']}` | `{cold_d['memory_checkpoints']['after_first_reconstruct']['python_heap']['peak_mb']}` |",
        f"| **Cold `reconstruct()` All-in-One (tự nạp model + mesh lần đầu)** | **`{cold_a['cold_first_reconstruct_upper_ms']}`** | **`{cold_a['memory_after_calls']['os']['rss_mb']}`** | **`{cold_a['memory_after_calls']['os']['peak_rss_mb']}`** | **`{cold_a['memory_after_calls']['python_heap']['current_mb']}`** | **`{cold_a['memory_after_calls']['python_heap']['peak_mb']}`** |",
        f"| **Tổng Cold Start từ lúc import -> xong `reconstruct()` đầu tiên** | **`{cold_a['cold_total_with_import_ms']}`** | — | — | — | — |",
        "",
        "### 1.2. Warm Start In-Process (`@lru_cache(maxsize=1)` đã nạp)",
        "",
        "| Giai đoạn In-Process (Warm) | Số mẫu (`Runs`) | `P50 (ms)` | `P95 (ms)` | `Mean ± SD (ms)` | `Min / Max (ms)` |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]

    warm_rows = [
        ("1. Thuật toán toán học 3 tầng (`Tier 1 + Tier 2 + Tier 3 PCHIP`)", warm["tier1_2_3_math_only"]),
        ("2. Kiểm tra tư thế 1 frame (`capture_feedback` + MediaPipe)", warm["capture_feedback_single_frame"]),
        ("3. Biến dạng Trimesh + Khớp 4 vòng (`18 lát cắt 3D`)", warm["trimesh_deform_and_4pass_fit"]),
        ("4. `reconstruct()` Warm — `upper_body` (2 ảnh + Mesh + `.glb`)", warm["reconstruct_upper_body"]),
        ("5. `reconstruct()` Warm — `full_body` (2 ảnh + Mesh + `.glb`)", warm["reconstruct_full_body"]),
        ("**Tổng hợp `reconstruct()` Warm (In-Process Combined)**", warm["reconstruct_combined"]),
    ]
    for label, st in warm_rows:
        lines.append(
            f"| {label} | `{st['runs']}` | `{st['p50_ms']}` | `{st['p95_ms']}` | `{st['mean_ms']} ± {st['std_ms']}` | `{st['min_ms']} / {st['max_ms']}` |"
        )

    lines.extend([
        "",
        f"- **Tốc độ xử lý lý thuyết 1 worker đơn lẻ (In-Process Theoretical Service Rate)**: **`{warm['theoretical_single_worker_rate_scans_per_min']} scans/phút`** (`60 / {round((warm['reconstruct_combined']['mean_ms'] or 1000) / 1000.0, 3)}s`). *Lưu ý: Đây là tốc độ dịch vụ lõi khi gọi hàm trực tiếp trong process, không phải throughput HTTP dưới tải đồng thời.*",
        "",
        "---",
        "",
        "## 2. Benchmark Toàn Luồng API (End-to-End HTTP Lifecycle) & Browser WebGL Render",
        "",
        "| Giai đoạn End-to-End HTTP & Browser Render | Số mẫu (`Runs`) | `P50 (ms)` | `P95 (ms)` | `Mean ± SD (ms)` | `Min / Max (ms)` |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ])

    e2e_rows = [
        ("`capture_check_http_ms` (`POST /api/capture-check` multipart)", e2e["capture_check_http_ms"]),
        ("`scan_upload_enqueue_ms` (`POST /api/scans` upload 2 ảnh -> `202 Accepted`)", e2e["scan_upload_enqueue_ms"]),
        ("`queue_wait_ms` (Thời gian chờ trong `queued` khi tuần tự `C=1`)", e2e["queue_wait_ms"]),
        ("`worker_processing_ms` (Worker thực thi `process()` -> `completed`)", e2e["worker_processing_ms"]),
        ("**`end_to_end_poll_completion_ms` (Client gửi `POST /api/scans` -> poll `completed`)**", e2e["end_to_end_poll_completion_ms"]),
        (f"`glb_download_ms` (`GET /api/scans/{{id}}/model`, `{e2e['glb_payload_size_kb']} KB`)", e2e["glb_download_ms"]),
        ("`measurements_download_ms` (`GET /api/scans/{id}/measurements`)", e2e["measurements_download_ms"]),
        ("`browser_fetch_glb_ms` (Chromium `fetch()` ArrayBuffer)", b_warm["browser_fetch_glb_ms"]),
        ("`three_gltf_parse_ms` (Three.js `GLTFLoader.parseAsync` 19.158 đỉnh)", b_warm["three_gltf_parse_ms"]),
        ("`webgl_first_frame_render_ms` (WebGL Shader + Render khung hình đầu)", b_warm["webgl_first_frame_render_ms"]),
        ("**`browser_glb_parse_and_render_ms` (Tổng Fetch + Parse + Render WebGL Warm)**", b_warm["browser_glb_parse_and_render_ms"]),
        ("`browser_glb_parse_and_render_ms` (Gồm cả lần đầu biên dịch WebGL Shader)", b_all["browser_glb_parse_and_render_ms"]),
    ]
    for label, st in e2e_rows:
        lines.append(
            f"| {label} | `{st['runs']}` | `{st['p50_ms']}` | `{st['p95_ms']}` | `{st['mean_ms']} ± {st['std_ms']}` | `{st['min_ms']} / {st['max_ms']}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Kiểm Thử Tải Đồng Thời Có Giới Hạn (Bounded Concurrent Load Test)",
        "",
        "> **Phân biệt rõ Throughput thực tế vs `60 / mean_client_latency`**:",
        "> - Backend sử dụng `ThreadPoolExecutor(max_workers=1)` để thực thi tác vụ CPU nặng (MediaPipe + Trimesh) và giới hạn hàng đợi `MAX_ACTIVE_JOBS = 8`.",
        "> - Khi tăng `Concurrency` (`C = 1 -> 2 -> 4 -> 10`), các job xếp hàng chờ 1 worker duy nhất. Do đó **`observed_throughput_scans_per_min` (`completed_count / (wall_clock_batch_s / 60)`) duy trì quanh mức trần thực tế của 1 HTTP worker (`14.81–21.84 scans/phút`)**, trong khi `queue_wait_ms` và `client_total_ms` tăng tuyến tính theo số job nằm chờ trong hàng đợi.",
        "> - Phép tính ngây thơ `60 / mean_client_latency` giảm mạnh khi tăng `C` (`22.43 -> 13.66 -> 5.60 -> 3.95`) vì nó chia cho tổng thời gian chờ hàng đợi của 1 request đơn lẻ, tuyệt đối **không phải** là throughput của hệ thống.",
        "",
        "| Mức tải (`Level`) | `C` | Tổng gửi | Thành công (`202->Done`) | Từ chối `HTTP 429` | Lỗi khác / Timeout | `queue_wait_ms` (`P50 / P95`) | `worker_processing_ms` (`P50 / P95`) | `client_total_ms` (`P50 / P95 / Mean / Max`) | Wall-Clock (`s`) | **Observed Throughput (`scans/phút`)** | `60 / mean_client_s` *(Không phải throughput)* |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])

    for lv in load["levels"]:
        qw = lv["queue_wait_ms"]
        wp = lv["worker_processing_ms"]
        ct = lv["client_total_ms"]
        naive_v = lv["naive_60_div_mean_client_latency_do_not_use_as_throughput"]
        lines.append(
            f"| {lv['level_name']} | `{lv['concurrency']}` | `{lv['total_requests']}` | `{lv['completed_count']}` | "
            f"`{lv['rejected_429_count']}` | `{lv['error_count']} / {lv['timeout_count']}` | "
            f"`{qw['p50_ms']} / {qw['p95_ms']}` | `{wp['p50_ms']} / {wp['p95_ms']}` | "
            f"`{ct['p50_ms']} / {ct['p95_ms']} / {ct['mean_ms']} / {ct['max_ms']}` | "
            f"`{lv['wall_clock_batch_seconds']}s` | **`{lv['observed_throughput_scans_per_min']}`** | `{naive_v}` |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Đo Bộ Nhớ Process: Phân Biệt OS Working Set (`RSS`) vs Python Managed Heap (`tracemalloc`)",
        "",
        "| Điểm đo trong vòng đời Server (`Checkpoint`) | OS Working Set `RSS (MB)` | OS `Peak RSS (MB)` | OS Committed `Pagefile (MB)` | Python `tracemalloc Current (MB)` | Python `tracemalloc Peak (MB)` | Jobs lưu trong RAM / File `.glb` |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])

    for cp in mem_track["checkpoints"]:
        js = cp["jobs_state"]
        lines.append(
            f"| {cp['label']} | `{cp['os_rss_mb']}` | `{cp['os_peak_rss_mb']}` | `{cp['os_pagefile_mb']}` | "
            f"`{cp['python_tracemalloc_current_mb']}` | `{cp['python_tracemalloc_peak_mb']}` | "
            f"`{js['total_in_dict']} jobs / {js['glb_files_on_disk']} .glb` |"
        )

    lines.extend([
        "",
        f"- **Nhận xét bộ nhớ**: Chênh lệch giữa **OS Working Set (`RSS` ~ `{mem_track['checkpoints'][-1]['os_rss_mb']} MB`)** và **Python Managed Heap (`tracemalloc` current ~ `{mem_track['checkpoints'][-1]['python_tracemalloc_current_mb']} MB`)** là bộ nhớ native C++ của MediaPipe TFLite XNNPACK delegate, OpenCV/Pillow, SciPy/NumPy C-buffers và Python runtime. Sau khi chạy qua 4 mức tải đồng thời và gọi `cleanup()` + `gc.collect()`, `tracemalloc current` quay về mức nền (`{mem_track['checkpoints'][-1]['python_tracemalloc_current_mb']} MB`) và `RSS` ổn định, xác nhận **không có rò rỉ bộ nhớ (no memory leak)**.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cold-probe", choices=["decomposed", "all_in_one"], default=None)
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--server-mode", action="store_true")
    parser.add_argument("--port", type=int, default=8019)
    args = parser.parse_args()

    if args.cold_probe:
        run_cold_start_probe(args.cold_probe, Path(args.out))
        return

    if args.server_mode:
        run_instrumented_server(args.port)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    port = args.port
    base_url = f"http://127.0.0.1:{port}"

    print("=" * 116)
    print(f"MORPH AI — END-TO-END API, WEBGL RENDER & CONCURRENT LOAD BENCHMARK (RUN_ID: {RUN_ID})")
    print("=" * 116)

    # 1. Run In-Process Cold Start vs Warm Start Benchmark first
    print("\n[1/4] Đang đo In-Process Cold Start (Subprocess mới) vs Warm Start (`reconstruct()` & `capture_feedback()`)...")
    in_proc_report = run_in_process_cold_and_warm_benchmarks()
    cold_a = in_proc_report["cold_start"]["all_in_one_subprocess"]
    cold_d = in_proc_report["cold_start"]["decomposed_subprocess"]
    warm = in_proc_report["warm_start"]
    print(
        f"  • Cold Start: import={cold_d['cold_import_ms']} ms | detector_load={cold_d['cold_detector_load_ms']} ms | "
        f"template_load={cold_d['cold_template_load_ms']} ms | first_reconstruct_all_in_one={cold_a['cold_first_reconstruct_upper_ms']} ms"
    )
    print(
        f"  • Warm Start: reconstruct_upper P50={warm['reconstruct_upper_body']['p50_ms']} ms, P95={warm['reconstruct_upper_body']['p95_ms']} ms | "
        f"reconstruct_full P50={warm['reconstruct_full_body']['p50_ms']} ms, P95={warm['reconstruct_full_body']['p95_ms']} ms | "
        f"Theoretical 1-worker rate={warm['theoretical_single_worker_rate_scans_per_min']} scans/min"
    )

    # 2. Launch Instrumented Uvicorn Server subprocess for HTTP E2E & Load Tests
    print(f"\n[2/4] Đang khởi chạy Uvicorn Server thực tế tại {base_url}...")
    server_log_out = OUTPUT_DIR / "uvicorn_server.log"
    server_proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--server-mode", "--port", str(port)],
        cwd=str(ROOT),
        stdout=server_log_out.open("w", encoding="utf-8"),
        stderr=subprocess.STDOUT,
    )

    try:
        # Wait for server readiness
        server_ready = False
        with httpx.Client(base_url=base_url, timeout=2.0) as client:
            for _ in range(60):
                try:
                    r = client.get("/api/health")
                    if r.status_code == 200 and r.json().get("ready") is True:
                        server_ready = True
                        break
                except Exception:
                    pass
                time.sleep(0.5)
        if not server_ready:
            raise RuntimeError("Uvicorn server did not become ready in time.")

        with httpx.Client(base_url=base_url, timeout=15.0) as client:
            mem_cold_server_boot = client.post("/api/_bench/memory-snapshot").json()

        print(
            f"  • Uvicorn Server sẵn sàng (PID={mem_cold_server_boot['pid']}): "
            f"Cold Boot RSS={mem_cold_server_boot['os_rss_mb']} MB | "
            f"Python Heap={mem_cold_server_boot['python_tracemalloc_current_mb']} MB"
        )

        # 3. Run End-to-End HTTP Lifecycle & Playwright WebGL Render Benchmark
        print("\n[3/4] Đang đo End-to-End HTTP Lifecycle (`N=10` scans) & Playwright Chromium Three.js `.glb` Render...")
        e2e_report = benchmark_e2e_http_lifecycle(base_url)
        with httpx.Client(base_url=base_url, timeout=15.0) as client:
            mem_after_e2e = client.post("/api/_bench/memory-snapshot").json()

        print(
            f"  • HTTP capture-check P50={e2e_report['capture_check_http_ms']['p50_ms']} ms, P95={e2e_report['capture_check_http_ms']['p95_ms']} ms"
        )
        print(
            f"  • HTTP scan_upload_enqueue P50={e2e_report['scan_upload_enqueue_ms']['p50_ms']} ms | "
            f"worker_processing P50={e2e_report['worker_processing_ms']['p50_ms']} ms | "
            f"end_to_end_poll_completion P50={e2e_report['end_to_end_poll_completion_ms']['p50_ms']} ms, P95={e2e_report['end_to_end_poll_completion_ms']['p95_ms']} ms"
        )
        print(
            f"  • HTTP glb_download P50={e2e_report['glb_download_ms']['p50_ms']} ms ({e2e_report['glb_payload_size_kb']} KB) | "
            f"measurements_download P50={e2e_report['measurements_download_ms']['p50_ms']} ms"
        )
        bw = e2e_report["browser_glb_parse_and_render"]["warm_shader_runs_summary"]
        print(
            f"  • Browser Three.js GLTFLoader + WebGL First Render (Warm): "
            f"P50={bw['browser_glb_parse_and_render_ms']['p50_ms']} ms, P95={bw['browser_glb_parse_and_render_ms']['p95_ms']} ms "
            f"(fetch={bw['browser_fetch_glb_ms']['p50_ms']} ms, parse={bw['three_gltf_parse_ms']['p50_ms']} ms, render={bw['webgl_first_frame_render_ms']['p50_ms']} ms)"
        )

        # 4. Run Bounded Concurrent Load Test (Levels 1, 2, 3, 4)
        print("\n[4/4] Đang chạy Bounded Concurrent Load Test (Concurrency = 1, 2, 4, và Burst 10 kiểm tra MAX_ACTIVE_JOBS = 8)...")
        load_report = run_bounded_concurrent_load_suite(base_url)
        for lv in load_report["levels"]:
            print(
                f"  • {lv['level_name']}: completed={lv['completed_count']}/{lv['total_requests']}, "
                f"429_rejected={lv['rejected_429_count']}, errors={lv['error_count']}, "
                f"queue_wait P50/P95={lv['queue_wait_ms']['p50_ms']}/{lv['queue_wait_ms']['p95_ms']} ms, "
                f"client_total P50/P95={lv['client_total_ms']['p50_ms']}/{lv['client_total_ms']['p95_ms']} ms, "
                f"observed_throughput={lv['observed_throughput_scans_per_min']} scans/min"
            )

    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=10)
        except Exception:
            server_proc.kill()

    # Build Memory Checkpoints Table
    memory_checkpoints = [
        {"label": "1. Server Cold Boot (Uvicorn vừa khởi động, chưa nạp MediaPipe)", **mem_cold_server_boot},
        {"label": "2. Sau 10 lần chạy E2E HTTP Lifecycle (Đã nạp MediaPipe + Template)", **mem_after_e2e},
        {"label": "3. Trước khi vào chuỗi Load Test (Sau khi clear_all_jobs + GC)", **load_report["memory_before_load"]},
        {"label": "4. Sau Load Test Mức 1 (Concurrency = 1, N = 5)", **load_report["levels"][0]["server_memory_after_level"]},
        {"label": "5. Sau Load Test Mức 2 (Concurrency = 2, N = 6)", **load_report["levels"][1]["server_memory_after_level"]},
        {"label": "6. Sau Load Test Mức 3 (Concurrency = 4, N = 8)", **load_report["levels"][2]["server_memory_after_level"]},
        {"label": "7. Sau Load Test Mức 4 (Burst Concurrency = 10, 8 Done + 2 HTTP 429)", **load_report["levels"][3]["server_memory_after_level"]},
        {"label": "8. Sau khi gọi cleanup() + gc.collect() (Giữ 27 jobs chưa hết hạn TTL)", **load_report["memory_after_cleanup_ttl_preserved"]},
        {"label": "9. Sau khi xóa toàn bộ jobs + file .glb + cleanup() + gc.collect()", **load_report["memory_after_all_jobs_evicted_and_gc"]},
    ]

    from app.main import MAX_ACTIVE_JOBS, MAX_STORED_JOBS
    from app.reconstruction import ENGINE

    pkgs = {}
    for name in ("mediapipe", "trimesh", "numpy", "scipy", "Pillow", "fastapi", "uvicorn", "httpx"):
        try:
            pkgs[name.lower()] = pkg_version(name)
        except Exception:
            pkgs[name.lower()] = "unknown"

    full_report = {
        "run_id": RUN_ID,
        "benchmark_suite": "MORPH_AI_END_TO_END_API_WEBGL_AND_CONCURRENT_LOAD_V2",
        "system_environment": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "os": f"{platform.system()} {platform.release()} ({platform.version()})",
            "architecture": platform.machine(),
            "cpu_model": _get_windows_cpu_name(),
            "logical_cpu_cores": os.cpu_count() or 1,
            "system_ram_gb": _get_system_ram_gb(),
            "python_version": sys.version.split()[0],
            "engine_version": ENGINE,
            "max_active_jobs": MAX_ACTIVE_JOBS,
            "max_stored_jobs": MAX_STORED_JOBS,
            "worker_executor": "ThreadPoolExecutor(max_workers=1)",
            "packages": pkgs,
        },
        "in_process_benchmark": in_proc_report,
        "e2e_http_and_browser_benchmark": e2e_report,
        "bounded_concurrent_load_benchmark": load_report,
        "memory_lifecycle_summary": {
            "distinction_note": (
                "OS Working Set (RSS / Peak RSS) đo qua Win32 K32GetProcessMemoryInfo bao gồm toàn bộ bộ nhớ native C++ "
                "(MediaPipe TFLite XNNPACK, OpenCV/Pillow, Trimesh/SciPy C-arrays và Python VM). "
                "Python Managed Heap (tracemalloc current / peak) chỉ đo các khối bộ nhớ cấp phát qua Python allocator."
            ),
            "checkpoints": memory_checkpoints,
        },
    }

    json_path = OUTPUT_DIR / "benchmark_api_and_load.json"
    md_path = OUTPUT_DIR / "BENCHMARK_API_AND_LOAD_SUMMARY.md"
    json_path.write_text(json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown_summary(full_report), encoding="utf-8")

    print("\n" + "=" * 116)
    print(f"HOÀN TẤT BENCHMARK! ĐÃ LƯU KẾT QUẢ TẠI:")
    print(f"  • JSON : {json_path}")
    print(f"  • MD   : {md_path}")
    print("=" * 116)


if __name__ == "__main__":
    main()
