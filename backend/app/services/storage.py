import os
import time
import shutil
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../data/runtime/uploads")
)

def cleanup_old_uploads():
    """
    Deletes upload directories older than settings.RETENTION_HOURS.
    Results and evidence rows are preserved.
    """
    if not os.path.exists(UPLOADS_DIR):
        return

    cutoff = time.time() - (settings.RETENTION_HOURS * 3600)
    cleaned_count = 0

    try:
        for entry in os.listdir(UPLOADS_DIR):
            entry_path = os.path.join(UPLOADS_DIR, entry)
            if os.path.isdir(entry_path):
                mtime = os.path.getmtime(entry_path)
                if mtime < cutoff:
                    try:
                        shutil.rmtree(entry_path)
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove expired upload dir {entry_path}: {e}")
    except Exception as e:
        logger.error(f"Error during uploads cleanup: {e}")

    if cleaned_count > 0:
        logger.info(f"Cleaned up {cleaned_count} expired upload folder(s).")
