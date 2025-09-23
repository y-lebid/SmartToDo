from fastapi import Request
from starlette.responses import Response

async def log_requests(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    response: Response = await call_next(request)
    print(f"Response status: {response.status_code}")
    return response

async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
