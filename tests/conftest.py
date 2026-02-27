from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)
