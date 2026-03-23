import os
import uuid
import logging
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_temp_dir() -> str:
    """Get or create temporary directory for file processing."""
    temp_dir = os.path.abspath(settings.TEMP_DIR)
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def save_temp_file(content: bytes, extension: str = ".pdf") -> str:
    """Save bytes content to a uniquely named temp file. Returns file path."""
    temp_dir = get_temp_dir()
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Temp file saved: {filename} ({len(content)} bytes)")
    return file_path


def cleanup_file(file_path: str) -> None:
    """Safely delete a file."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up: {os.path.basename(file_path)}")
    except OSError as e:
        logger.warning(f"Failed to clean up {file_path}: {e}")


def cleanup_files(*file_paths: str) -> None:
    """Safely delete multiple files."""
    for path in file_paths:
        if path:
            cleanup_file(path)
