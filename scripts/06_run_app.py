"""Fase 10 — lanza el dashboard Streamlit en el puerto 8510."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
                    "--server.port", "8510"], check=False)
