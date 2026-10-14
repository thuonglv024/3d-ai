from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MODELS = ROOT / "models"
MAX_UPLOAD = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
RESULT_TTL_SECONDS = 3600
