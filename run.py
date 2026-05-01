from __future__ import annotations

import os
import sys
import socket
from pathlib import Path

import uvicorn


def _find_free_port(start_port: int, limit: int = 20) -> int:
    for port in range(start_port, start_port + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + limit - 1}")


if __name__ == "__main__":
    src_path = str((Path(__file__).parent / "src").resolve())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    base_port = int(os.getenv("PORT", "8002"))
    port = _find_free_port(base_port)
    if port != base_port:
        print(f"Port {base_port} is busy; using {port} instead.")
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)
