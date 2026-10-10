
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="GA2 Q12 Middleware Service")

ALLOWED_ORIGIN = "https://app-jp517i.example.com"
RATE_LIMIT = 14
WINDOW_SECONDS = 10

# Independent request timestamps for each client.
client_requests = defaultdict(deque)


# Middleware 1: Request context
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid4())

    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# Middleware 2: Per-client rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in {"/ping", "/api/index"} and request.method == "GET":
        client_id = request.headers.get("X-Client-Id")

        if not client_id:
            client_id = "__missing_client_id__"

        now = time.monotonic()
        timestamps = client_requests[client_id]

        # Remove timestamps that are outside the 10-second window.
        while timestamps and now - timestamps[0] >= WINDOW_SECONDS:
            timestamps.popleft()

        print(
            f"RATE LIMIT DEBUG: client={client_id}, "
            f"count_before_request={len(timestamps)}"
        )

        if len(timestamps) >= RATE_LIMIT:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests"},
                headers={"Retry-After": "10"},
            )
            return response

        timestamps.append(now)

    return await call_next(request)


# Middleware 3: Scoped CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-Request-ID",
        "X-Client-Id",
    ],
)


async def ping_response(request: Request):
    return {
        "email": "23f2004679@ds.study.iitm.ac.in",
        "request_id": request.state.request_id,
    }


@app.get("/ping")
async def ping(request: Request):
    return await ping_response(request)


@app.get("/api/index")
async def vercel_ping(request: Request):
    return await ping_response(request)
