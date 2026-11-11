"""Entry point: `python app.py` launches the Streamlit chat UI.

Binds to HOST (default 127.0.0.1, local only) and PORT (default 8501).
"""
import sys
from pathlib import Path

from streamlit.web import cli as stcli

from src.config import settings

if __name__ == "__main__":
    ui = Path(__file__).resolve().parent / "src" / "ui" / "streamlit_app.py"
    sys.argv = [
        "streamlit", "run", str(ui),
        "--server.address", settings.host,
        "--server.port", str(settings.port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    print(f"Starting Music Store Support on http://{settings.host}:{settings.port}")
    sys.exit(stcli.main())
