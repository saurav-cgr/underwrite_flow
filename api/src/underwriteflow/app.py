"""FastAPI composition root."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from underwriteflow.api.v1.router import router as api_v1_router
from underwriteflow.auth.router import router as auth_router
from underwriteflow.cases.router import router as cases_router
from underwriteflow.config import Settings, get_settings
from underwriteflow.database import Database
from underwriteflow.errors import ApiError, error_response
from underwriteflow.evaluation.router import router as evaluation_router
from underwriteflow.products.router import router as products_router
from underwriteflow.reviews.router import router as reviews_router
from underwriteflow.queues.router import router as queues_router


# Return an existing request ID or create one for an early failure.
def request_id_for(request: Request) -> str:
    return getattr(request.state, "request_id", None) or str(uuid4())


# Release database resources when the application stops.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.database.close()


# Build the local API with its stable service boundaries.
def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    app = FastAPI(title="UnderwriteFlow", lifespan=lifespan)
    app.state.settings = active_settings
    app.state.database = Database(active_settings.database_url)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach an opaque correlation ID to every response.
    @app.middleware("http")
    async def attach_request_id(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    # Return expected application errors without raw exception details.
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, error: ApiError) -> Response:
        return error_response(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            request_id=request_id_for(request),
            retryable=error.retryable,
            details=error.details,
        )

    # Normalize framework HTTP errors, including unknown routes.
    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, error: StarletteHTTPException
    ) -> Response:
        if error.status_code == 404:
            return error_response(
                status_code=404,
                code="not_found",
                message="Resource not found",
                request_id=request_id_for(request),
            )
        return error_response(
            status_code=error.status_code,
            code="http_error",
            message="Request could not be completed",
            request_id=request_id_for(request),
        )

    # Keep validation details generic until endpoint contracts define safe fields.
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> Response:
        del error
        return error_response(
            status_code=422,
            code="validation_error",
            message="Request validation failed",
            request_id=request_id_for(request),
        )

    # Prevent unhandled exceptions from exposing implementation details.
    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, error: Exception) -> Response:
        del error
        return error_response(
            status_code=500,
            code="internal_error",
            message="Internal server error",
            request_id=request_id_for(request),
            retryable=True,
        )

    # Report process health without contacting external providers.
    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Report database readiness through a minimal connection check.
    @app.get("/ready", tags=["system"])
    async def ready(request: Request) -> dict[str, str]:
        await request.app.state.database.ping()
        return {"status": "ready"}

    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(cases_router, prefix="/api/v1")
    app.include_router(products_router, prefix="/api/v1")
    app.include_router(reviews_router, prefix="/api/v1")
    app.include_router(queues_router, prefix="/api/v1")
    app.include_router(evaluation_router, prefix="/api/v1")
    return app
