"""
MedLit AI — FastAPI Application Entry Point

This is where the application starts. FastAPI is a modern Python web framework
that handles HTTP requests. Think of it as a receptionist at a building:
- Requests arrive at specific URLs (routes).
- The receptionist (FastAPI) directs each request to the right handler.
- The handler processes the request and sends back a response.

KEY CONCEPTS:
- `app = FastAPI(...)` creates the application instance.
- `@app.get("/health")` registers a handler for GET requests to /health.
- CORS middleware lets the React frontend (different port) talk to this backend.
- Lifespan context manager handles startup/shutdown tasks.

HOW TO RUN:
    cd backend
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.summaries import router as summaries_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.

    Startup: log configuration, verify connections.
    Shutdown: clean up resources.

    WHY: Some resources (database connections, HTTP clients) should be
    created once at startup and cleaned up at shutdown, not per-request.
    """
    logger.info("Starting MedLit AI backend...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    # NOTE: We intentionally do NOT log API keys or secrets
    yield
    logger.info("Shutting down MedLit AI backend...")


app = FastAPI(
    title="MedLit AI",
    description=(
        "AI-powered medical literature summarization and research assistant. "
        "Helps researchers search, screen, summarize, and compare scientific publications. "
        "This tool assists research — it does not provide clinical recommendations."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
# CORS = Cross-Origin Resource Sharing.
# The browser blocks requests from one origin (localhost:5173, our React app)
# to a different origin (localhost:8000, our API) by default.
# This middleware tells the browser: "Yes, requests from these origins are allowed."
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.FRONTEND_PORT}",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allow any headers
)

# --- Register API Routers ---
# Each router handles a specific domain (summaries, articles, etc.)
# They are mounted on the app so their routes become available.
app.include_router(summaries_router)


# --- Health Check Endpoint ---
@app.get("/health", tags=["System"])
async def health_check():
    """
    Returns the application status.

    WHY: Every production service needs a health check endpoint.
    Monitoring tools, load balancers, and Docker HEALTHCHECK use this
    to verify the service is running. It's also a useful smoke test
    during development: if /health works, your server is up.

    Returns a simple JSON object. No authentication required.
    """
    return {
        "status": "healthy",
        "service": "medlit-ai",
        "version": "0.1.0",
        "llm_provider": settings.LLM_PROVIDER,
    }
