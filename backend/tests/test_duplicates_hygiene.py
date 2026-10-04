import pytest
import sqlite3
import asyncio
import uuid
from backend.app.services.orchestrator import _execute_analysis_job
import backend.app.detectors.image.duplicates as dups

@pytest.mark.asyncio
async def test_synthetic_history_leaves_index_unchanged():
    dups._init_index()
    initial_count = len(dups._NUMPY_VECTORS) if dups._NUMPY_VECTORS is not None else (dups._FAISS_INDEX.ntotal if dups._FAISS_INDEX else 0)
    
    job_id = str(uuid.uuid4())
    input_data = {"images": ["web/public/samples/genuine_car.jpg"], "metadata": {"data_source": "synthetic_history", "claim_id": "test_syn_123"}}
    
    await _execute_analysis_job(job_id, "image", input_data)
    
    final_count = len(dups._NUMPY_VECTORS) if dups._NUMPY_VECTORS is not None else (dups._FAISS_INDEX.ntotal if dups._FAISS_INDEX else 0)
    assert final_count == initial_count, "Synthetic history should not change duplicate index"

@pytest.mark.asyncio
async def test_skip_index_leaves_index_unchanged():
    dups._init_index()
    initial_count = len(dups._NUMPY_VECTORS) if dups._NUMPY_VECTORS is not None else (dups._FAISS_INDEX.ntotal if dups._FAISS_INDEX else 0)
    
    job_id = str(uuid.uuid4())
    input_data = {"images": ["web/public/samples/ai_car.jpg"], "metadata": {"index": False, "claim_id": "test_idx_123"}}
    
    await _execute_analysis_job(job_id, "image", input_data)
    
    final_count = len(dups._NUMPY_VECTORS) if dups._NUMPY_VECTORS is not None else (dups._FAISS_INDEX.ntotal if dups._FAISS_INDEX else 0)
    assert final_count == initial_count, "index=False should not change duplicate index"
