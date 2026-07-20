import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile


def safe_join(*parts) -> Path:
    """Join path parts and create the resulting directory. Guards against
    path traversal by resolving and checking the result stays under the
    first (root) part."""
    root = Path(parts[0]).resolve()
    target = Path(*[str(p) for p in parts]).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Invalid path")
    target.mkdir(parents=True, exist_ok=True)
    return target


async def save_upload(file: UploadFile, dest_dir: Path, max_mb: int = 25) -> Path:
    suffix = Path(file.filename or "").suffix or ".bin"
    dest_path = dest_dir / f"{uuid.uuid4().hex}{suffix}"

    max_bytes = max_mb * 1024 * 1024
    size = 0
    with open(dest_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"File exceeds {max_mb}MB limit")
            out.write(chunk)

    return dest_path
