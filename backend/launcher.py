from __future__ import annotations

import logging
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


ROOT_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[1]
)
LOG_DIR = ROOT_DIR / "logs"


def create_web_app(api_app: Any, frontend_dir: Path | None = None) -> FastAPI:
    static_dir = Path(frontend_dir or ROOT_DIR / "frontend" / "dist")
    if not (static_dir / "index.html").is_file():
        raise FileNotFoundError(f"Frontend build not found: {static_dir / 'index.html'}")

    web_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    web_app.mount("/api", api_app, name="api")
    web_app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
    return web_app


def _configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(LOG_DIR / "minecraft-link.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[console, file_handler], force=True)


def main() -> int:
    _configure_logging()
    logger = logging.getLogger("minecraft_link")

    from tools.bootstrap_config import ensure_config

    ensure_config(ROOT_DIR / ".env", ROOT_DIR / ".env.example")

    from app.main import app as api_app

    web_app = create_web_app(api_app)
    servers = [
        uvicorn.Server(
            uvicorn.Config(
                api_app,
                host="127.0.0.1",
                port=8959,
                log_level="info",
                log_config=None,
                access_log=True,
            )
        ),
        uvicorn.Server(
            uvicorn.Config(
                web_app,
                host="127.0.0.1",
                port=8958,
                log_level="info",
                log_config=None,
                access_log=True,
            )
        ),
    ]
    threads = [
        threading.Thread(target=server.run, name=f"uvicorn-{index}")
        for index, server in enumerate(servers)
    ]

    logger.info("Minecraft-Link starting. Web: http://127.0.0.1:8958 | API: http://127.0.0.1:8959")
    logger.info("Log file: %s", LOG_DIR / "minecraft-link.log")
    for thread in threads:
        thread.start()

    browser_opened = False
    try:
        while all(thread.is_alive() for thread in threads):
            if not browser_opened and all(server.started for server in servers):
                try:
                    webbrowser.open("http://127.0.0.1:8958")
                except OSError:
                    logger.warning("Could not open the browser automatically.")
                browser_opened = True
            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("Shutdown requested from console.")
    finally:
        for server in servers:
            server.should_exit = True
        for thread in threads:
            thread.join(timeout=10)

    if any(thread.is_alive() for thread in threads):
        logger.error("A server thread did not stop cleanly.")
        return 1
    if not all(server.started for server in servers):
        logger.error("A server failed to start. Check the port and startup messages above.")
        return 1
    logger.info("Minecraft-Link stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
