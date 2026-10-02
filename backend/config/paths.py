import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(
    os.getenv(
        "DATA_DIR",
        PROJECT_ROOT / "data",
    )
)

DOCUMENTS_DIR = DATA_DIR / "documents"

STATE_DIR = DATA_DIR / "state"

CHECKPOINT_FILE = STATE_DIR / "checkpoints.json"