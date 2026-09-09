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

# FastAPI Ingress and Lifespan
app = FastAPI(
    title="AITU Gaming Hub Platform",
    description="High-performance, modular Telegram platform for Astana IT University esports club",
    version="1.0.0",
    lifespan=app_lifespan,
)

# Register Ingress Routes (/healthz, /ready, /webhook)
register_ingress_routes(app)


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
