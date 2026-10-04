"""
Duplicate and near-duplicate image detection engine (§10, §13).
Layers:
1. pHash (imagehash) + Hamming distance (catches exact and resized copies)
2. CLIP embeddings (openai/clip-vit-base-patch32) on normalized vectors (catches crops, color edits, mirrored images)
Indexed in FAISS (faiss-cpu) with NumPy brute-force fallback.
"""
import os
import json
import logging
import sqlite3
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image
import imagehash
import torch

from ...db.database import get_connection
from ...db.repository import mask_claimant_name

logger = logging.getLogger("lucen_ai.duplicates")

INDEX_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../data/runtime/index")
)
FAISS_INDEX_PATH = os.path.join(INDEX_DIR, "clip_faiss.index")
NUMPY_INDEX_PATH = os.path.join(INDEX_DIR, "clip_vectors.npz")
META_PATH = os.path.join(INDEX_DIR, "index_meta.json")

# Global in-memory cache for CLIP model and index
_CLIP_PROCESSOR = None
_CLIP_MODEL = None
_FAISS_INDEX = None
_NUMPY_VECTORS = None  # (N, 512)
_NUMPY_META = []       # list of dicts

def _get_calibration_thresholds() -> Tuple[int, float]:
    calib_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../models/calibration.json")
    )
    phash_thresh = 6
    clip_thresh = 0.85
    if os.path.exists(calib_path):
        try:
            with open(calib_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                dup = data.get("duplicates", {})
                phash_thresh = int(dup.get("phash_hamming_threshold", 6))
                clip_thresh = float(dup.get("clip_cosine_threshold", 0.85))
        except Exception as e:
            logger.warning(f"Could not read duplicate calibration: {e}")
    return phash_thresh, clip_thresh

def _load_clip():
    global _CLIP_PROCESSOR, _CLIP_MODEL
    if _CLIP_MODEL is not None and _CLIP_PROCESSOR is not None:
        return _CLIP_PROCESSOR, _CLIP_MODEL
    try:
        from transformers import CLIPProcessor, CLIPModel
        model_id = "openai/clip-vit-base-patch32"
        _CLIP_PROCESSOR = CLIPProcessor.from_pretrained(model_id, local_files_only=True)
        _CLIP_MODEL = CLIPModel.from_pretrained(model_id, local_files_only=True)
        _CLIP_MODEL.eval()
        logger.info("CLIP model loaded for duplicate detection.")
    except Exception as e:
        logger.error(f"Failed to load CLIP model offline: {e}")
        _CLIP_PROCESSOR = None
        _CLIP_MODEL = None
    return _CLIP_PROCESSOR, _CLIP_MODEL

def compute_phash(img: Image.Image) -> str:
    """Computes pHash string for an image."""
    rgb = img.convert("RGB")
    return str(imagehash.phash(rgb))

def compute_clip_embedding(img: Image.Image) -> Optional[np.ndarray]:
    """Computes L2-normalized 512-dim embedding using CLIP."""
    proc, model = _load_clip()
    if proc is None or model is None:
        return None
    try:
        rgb = img.convert("RGB")
        inputs = proc(images=rgb, return_tensors="pt")
        with torch.no_grad():
            out = model.get_image_features(**inputs)
            if hasattr(out, "pooler_output") and out.pooler_output is not None:
                feats = out.pooler_output
            elif hasattr(out, "image_embeds") and out.image_embeds is not None:
                feats = out.image_embeds
            elif isinstance(out, torch.Tensor):
                feats = out
            else:
                feats = out[0]
            norm = feats.norm(p=2, dim=-1, keepdim=True)
            norm_feats = feats / (norm + 1e-7)
            vec = norm_feats.cpu().numpy().astype("float32")[0]
            return vec
    except Exception as e:
        logger.error(f"Error computing CLIP embedding: {e}")
        return None

# --- Index Management ---

def _init_index():
    global _FAISS_INDEX, _NUMPY_VECTORS, _NUMPY_META
    os.makedirs(INDEX_DIR, exist_ok=True)
    
    # Try FAISS first
    try:
        import faiss
        if os.path.exists(FAISS_INDEX_PATH):
            _FAISS_INDEX = faiss.read_index(FAISS_INDEX_PATH)
            logger.info(f"Loaded FAISS index with {_FAISS_INDEX.ntotal} entries.")
        else:
            _FAISS_INDEX = faiss.IndexFlatIP(512)
            logger.info("Initialized new empty FAISS IndexFlatIP(512).")
        if os.path.exists(META_PATH):
            with open(META_PATH, "r", encoding="utf-8") as f:
                _NUMPY_META = json.load(f)
        else:
            _NUMPY_META = []
        logger.info("Active duplicate index: FAISS (faiss-cpu)")
        return
    except Exception as e:
        logger.warning(f"FAISS not available or failed ({e}). Falling back to NumPy brute-force.")

    # NumPy Fallback
    logger.info("Active duplicate index: NumPy brute-force cosine fallback")
    if os.path.exists(NUMPY_INDEX_PATH):
        try:
            data = np.load(NUMPY_INDEX_PATH)
            _NUMPY_VECTORS = data["vectors"]
        except Exception:
            _NUMPY_VECTORS = np.zeros((0, 512), dtype=np.float32)
    else:
        _NUMPY_VECTORS = np.zeros((0, 512), dtype=np.float32)

    if os.path.exists(META_PATH):
        with open(META_PATH, "r", encoding="utf-8") as f:
            _NUMPY_META = json.load(f)
    else:
        _NUMPY_META = []

def _save_index():
    global _FAISS_INDEX, _NUMPY_VECTORS, _NUMPY_META
    os.makedirs(INDEX_DIR, exist_ok=True)
    if _FAISS_INDEX is not None:
        try:
            import faiss
            faiss.write_index(_FAISS_INDEX, FAISS_INDEX_PATH)
        except Exception as e:
            logger.warning(f"Could not persist FAISS index: {e}")
    elif _NUMPY_VECTORS is not None:
        try:
            np.savez_compressed(NUMPY_INDEX_PATH, vectors=_NUMPY_VECTORS)
        except Exception as e:
            logger.warning(f"Could not persist NumPy index: {e}")

    try:
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(_NUMPY_META, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not persist index metadata: {e}")

def create_thumbnail(img: Image.Image, output_path: str, size: Tuple[int, int] = (256, 256)) -> str:
    """Generates and saves a thumbnail JPEG."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    thumb = img.copy()
    thumb.thumbnail(size)
    thumb.convert("RGB").save(output_path, "JPEG", quality=85)
    return output_path

def search_duplicates(
    image_path: Any = None,
    current_claim_id: Optional[str] = None,
    current_claimant_id: Optional[str] = None,
    current_slot: Optional[str] = None,
    image: Any = None
) -> List[Dict[str, Any]]:
    """
    Searches index and database for duplicates matching image_path (path or PIL Image).
    Matches are filtered to OTHER claims only (ignoring same claim and same claimant's resubmission of same slot).
    """
    if image is not None:
        image_path = image
    _init_index()
    phash_thresh, clip_thresh = _get_calibration_thresholds()

    try:
        if isinstance(image_path, Image.Image):
            img = image_path
            q_phash = imagehash.phash(img.convert("RGB"))
            q_embed = compute_clip_embedding(img)
            flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)
            q_embed_flip = compute_clip_embedding(flipped_img)
        elif os.path.exists(str(image_path)):
            with Image.open(image_path) as img:
                q_phash = imagehash.phash(img.convert("RGB"))
                q_embed = compute_clip_embedding(img)
                # Mirrored flip
                flipped_img = img.transpose(Image.FLIP_LEFT_RIGHT)
                q_embed_flip = compute_clip_embedding(flipped_img)
        else:
            return []
    except Exception as e:
        logger.warning(f"Could not open image for duplicate detection: {e}")
        return []

    conn = get_connection()
    # Query candidate records from other claims
    # Rule: compare only against OTHER claims; ignore matches within the same claim and same claimant resubmission of same slot
    query = """
        SELECT ih.id, ih.claim_id, ih.claimant_id, ih.result_id, ih.slot,
               ih.phash, ih.embedding_row, ih.file_path, ih.thumbnail_path, ih.created_at,
               c.claimant_name
        FROM image_hashes ih
        LEFT JOIN claims c ON ih.claim_id = c.id
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    matches = []
    
    for r in rows:
        row = dict(r)
        other_claim_id = row.get("claim_id")
        other_claimant_id = row.get("claimant_id")
        other_slot = row.get("slot")

        # 0. Compare only against OTHER legitimate claims
        if not other_claim_id:
            continue

        # 1. Ignore matches within the same claim
        if current_claim_id and other_claim_id == current_claim_id:
            continue

        # 2. Ignore same claimant's resubmission of the same slot
        if current_claimant_id and other_claimant_id == current_claimant_id:
            if current_slot and other_slot == current_slot:
                continue

        other_phash_str = row.get("phash")
        phash_dist = 999
        if other_phash_str:
            try:
                other_phash = imagehash.hex_to_hash(other_phash_str)
                phash_dist = q_phash - other_phash
            except Exception:
                pass

        # CLIP cosine similarity
        clip_sim = 0.0
        clip_flip_sim = 0.0
        emb_idx = row.get("embedding_row")

        if emb_idx is not None and 0 <= emb_idx < len(_NUMPY_META):
            # Check vector in index
            try:
                if _FAISS_INDEX is not None and emb_idx < _FAISS_INDEX.ntotal:
                    stored_vec = _FAISS_INDEX.reconstruct(emb_idx)
                elif _NUMPY_VECTORS is not None and emb_idx < len(_NUMPY_VECTORS):
                    stored_vec = _NUMPY_VECTORS[emb_idx]
                else:
                    stored_vec = None

                if stored_vec is not None and q_embed is not None:
                    clip_sim = float(np.dot(q_embed, stored_vec))
                if stored_vec is not None and q_embed_flip is not None:
                    clip_flip_sim = float(np.dot(q_embed_flip, stored_vec))
            except Exception as e:
                logger.debug(f"Error reading vector from index: {e}")

        # Determine match type and similarity
        matched = False
        match_type = None
        similarity = 0.0

        if phash_dist == 0:
            matched = True
            match_type = "exact"
            similarity = 1.0
        elif phash_dist <= phash_thresh:
            matched = True
            match_type = "resized"
            similarity = max(0.85, 1.0 - (phash_dist / 64.0))
        elif clip_sim >= clip_thresh:
            matched = True
            similarity = clip_sim
            if phash_dist <= 14:
                match_type = "cropped"
            else:
                match_type = "edited"
        elif clip_flip_sim >= clip_thresh:
            matched = True
            match_type = "mirrored"
            similarity = clip_flip_sim

        if matched:
            diff_claimant = (other_claimant_id != current_claimant_id) if (other_claimant_id and current_claimant_id) else True
            raw_claimant_name = row.get("claimant_name") or "Another Claimant"
            masked_name = mask_claimant_name(raw_claimant_name)

            matches.append({
                "other_claim_id": other_claim_id,
                "other_claimant": masked_name,
                "other_claimant_id": other_claimant_id,
                "other_result_id": row.get("result_id"),
                "date": row.get("created_at"),
                "similarity": round(float(similarity), 3),
                "phash_distance": int(phash_dist),
                "match_type": match_type,
                "different_claimant": diff_claimant,
                "thumbnail_earlier": row.get("thumbnail_path"),
            })

    # Sort matches by similarity descending
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches

find_image_duplicates = search_duplicates

def index_image(
    image_path: Any = None,
    claim_id: Optional[str] = None,
    claimant_id: Optional[str] = None,
    result_id: str = "res_temp",
    slot: str = "image",
    thumbnail_path: Optional[str] = None,
    image: Any = None
) -> Optional[int]:
    """
    Indexes an image after analysis completes.
    Computes pHash and CLIP embeddings, stores in index and image_hashes table.
    """
    if image is not None:
        image_path = image
    global _FAISS_INDEX, _NUMPY_VECTORS, _NUMPY_META
    _init_index()

    art_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../data/runtime/artifacts", result_id)
    )
    os.makedirs(art_dir, exist_ok=True)

    try:
        if isinstance(image_path, Image.Image):
            img = image_path
            stored_path = os.path.join(art_dir, f"indexed_{slot}.jpg")
            img.convert("RGB").save(stored_path, "JPEG")
            file_path_to_save = stored_path
            phash_str = compute_phash(img)
            embed = compute_clip_embedding(img)
            if not thumbnail_path:
                thumb_file = f"thumb_{slot}.jpg"
                thumbnail_path = create_thumbnail(img, os.path.join(art_dir, thumb_file))
        else:
            if not os.path.exists(str(image_path)):
                logger.warning(f"Cannot index non-existent image: {image_path}")
                return None
            file_path_to_save = str(image_path)
            with Image.open(image_path) as img:
                phash_str = compute_phash(img)
                embed = compute_clip_embedding(img)
                if not thumbnail_path:
                    thumb_file = f"thumb_{slot}_{os.path.basename(image_path)}"
                    thumbnail_path = create_thumbnail(img, os.path.join(art_dir, thumb_file))
    except Exception as e:
        logger.error(f"Failed to process image for indexing: {e}")
        return None

    emb_row = len(_NUMPY_META)

    if embed is not None:
        try:
            import faiss
            if _FAISS_INDEX is None:
                _FAISS_INDEX = faiss.IndexFlatIP(512)
            vec_batch = np.array([embed], dtype=np.float32)
            _FAISS_INDEX.add(vec_batch)
        except Exception:
            if _NUMPY_VECTORS is None or len(_NUMPY_VECTORS) == 0:
                _NUMPY_VECTORS = np.array([embed], dtype=np.float32)
            else:
                _NUMPY_VECTORS = np.vstack([_NUMPY_VECTORS, embed])

    meta_entry = {
        "claim_id": claim_id,
        "claimant_id": claimant_id,
        "result_id": result_id,
        "slot": slot,
        "phash": phash_str,
        "embedding_row": emb_row,
        "thumbnail_path": thumbnail_path
    }
    _NUMPY_META.append(meta_entry)
    _save_index()

    # Insert into image_hashes database table
    from datetime import datetime
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO image_hashes (
            claim_id, claimant_id, result_id, slot, phash,
            embedding_row, file_path, thumbnail_path, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            claim_id, claimant_id, result_id, slot, phash_str,
            emb_row, file_path_to_save, thumbnail_path, datetime.utcnow().isoformat()
        )
    )
    conn.commit()
    conn.close()
    logger.info(f"Indexed image for result {result_id} (claim {claim_id}) at embedding row {emb_row}.")
    return emb_row

def remove_result_from_index(result_id: str):
    """
    Removes entries for a given result_id from image_hashes and triggers a clean rebuild of the index.
    """
    conn = get_connection()
    conn.execute("DELETE FROM image_hashes WHERE result_id = ?", (result_id,))
    conn.commit()
    conn.close()
    rebuild_duplicate_index()

def rebuild_duplicate_index():
    """
    Rebuilds FAISS/NumPy index completely from the image_hashes table and existing files.
    """
    global _FAISS_INDEX, _NUMPY_VECTORS, _NUMPY_META
    logger.info("Rebuilding duplicate index from SQLite image_hashes...")

    # Clear memory and disk index
    try:
        import faiss
        _FAISS_INDEX = faiss.IndexFlatIP(512)
    except Exception:
        _FAISS_INDEX = None
    _NUMPY_VECTORS = np.zeros((0, 512), dtype=np.float32)
    _NUMPY_META = []

    conn = get_connection()
    rows = conn.execute("SELECT * FROM image_hashes ORDER BY id ASC").fetchall()
    conn.close()

    updated_rows = []
    for r in rows:
        row = dict(r)
        fpath = row.get("file_path")
        if not fpath or not os.path.exists(fpath):
            continue
        try:
            with Image.open(fpath) as img:
                embed = compute_clip_embedding(img)
                phash_str = compute_phash(img)
                emb_idx = len(_NUMPY_META)
                if embed is not None:
                    if _FAISS_INDEX is not None:
                        _FAISS_INDEX.add(np.array([embed], dtype=np.float32))
                    else:
                        if len(_NUMPY_VECTORS) == 0:
                            _NUMPY_VECTORS = np.array([embed], dtype=np.float32)
                        else:
                            _NUMPY_VECTORS = np.vstack([_NUMPY_VECTORS, embed])
                _NUMPY_META.append({
                    "claim_id": row.get("claim_id"),
                    "claimant_id": row.get("claimant_id"),
                    "result_id": row.get("result_id"),
                    "slot": row.get("slot"),
                    "phash": phash_str,
                    "embedding_row": emb_idx,
                    "thumbnail_path": row.get("thumbnail_path")
                })
                updated_rows.append((emb_idx, phash_str, row["id"]))
        except Exception as e:
            logger.warning(f"Error reading {fpath} during rebuild: {e}")

    # Update SQLite rows with new embedding_rows
    conn = get_connection()
    for emb_idx, phash_str, row_id in updated_rows:
        conn.execute("UPDATE image_hashes SET embedding_row = ?, phash = ? WHERE id = ?", (emb_idx, phash_str, row_id))
    conn.commit()
    conn.close()

    _save_index()
    logger.info(f"Rebuilt duplicate index with {len(_NUMPY_META)} items.")

def get_index_stats() -> Dict[str, Any]:
    """Returns current index and hash counts and engine type."""
    _init_index()
    conn = get_connection()
    c = conn.cursor()
    total_hashes = c.execute("SELECT COUNT(*) FROM image_hashes").fetchone()[0]
    conn.close()
    return {
        "total_hashes": total_hashes,
        "indexed_vectors": len(_NUMPY_META),
        "engine": "faiss" if _FAISS_INDEX is not None else "numpy"
    }
