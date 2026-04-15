from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


if __name__ == "__main__":
    src_path = str((Path(__file__).parent / "src").resolve())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
