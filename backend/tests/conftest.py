import sys
from pathlib import Path

# Ensure both 'backend' and workspace root are in sys.path when running pytest
backend_dir = Path(__file__).resolve().parent.parent
root_dir = backend_dir.parent
for d in (str(backend_dir), str(root_dir)):
    if d not in sys.path:
        sys.path.insert(0, d)

