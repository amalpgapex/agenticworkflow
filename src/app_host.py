
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Import your current FastAPI app (must expose: app = FastAPI(...))
from app_fastapi import app as rest_app

# Explicit allow-list of endpoints you DO want to expose as MCP tools
ALLOWLIST_ROUTE_MAPS = [
    # /api/transformations (listing and CRUD)
    RouteMap(methods=["GET"],  pattern=r"^/api/transformations$",                                 mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/api/transformation$",                                  mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"],  pattern=r"^/api/transformation/\{transformation_key\}$",           mcp_type=MCPType.TOOL),
    RouteMap(methods=["PUT"],  pattern=r"^/api/transformation/\{transformation_key\}$",           mcp_type=MCPType.TOOL),
    RouteMap(methods=["DELETE"],pattern=r"^/api/transformation/\{transformation_key\}$",          mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/api/transformation/\{transformation_key\}/duplicate$", mcp_type=MCPType.TOOL),
    RouteMap(methods=["GET"],  pattern=r"^/api/transformation/\{transformation_key\}/export$",    mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/api/transformation/import$",                           mcp_type=MCPType.TOOL),

    # /api/audio/{filename}
    RouteMap(methods=["GET"],  pattern=r"^/api/audio/\{filename\}$",                              mcp_type=MCPType.TOOL),

    # uploads
    #RouteMap(methods=["POST"], pattern=r"^/api/upload-labeled$",                                  mcp_type=MCPType.TOOL),
    #RouteMap(methods=["POST"], pattern=r"^/api/upload$",                                          mcp_type=MCPType.TOOL),
    #RouteMap(methods=["POST"], pattern=r"^/api/upload-dual$",                                     mcp_type=MCPType.TOOL),

    # stream, session, chat, export
    RouteMap(methods=["GET"],  pattern=r"^/api/stream/\{transformation_key\}$",                   mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/api/session/reset$",                                   mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/api/chat$",                                            mcp_type=MCPType.TOOL),
    #RouteMap(methods=["POST"], pattern=r"^/api/export$",                                          mcp_type=MCPType.TOOL),

    # Catalog and skill execution (new multiplexor)
    RouteMap(methods=["GET"], pattern=r"^/api/tools$",                                            mcp_type=MCPType.TOOL),
    RouteMap(methods=["POST"], pattern=r"^/api/tool/execute$",                                    mcp_type=MCPType.TOOL),

    # Catch-all: exclude EVERYTHING else (real allow-list)
    RouteMap(mcp_type=MCPType.EXCLUDE),
]

# Generate MCP from your FastAPI app, filtered via the allow-list
mcp = FastMCP.from_fastapi(
    app=rest_app,
    name="Catalyst UI UX POC - MCP Server",
    route_maps=ALLOWLIST_ROUTE_MAPS,
)

# MCP ASGI app (StarletteWithLifespan). Do not use path="/"
mcp_app = mcp.http_app("/")

# === FastAPI wrapper to expose /mcp/health and mount MCP ===
mcp_container = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# --- Correlation & error middleware (Azure-ready, para MCP container) ---
import uuid, time

@mcp_container.middleware("http")
async def mcp_correlation_mw(request: Request, call_next):
    """
    - Genera/propaga X-Request-ID para correlación end-to-end (APIM/clients).
    - Expone X-Process-Time en la respuesta.
    - La validación JWT/roles/scopes se hace en APIM, no aquí.
    """
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Error JSON uniforme con correlación
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Internal Server Error",
                    "request_id": request_id
                }
            }
        )

    duration = time.perf_counter() - start
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duration:.4f}"
    return response

async def _extract_mcp_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", request.headers.get("x-request-id", str(uuid.uuid4())))

@mcp_container.exception_handler(HTTPException)
async def mcp_http_exception_handler(request: Request, exc: HTTPException):
    request_id = await _extract_mcp_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id
            }
        }
    )

@mcp_container.exception_handler(Exception)
async def mcp_unhandled_exception_handler(request: Request, exc: Exception):
    request_id = await _extract_mcp_request_id(request)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal Server Error",
                "request_id": request_id
            }
        }
    )

@mcp_container.get("/health", include_in_schema=False)
async def mcp_health():
    return {"status": "ok", "app": "MCP", "message": "MCP HTTP app mounted"}

# Mount the MCP Starlette app inside the FastAPI container
mcp_container.mount("/", mcp_app)

@asynccontextmanager
async def combined_lifespan(app: FastAPI):
    # Initialize the lifespan of your REST app and MCP (session manager)
    async with rest_app.router.lifespan_context(rest_app):
        async with mcp_app.lifespan(app):
            yield

# Single host (root docs disabled so you see those of rest_app)
app = FastAPI(
    title="Catalyst API + MCP",
    lifespan=combined_lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Mount '/mcp' (container) first and then '/'
app.mount("/mcp", mcp_container)
app.mount("/", rest_app)




