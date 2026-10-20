"""Experimental AI vision measurement mode.

This package is intentionally isolated from the existing MediaPipe + 3D
reconstruction pipeline. It only estimates measurements from two photos with a
vision LLM and never writes images to disk.
"""

from .router import router as ai_scan_router

__all__ = ["ai_scan_router"]
