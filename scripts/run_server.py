"""
Start the FloodLens development server.

    python scripts/run_server.py

The server will be available at http://localhost:8000
API docs at http://localhost:8000/docs

To stop: press Ctrl+C once. The server will shut down cleanly.

Note: --reload is intentionally omitted. On Windows, uvicorn's file-watcher
spawns a child process that can hold port 8000 open after Ctrl+C, making the
port appear busy on the next start. Without --reload the single process exits
immediately on Ctrl+C.
"""

import subprocess
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"

if __name__ == "__main__":
    subprocess.run(
        [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
        ],
        cwd=str(SRC_DIR),
        check=True,
    )
