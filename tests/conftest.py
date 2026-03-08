import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
API_SRC = ROOT / "apps" / "api" / "src"

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
)
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")

for path in (ROOT, API_SRC):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
