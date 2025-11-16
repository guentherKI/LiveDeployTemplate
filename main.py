from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes.upload import router as upload_router
from routes.download import router as download_router
from pathlib import Path

app = FastAPI(title="LiveDeploy Minimal Example")

# Upload-Routen einbinden
app.include_router(upload_router)
app.include_router(download_router)

# Inhalte statisch bereitstellen
content_folder = Path("content/sites")
content_folder.mkdir(parents=True, exist_ok=True)
app.mount("/sites", StaticFiles(directory=content_folder), name="sites")

# Root-Route zum Testen
@app.get("/")
async def root():
    return {"message": "Server läuft!"}
