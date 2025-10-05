import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class RequestLogger(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
            return response
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            logging.getLogger("uvicorn.access").info(
                "%s %s -> %s (%.2f ms)",
                request.method,
                request.url.path,
                getattr(response, "status_code", "?"),
                dur_ms,
            )
