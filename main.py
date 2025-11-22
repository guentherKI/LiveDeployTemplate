from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import FileResponse
from pathlib import Path
import json, time, importlib.util, asyncio, traceback

app = FastAPI(title="LiveDeploy Template")

# ------------------------------------------------
# CONFIG HANDLING
# ------------------------------------------------
CONFIG_PATH = Path("config.json")
if not CONFIG_PATH.exists():
    CONFIG_PATH.write_text(json.dumps({
        "dashboard_route": "/dashboard",
        "webroot": "content",
        "default_page": "index.html",
        "routes": {}
    }, indent=4))

def load_config():
    return json.loads(CONFIG_PATH.read_text())

config = load_config()
WEBROOT = Path(config.get("webroot", "content"))
WEBROOT.mkdir(parents=True, exist_ok=True)

BACKEND_DIR = WEBROOT / "backend"
backend_modules = {}

# ------------------------------------------------
# BACKEND AUTO-RELOAD
# ------------------------------------------------
def load_backend(path: Path):
    module_name = f"backend_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    router = getattr(mod, "router", None)
    return module_name, router

def mount_backend(router, module_name):
    if router:
        app.include_router(router)
        backend_modules[module_name] = {"mtime": time.time(), "router": router}
        print(f"[Backend] Mounted: {module_name}")

def unmount_backend(module_name):
    if module_name not in backend_modules:
        return
    old_router = backend_modules[module_name]["router"]
    app.router.routes = [
        r for r in app.router.routes
        if not (hasattr(r, "endpoint") and r in old_router.routes)
    ]
    print(f"[Backend] Unmounted: {module_name}")
    del backend_modules[module_name]

async def backend_watcher():
    print("Backend watcher running...")
    while True:
        if BACKEND_DIR.exists():
            for file in BACKEND_DIR.glob("*.py"):
                module_name = f"backend_{file.stem}"
                mtime = file.stat().st_mtime

                if module_name not in backend_modules:
                    print(f"[Backend] Loading: {file}")
                    _, router = load_backend(file)
                    mount_backend(router, module_name)

                elif mtime > backend_modules[module_name]["mtime"]:
                    print(f"[Backend] Reload: {file.name}")
                    unmount_backend(module_name)
                    _, router = load_backend(file)
                    mount_backend(router, module_name)

        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(backend_watcher())

# ------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------
def content_is_empty():
    return not any(WEBROOT.iterdir())

def find_first_html():
    for file in sorted(WEBROOT.iterdir()):
        if file.suffix.lower() == ".html":
            return file
    return None

# ------------------------------------------------
# NEW API ROUTES
# ------------------------------------------------
@app.get("/api/config")
def api_get_config():
    return load_config()

@app.post("/api/config")
async def api_set_config(new_config: dict):
    CONFIG_PATH.write_text(json.dumps(new_config, indent=4))
    return {"status": "OK", "updated": new_config}

@app.get("/api/content")
def api_list_content():
    items = []
    for path in WEBROOT.rglob("*"):
        if path.is_file():
            items.append({
                "path": str(path.relative_to(WEBROOT)),
                "size": path.stat().st_size,
                "modified": path.stat().st_mtime
            })
    return items

@app.get("/api/content/{file_path:path}")
def api_read_file(file_path: str):
    fp = WEBROOT / file_path
    if not fp.exists():
        return {"error": "file not found"}
    return {"path": file_path, "content": fp.read_text(errors="ignore")}

@app.post("/api/content/{file_path:path}")
async def api_write_file(file_path: str, request: Request):
    fp = WEBROOT / file_path
    fp.parent.mkdir(parents=True, exist_ok=True)
    body = await request.body()
    fp.write_bytes(body)
    return {"status": "OK", "written": file_path}

@app.delete("/api/content/{file_path:path}")
def api_delete_file(file_path: str):
    fp = WEBROOT / file_path
    if not fp.exists():
        return {"error": "file not found"}
    fp.unlink()
    return {"status": "OK", "deleted": file_path}

# ------------------------------------------------
# FILE UPLOAD
# ------------------------------------------------
@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    target = WEBROOT / file.filename
    target.write_bytes(await file.read())
    return {"status": "OK", "saved": file.filename}

# ------------------------------------------------
# FRONTEND SERVING (catch-all)
# ------------------------------------------------
@app.get("/{path:path}")
def serve(path: str):

    config = load_config()
    WEBROOT = Path(config.get("webroot", "content"))
    WEBROOT.mkdir(exist_ok=True)

    ROUTES = config.get("routes", {})
    DEFAULT_PAGE = config.get("default_page")
    DASHBOARD_ROUTE = config.get("dashboard_route", "/dashboard")

    path = "/" + path.strip("/")

    if path == DASHBOARD_ROUTE:
        return FileResponse("template/dashboard.html")

    if content_is_empty() and path == "/":
        return FileResponse("template/index.html")

    if path == "/":
        if DEFAULT_PAGE:
            fp = WEBROOT / DEFAULT_PAGE
            if fp.exists():
                return FileResponse(fp)
        first = find_first_html()
        if first:
            return FileResponse(first)

    if path in ROUTES:
        fp = WEBROOT / ROUTES[path]
        if fp.exists():
            return FileResponse(fp)

    requested = WEBROOT / path.lstrip("/")
    if requested.exists() and requested.is_file():
        return FileResponse(requested)

    if (WEBROOT / "404.html").exists():
        return FileResponse(WEBROOT / "404.html", status_code=404)

    return FileResponse("template/404.html", status_code=404)
