# backend/routes/download.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pathlib import Path

router = APIRouter()

@router.get("/api/files")
async def get_files():
    root_dir = Path("content/sites/testuser")
    result = {}

    for file_path in root_dir.rglob("*"):
        if file_path.is_file():
            with file_path.open("r", encoding="utf-8") as f:
                # Inhalt der Datei als String zurückgeben
                relative_path = file_path.relative_to(root_dir).as_posix()
                result[relative_path] = f.read()

    return JSONResponse(content=result)
