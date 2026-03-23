"""
Airco Insights — Download Router
==================================
GET /download/{file_id} endpoint.
Serves generated Excel/PDF files from the application temp directory.
"""

import os
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.utils.file_handler import get_temp_dir

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed extensions for security
ALLOWED_EXTENSIONS = {".xlsx", ".pdf"}


@router.get("/download/{file_id}")
async def download_file(file_id: str):
    """
    Download a generated report file by its ID (filename).

    Only serves files from the application temp directory with allowed extensions.
    """
    # Security: strip path traversal attempts
    safe_name = os.path.basename(file_id)
    if safe_name != file_id:
        raise HTTPException(status_code=400, detail="Invalid file ID.")

    # Check extension
    _, ext = os.path.splitext(safe_name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type.")

    # Look in application temp directory (same as where pipeline writes files)
    temp_dir = get_temp_dir()
    file_path = os.path.join(temp_dir, safe_name)

    logger.info("Download requested: %s → %s (exists=%s)", file_id, file_path, os.path.isfile(file_path))

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found or expired.")

    # Determine media type
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if ext.lower() == ".xlsx"
        else "application/pdf"
    )

    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type=media_type,
    )
