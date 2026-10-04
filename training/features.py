"""Extracts standardized word-level forensic features for the anomaly detector (§11.1 Step 9, §17.7).

Shared feature extractor: height, width, aspect, baseline offset, char spacing,
stroke width (distance transform), ink intensity, OCR conf, font size, and font id.
Features are z-scored within the page.
"""

from typing import List, Dict, Any, Tuple
import cv2
import numpy as np

FEATURE_NAMES = [
    "height",
    "width",
    "aspect",
    "baseline_offset",
    "char_spacing",
    "stroke_width",
    "ink_intensity",
    "ocr_conf",
    "font_size",
    "font_id",
]


def extract_word_features(
    image: np.ndarray,
    words: List[Dict[str, Any]]
) -> Tuple[np.ndarray, List[str]]:
    """Extracts 10 forensic features per word and z-scores them across the page.

    Args:
        image: Page image as numpy array (H, W, 3) or (H, W).
        words: List of word dicts containing:
               - "bbox": [x, y, w, h] in pixels
               - "text": str
               - "conf": float (0.0 - 1.0)
               - "font_size": optional float
               - "font_name": optional str

    Returns:
        (z_scored_features_matrix, FEATURE_NAMES)
        Matrix shape: (num_words, 10)
    """
    n_words = len(words)
    if n_words == 0:
        return np.empty((0, len(FEATURE_NAMES)), dtype=np.float32), FEATURE_NAMES

    # Ensure grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    img_h, img_w = gray.shape[:2]

    # Pre-calculate line groupings to compute line-level medians
    # Approximate line index by clustering Y midpoints within 15 pixels
    line_y_centers = []
    for w in words:
        bbox = w.get("bbox", [0, 0, 10, 10])
        y, h = bbox[1], bbox[3]
        line_y_centers.append(y + h / 2.0)

    # Compute baseline and char width medians per word
    raw_feats = np.zeros((n_words, len(FEATURE_NAMES)), dtype=np.float32)

    for i, w in enumerate(words):
        bbox = w.get("bbox", [0, 0, 10, 10])
        bx = max(0, min(int(bbox[0]), img_w - 1))
        by = max(0, min(int(bbox[1]), img_h - 1))
        bw = max(1, min(int(bbox[2]), img_w - bx))
        bh = max(1, min(int(bbox[3]), img_h - by))

        text = str(w.get("text", ""))
        text_len = max(len(text), 1)
        conf = float(w.get("conf", 1.0))
        font_size = float(w.get("font_size", bh * 0.85))
        font_name = str(w.get("font_name", "default"))
        font_id = float(abs(hash(font_name)) % 100) / 10.0

        # Geometry
        aspect = bw / float(bh)
        baseline = by + bh

        # Find nearby words on the same approximate text line (within +/- 15px)
        same_line_indices = [
            j for j, yc in enumerate(line_y_centers)
            if abs(yc - line_y_centers[i]) <= 15.0
        ]
        if same_line_indices:
            line_baselines = [words[j].get("bbox", [0, 0, 10, 10])[1] + words[j].get("bbox", [0, 0, 10, 10])[3] for j in same_line_indices]
            line_char_widths = [words[j].get("bbox", [0, 0, 10, 10])[2] / max(len(str(words[j].get("text", ""))), 1) for j in same_line_indices]
            line_median_baseline = float(np.median(line_baselines))
            line_median_char_width = float(np.median(line_char_widths))
        else:
            line_median_baseline = float(baseline)
            line_median_char_width = float(bw / text_len)

        baseline_offset = baseline - line_median_baseline
        char_spacing = (bw / text_len) - line_median_char_width

        # Crop word region for ink and stroke analysis
        crop = gray[by:by+bh, bx:bx+bw]
        ink_intensity = float(255.0 - np.mean(crop)) if crop.size > 0 else 0.0

        # Stroke width via distance transform of binarized crop
        if crop.size >= 9:
            # Otsu thresholding
            _, bin_crop = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            ink_pixels = bin_crop > 0
            if np.sum(ink_pixels) > 0:
                dist = cv2.distanceTransform(bin_crop, cv2.DIST_L2, 5)
                stroke_width = float(np.mean(dist[ink_pixels]) * 2.0)
            else:
                stroke_width = 1.0
        else:
            stroke_width = 1.0

        raw_feats[i, 0] = float(bh)
        raw_feats[i, 1] = float(bw)
        raw_feats[i, 2] = float(aspect)
        raw_feats[i, 3] = float(baseline_offset)
        raw_feats[i, 4] = float(char_spacing)
        raw_feats[i, 5] = float(stroke_width)
        raw_feats[i, 6] = float(ink_intensity)
        raw_feats[i, 7] = float(conf)
        raw_feats[i, 8] = float(font_size)
        raw_feats[i, 9] = float(font_id)

    # Within-page Z-score standardization (§11.1 Step 9)
    if n_words > 1:
        mean = np.mean(raw_feats, axis=0, keepdims=True)
        std = np.std(raw_feats, axis=0, keepdims=True)
        z_scored = (raw_feats - mean) / (std + 1e-6)
    else:
        z_scored = np.zeros_like(raw_feats)

    return z_scored.astype(np.float32), FEATURE_NAMES
