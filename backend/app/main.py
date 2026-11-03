from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import authorize, minecraft
from app.core.config import settings
from app.db import storage


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    storage.init_db()
    app.include_router(authorize.router)
    app.include_router(minecraft.router)

    @app.get("/")
    def root():
        return {
            "message": "Minecraft Link API 运行正常",
            "db": storage.stats(),
            "runtime": storage.runtime_info(),
        }

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


app = create_app()
