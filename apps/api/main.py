from pathlib import Path
import sys

API_DIR = Path(__file__).resolve().parent
SRC_DIR = API_DIR / "src"
REPO_ROOT = API_DIR.parent.parent

for path in (SRC_DIR, REPO_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from airbeeps_api.main import app

__all__ = ["app"]
