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
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from web.api.router import web_router, public_router
from web.api.v1.auth import v1_auth_router

# Register Ingress Routes (/healthz, /ready, /webhook)
register_ingress_routes(app)

# Mount Web API (Admin, Public, and V1 Services)
app.include_router(web_router)
app.include_router(public_router)
app.include_router(v1_auth_router)

# Mount Vue SPA Frontend
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException, Request, Depends
from web.api.dependencies import get_redis, get_steam_service
from web.api.v1.auth import steam_tma_bridge

@app.get("/auth/steam/bridge", include_in_schema=False)
async def auth_steam_bridge_alias(
    request: Request,
    state: str,
    redis=Depends(get_redis),
    steam_service=Depends(get_steam_service),
):
    return await steam_tma_bridge(
        request=request,
        state=state,
        redis=redis,
        steam_service=steam_service,
    )

dist_path = os.path.join(os.path.dirname(__file__), "web", "app", "dist")
if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_vue_app(full_path: str):
        if (
            full_path.startswith("api")
            or full_path.startswith("auth")
            or full_path.startswith("docs")
            or full_path.startswith("openapi.json")
            or full_path in ["healthz", "ready", "webhook"]
        ):
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
