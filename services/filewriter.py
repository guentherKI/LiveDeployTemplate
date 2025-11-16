import os
import aiofiles

async def save_file(path: str, file):
    dirpath = os.path.dirname(path)
    os.makedirs(dirpath, exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        content = await file.read()
        await f.write(content)
