"""信息化运维管理系统 · FastAPI 入口。

启动：.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .db import DATA_DIR, init_db
from .test_mode import is_test_mode
from .test_seed import maybe_seed_test_data
from .routers import assets, config, duty, materials, public, reports, rooms, staff_auth, staff_tickets

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR.parent / "frontend" / "dist"

app = FastAPI(title="信息化运维管理系统", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(staff_auth.router)
app.include_router(staff_tickets.router)
app.include_router(reports.router)
app.include_router(materials.router)
app.include_router(rooms.router)
app.include_router(assets.router)
app.include_router(config.router)
app.include_router(duty.router)
app.include_router(rooms.print_router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    if is_test_mode():
        print("[WARN] OPS_TEST_MODE=1：已启用免密登录，仅限测试环境使用！")
    maybe_seed_test_data()


@app.get("/api/health")
def health():
    return {"ok": True, "service": "ops-management"}


if (DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

(DATA_DIR / "uploads").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=DATA_DIR / "uploads"), name="uploads")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")
    target = (DIST_DIR / full_path).resolve()
    if full_path and str(target).startswith(str(DIST_DIR.resolve())) and target.is_file():
        return FileResponse(target)
    index = DIST_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(
        "<meta charset='utf-8'><div style='font-family:sans-serif;padding:40px'>"
        "前端尚未构建，请先执行 <code>cd frontend && npm install && npm run build</code>"
        "</div>",
        status_code=200,
    )
