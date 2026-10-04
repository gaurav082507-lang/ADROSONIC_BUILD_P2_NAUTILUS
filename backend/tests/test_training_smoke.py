"""Smoke tests for synthetic document generation and feature parity (§17, Part 5).

Verifies:
1. Quick synthetic document generation generates valid images, masks, and metadata JSON.
2. Binary mask values are strictly 0 or 255.
3. Feature extraction parity between training/features.py and backend app/detectors/document/word_features.py.
"""

import sys
from pathlib import Path
import cv2
import numpy as np
import pytest

# Ensure root is in path for training package imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from training.make_clean_documents import generate_clean_document, TEMPLATE_SPLITS
from training.make_tampered_documents import generate_tampered_dataset
from training.features import extract_word_features as train_extract_features, FEATURE_NAMES as TRAIN_FEAT_NAMES
from app.detectors.document.word_features import extract_word_features as backend_extract_features, FEATURE_NAMES as BACKEND_FEAT_NAMES


def test_quick_data_generation_and_binary_masks(tmp_path):
    clean_dir = tmp_path / "clean"
    tampered_dir = tmp_path / "tampered"
    clean_dir.mkdir(parents=True, exist_ok=True)
    tampered_dir.mkdir(parents=True, exist_ok=True)

    templates = list(TEMPLATE_SPLITS.keys())[:5]

    # Generate 5 clean documents
    for i, tmpl in enumerate(templates):
        generate_clean_document(tmpl, f"test_clean_{i:02d}", seed=5000 + i, out_dir=clean_dir)

    clean_pngs = list(clean_dir.glob("*.png"))
    assert len(clean_pngs) == 5, f"Expected 5 clean PNGs, found {len(clean_pngs)}"

    # Generate tampered documents from the 5 clean documents
    tampered_records = generate_tampered_dataset(clean_dir, tampered_dir)
    assert len(tampered_records) == 5

    mask_files = list(tampered_dir.glob("*_mask.png"))
    assert len(mask_files) == 5, f"Expected 5 mask PNGs, found {len(mask_files)}"

    for mask_path in mask_files:
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        assert mask is not None, f"Failed to load mask {mask_path}"
        unique_vals = set(np.unique(mask))
        # Mask must contain binary values (0 or 255)
        assert unique_vals.issubset({0, 255}), f"Mask {mask_path.name} contains non-binary values: {unique_vals}"

        # JSON record exists
        json_path = mask_path.parent / (mask_path.name.replace("_mask.png", ".json"))
        assert json_path.exists(), f"Missing metadata JSON for {mask_path.name}"


def test_feature_parity_between_training_and_backend():
    # 1. Assert feature names parity
    assert TRAIN_FEAT_NAMES == BACKEND_FEAT_NAMES

    # 2. Create mock page image (300 x 500 white background)
    img = np.ones((500, 300, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Tax Invoice 50000.00", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "Total Due 59000.00", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    words = [
        {"bbox": [20, 35, 45, 20], "text": "Tax", "conf": 0.95, "font_size": 12.0, "font_name": "Helvetica"},
        {"bbox": [70, 35, 80, 20], "text": "Invoice", "conf": 0.92, "font_size": 12.0, "font_name": "Helvetica"},
        {"bbox": [160, 35, 95, 20], "text": "50000.00", "conf": 0.88, "font_size": 12.0, "font_name": "Helvetica"},
        {"bbox": [20, 105, 55, 20], "text": "Total", "conf": 0.94, "font_size": 12.0, "font_name": "Helvetica"},
        {"bbox": [80, 105, 40, 20], "text": "Due", "conf": 0.91, "font_size": 12.0, "font_name": "Helvetica"},
        {"bbox": [130, 105, 95, 20], "text": "59000.00", "conf": 0.85, "font_size": 12.0, "font_name": "Times"},
    ]

    train_feats, train_names = train_extract_features(img, words)
    backend_feats, backend_names = backend_extract_features(img, words)

    assert train_names == backend_names
    assert train_feats.shape == backend_feats.shape
    assert np.allclose(train_feats, backend_feats, atol=1e-6), "Feature extraction mismatch between training and backend!"
