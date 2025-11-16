from fastapi import APIRouter, UploadFile, File
from pathlib import Path
import shutil

router = APIRouter()

@router.post("/api/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    # Speichert die Dateien dynamisch im Workspace (oder Standardpfad)
    root_dir = Path("content/sites/testuser")
    for file in files:
        dest = root_dir / file.filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    return {"status": "success", "files": [f.filename for f in files]}
