"""
Rebuild duplicate index script.
Scans SQLite image_hashes and re-indexes all entries into FAISS / NumPy vector index.
"""
import sys
import os

# Set root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.detectors.image.duplicates import rebuild_duplicate_index

if __name__ == "__main__":
    print("Rebuilding Lucen AI duplicate index...")
    rebuild_duplicate_index()
    print("Done!")
