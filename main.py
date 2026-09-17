import logging
import sys
from fastapi import FastAPI
import uvicorn
from common.config import settings
from core.lifespan import app_lifespan, register_ingress_routes

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("main")

from fastapi.middleware.cors import CORSMiddleware

# FastAPI Ingress and Lifespan
app = FastAPI(
    title="AITU Gaming Hub Platform",
    description="High-performance, modular Telegram platform for Astana IT University esports club",
    version="1.0.0",
    lifespan=app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from web.api.router import web_router

# Register Ingress Routes (/healthz, /ready, /webhook)
register_ingress_routes(app)

# Mount Web API
app.include_router(web_router)

# Mount Vue SPA Frontend
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

dist_path = os.path.join(os.path.dirname(__file__), "web", "app", "dist")
if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_vue_app(full_path: str):
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json") or full_path in ["healthz", "ready", "webhook"]:
            raise HTTPException(status_code=404, detail="Not found")
        
        file_path = os.path.join(dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        return FileResponse(os.path.join(dist_path, "index.html"))


def start() -> None:
    """Entry point for command-line runner."""
    logger.info(f"Starting AITU Gaming Hub server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    start()
