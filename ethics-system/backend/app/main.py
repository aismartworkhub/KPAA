"""애플리케이션 진입점.  실행: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, config, db, seed
from .routers import admin, auth, cases, documents, evidence, knowledge, meetings

log = logging.getLogger("kpaa")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()
    conn = db.get_conn()
    try:
        seed.seed_base(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="KPAA 윤리·징계·광고 업무지원 시스템", version=__version__, lifespan=lifespan,
              docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if not request.url.path.startswith("/api/docs"):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
            "frame-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    msgs = []
    for e in exc.errors():
        loc = ".".join(str(x) for x in e.get("loc", []) if x not in ("body", "query"))
        msgs.append(f"{loc}: {e.get('msg')}")
    return JSONResponse(status_code=422, content={"detail": "입력값을 확인하세요 — " + "; ".join(msgs)})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다. 관리자에게 문의하세요."})


for r in (auth.router, cases.router, evidence.router, knowledge.router, documents.router, meetings.router, admin.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    conn = db.get_conn()
    try:
        conn.execute("SELECT 1").fetchone()
    finally:
        conn.close()
    return {"ok": True, "version": __version__}


if config.FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(config.FRONTEND_DIR / "index.html")
