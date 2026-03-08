import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
API_SRC = ROOT / "apps" / "api" / "src"

for path in (ROOT, API_SRC):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
