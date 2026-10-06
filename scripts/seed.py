from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from scripts.seed import main  # noqa: E402


if __name__ == "__main__":
    main()
