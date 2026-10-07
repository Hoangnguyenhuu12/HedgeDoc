"""
Launcher script for HedgeDoc Streamlit Application.
Usage:
    python HedgeDoc/run_app.py
"""

import subprocess
import sys
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent / "frontend" / "app.py"

if __name__ == "__main__":
    cmd = [sys.executable, "-m", "streamlit", "run", str(APP_PATH)]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nĐã dừng ứng dụng HedgeDoc.")
