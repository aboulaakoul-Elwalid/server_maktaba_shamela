# app/main.py
"""
Main FastAPI application entry point.

This module:
1. Creates the FastAPI application
2. Configures it (title, description, middleware, etc.)
3. Includes all the routers from the endpoints
4. Provides the entry point for running the app locally with uvicorn

The modular organization helps with scaling as the app grows,
since each part (endpoints, core logic, etc.) is separated.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import traceback

from app.config.settings import settings
from app.api.endpoints import embed, retrieval, ingestion, rag_query, auth, chat
from app.utils.helpers import setup_logging
import os
# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Create the FastAPI application with metadata for OpenAPI/Swagger
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs",  # URL for Swagger UI
    redoc_url="/redoc",  # URL for ReDoc
    debug=True  # Add debug here instead of creating a new app
)

# Configure CORS
if settings.CORS_ORIGINS == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

logger.info(f"Configuring CORS with allowed origins: {allowed_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Middleware that times how long each request takes to process and
    adds it as a header in the response. This is useful for monitoring
    performance and debugging slow endpoints.
    """
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        # Log the full exception with traceback
        logger.error(f"Request failed: {e}\n{traceback.format_exc()}")
        # Return a JSON error response
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

# Include routers from endpoints
app.include_router(embed.router, prefix="/embed", tags=["embeddings"])
app.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
app.include_router(rag_query.router, prefix="/rag", tags=["rag"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])

# Include other routers as needed

# Startup and shutdown events git push -u origin main
@app.on_event("startup")
async def startup_event():
    """
    Runs when the application starts up.
    Initialize connections to external services, load models, etc.
    """
    logger.info("Application startup: initializing services and connections")
    # You can add initialization code here if needed
    
@app.on_event("shutdown")
async def shutdown_event():
    """
    Runs when the application is shutting down.
    Close connections, free resources, etc.
    """
    logger.info("Application shutdown: cleaning up resources")
    # You can add cleanup code here if needed

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Simple health check endpoint to verify the API is running"""
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Hello World"}
    
if __name__ == "__main__":
    # This block only runs when you execute the file directly
    # (not when imported by another module)
    import uvicorn
    logger.info(f"Starting application in development mode on port {settings.PORT}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)