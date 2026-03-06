import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import asyncio

app = FastAPI(title="email2Print Admin")

BASE_DIR        = Path("/app")
STATIC_DIR      = BASE_DIR / "app" / "webui" / "static"
UI_TEMPLATES    = BASE_DIR / "app" / "webui" / "templates"
PRINT_TPLS_DIR  = BASE_DIR / "templates"
JOBS_FILE       = BASE_DIR / "data" / "jobs.json"
LOG_FILE        = BASE_DIR / "logs" / "email2print.log"
ACTIVE_TPL_FILE = BASE_DIR / "data" / "active_template.txt"

STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(UI_TEMPLATES))


# ── Helpers ────────────────────────────────────────────────────────────────────────────

def _load_jobs():
    if not JOBS_FILE.exists():
        return []
    try:
        return json.loads(JOBS_FILE.read_text())
    except Exception:
        return []


def _active_template():
    if ACTIVE_TPL_FILE.exists():
        t = ACTIVE_TPL_FILE.read_text().strip()
        if t:
            return t
    return os.getenv("CONFIRM_TEMPLATE", "default_en.html")


def _list_print_templates():
    if not PRINT_TPLS_DIR.exists():
        return []
    return [f.name for f in sorted(PRINT_TPLS_DIR.iterdir()) if f.is_file() and f.suffix in (".html", ".txt")]


# ── Routes ───────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    jobs = _load_jobs()
    total   = len(jobs)
    success = sum(1 for j in jobs if j.get("status") == "success")
    failed  = total - success
    last_print = jobs[-1]["timestamp"][:19].replace("T", " ") if jobs else "—"
    recent  = list(reversed(jobs[-10:]))
    rate    = round(success / total * 100) if total else 0
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total": total, "success": success, "failed": failed,
        "last_print": last_print, "recent": recent, "rate": rate,
        "active_page": "dashboard",
    })


@app.get("/jobs", response_class=HTMLResponse)
async def job_history(request: Request, page: int = 1, status: str = "", sender: str = ""):
    jobs = list(reversed(_load_jobs()))
    if status:
        jobs = [j for j in jobs if j.get("status") == status]
    if sender:
        jobs = [j for j in jobs if sender.lower() in j.get("sender", "").lower()]
    per_page = 20
    total_pages = max(1, (len(jobs) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    paginated = jobs[(page - 1) * per_page: page * per_page]
    return templates.TemplateResponse("jobs.html", {
        "request": request,
        "jobs": paginated, "page": page, "total_pages": total_pages,
        "filter_status": status, "filter_sender": sender,
        "active_page": "jobs",
    })


@app.get("/mail-templates", response_class=HTMLResponse)
async def tmpl_manager(request: Request):
    # previews werden nicht mehr server-seitig gerendert,
    # sondern per JS via /mail-templates/{name}/content geladen
    tpls   = _list_print_templates()
    active = _active_template()
    return templates.TemplateResponse("templates.html", {
        "request": request,
        "templates": tpls,
        "active": active,
        "active_page": "templates",
    })


@app.post("/mail-templates/activate/{name}")
async def activate_template(name: str):
    allowed = _list_print_templates()
    if name not in allowed:
        return JSONResponse({"error": "Template not found"}, status_code=404)
    ACTIVE_TPL_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_TPL_FILE.write_text(name)
    return JSONResponse({"ok": True, "active": name})


@app.get("/mail-templates/{name}/content")
async def get_template_content(name: str):
    path = PRINT_TPLS_DIR / name
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({"name": name, "content": path.read_text(errors="ignore")})


class SavePayload(BaseModel):
    content: str


@app.put("/mail-templates/{name}/save")
async def save_template(name: str, payload: SavePayload):
    path = (PRINT_TPLS_DIR / name).resolve()
    if not str(path).startswith(str(PRINT_TPLS_DIR.resolve())):
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    PRINT_TPLS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.content, encoding="utf-8")
    return JSONResponse({"ok": True, "name": name})


class NewTemplatePayload(BaseModel):
    name: str
    content: str = ""


@app.post("/mail-templates/new")
async def create_template(payload: NewTemplatePayload):
    name = payload.name.strip()
    if not name.endswith(".html"):
        name += ".html"
    path = (PRINT_TPLS_DIR / name).resolve()
    if not str(path).startswith(str(PRINT_TPLS_DIR.resolve())):
        return JSONResponse({"error": "Invalid name"}, status_code=400)
    if path.exists():
        return JSONResponse({"error": "Already exists"}, status_code=409)
    PRINT_TPLS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.content or "<!-- New template -->\n", encoding="utf-8")
    return JSONResponse({"ok": True, "name": name})


@app.delete("/mail-templates/{name}")
async def delete_template(name: str):
    allowed = _list_print_templates()
    if name not in allowed:
        return JSONResponse({"error": "Not found"}, status_code=404)
    active = _active_template()
    if name == active:
        return JSONResponse({"error": "Cannot delete the active template"}, status_code=409)
    (PRINT_TPLS_DIR / name).unlink()
    return JSONResponse({"ok": True})


@app.get("/logs", response_class=HTMLResponse)
async def log_viewer(request: Request):
    return templates.TemplateResponse("logs.html", {
        "request": request, "active_page": "logs",
    })


@app.get("/logs/stream")
async def log_stream():
    async def event_generator():
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(errors="ignore").splitlines()
            for line in lines[-150:]:
                yield f"data: {line}\n\n"
        with open(LOG_FILE, "a+"):
            pass
        with open(LOG_FILE, "r") as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    env_keys = [
        "IMAP_SERVER", "IMAP_PORT", "EMAIL_ACCOUNT",
        "SMTP_SERVER", "SMTP_PORT", "SMTP_USERNAME", "FROM_ADDRESS",
        "PRINTER_NAME", "SLEEP_TIME", "ALLOWED_ATTACHMENT_TYPES",
        "ALLOWED_RECIPIENTS", "CONFIRM_TEMPLATE",
    ]
    secret_keys = {"EMAIL_PASSWORD", "SMTP_PASSWORD"}
    env_vals = {k: ("***" if k in secret_keys else os.getenv(k, "—")) for k in env_keys}

    printer_status = "unknown"
    try:
        result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=5)
        printer_status = result.stdout or result.stderr or "No output"
    except Exception as exc:
        printer_status = str(exc)

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "env": env_vals,
        "printer_status": printer_status,
        "active_page": "settings",
    })


@app.get("/api/stats")
async def api_stats():
    jobs  = _load_jobs()
    total   = len(jobs)
    success = sum(1 for j in jobs if j.get("status") == "success")
    failed  = total - success
    rate    = round(success / total * 100) if total else 0
    last_print = jobs[-1]["timestamp"][:19].replace("T", " ") if jobs else "—"
    return {"total": total, "success": success, "failed": failed, "rate": rate, "last_print": last_print}
