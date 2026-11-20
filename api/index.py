import sys
import os

# Ensure the root project directory is in Python's search path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Mark environment as Vercel serverless
os.environ.setdefault("VERCEL", "1")

# Ensure temporary writable directories exist
try:
    os.makedirs("/tmp/generated", exist_ok=True)
    os.makedirs("/tmp/data", exist_ok=True)
except Exception:
    pass

from app import app  # noqa: E402
