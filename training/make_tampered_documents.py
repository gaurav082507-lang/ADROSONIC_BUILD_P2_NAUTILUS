"""Generates tampered synthetic insurance documents with pixel masks and JSON records.

Tamper Recipes:
1. digit_replacement: whiten number, redraw with different/matching font.
2. overlay_text: paste new text box over original.
3. inpaint_retype: cv2.inpaint region, type new text.
4. copy_move: duplicate stamp, signature or table block.
5. splice: paste region from a different document (HELD OUT RECIPE).
6. style_change: change font weight/color of one field.
7. logic_edit: alter totals so rules fail (sum mismatch, word mismatch).

Plus Hard Negatives (clean variations with empty masks).
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Add local path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from indian_numbers import format_inr, number_to_inr_words

RECIPES = [
    "digit_replacement",
    "overlay_text",
    "inpaint_retype",
    "copy_move",
    "splice",          # HELD OUT
    "style_change",
    "logic_edit"
]
HELD_OUT_RECIPE = "splice"


def _get_pil_font(size: int = 18, variant: str = "normal"):
    # Standard system fonts or fallbacks
    try:
        if variant == "bold":
            return ImageFont.truetype("arialbd.ttf", size)
        elif variant == "times":
            return ImageFont.truetype("times.ttf", size)
        elif variant == "courier":
            return ImageFont.truetype("cour.ttf", size)
        return ImageFont.truetype("arial.ttf", size)
    except IOError:
        return ImageFont.load_default()


def apply_tamper_recipe(clean_img: np.ndarray, clean_meta: dict, recipe: str, seed: int, other_img: np.ndarray = None):
    random.seed(seed)
    np.random.seed(seed)

    h, w = clean_img.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    tampered_img = clean_img.copy()

    fields = clean_meta.get("fields", {})
    record = {
        "recipe": recipe,
        "held_out": (recipe == HELD_OUT_RECIPE),
        "before_text": "",
        "after_text": "",
        "region": {},
        "normalized_bbox": []
    }

    # Default search region for monetary totals: lower half of page, right side
    # At 150 DPI A4 is ~1240 x 1754 px
    total_val = fields.get("total_amount", 50000.0)
    new_val = round(total_val * random.uniform(1.8, 3.5), 2)
    before_str = format_inr(total_val)
    after_str = format_inr(new_val)

    if recipe == "digit_replacement":
        # Target amount box near bottom right
        rx = int(w * 0.72)
        ry = int(h * 0.42 + random.uniform(0, 0.15) * h)
        rw = int(w * 0.20)
        rh = int(h * 0.035)

        # Whiten original box
        tampered_img[ry:ry+rh, rx:rx+rw] = 255
        mask[ry:ry+rh, rx:rx+rw] = 255

        # Redraw changed digits with slightly different font
        pil_img = Image.fromarray(cv2.cvtColor(tampered_img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = _get_pil_font(size=18, variant="courier" if seed % 2 == 0 else "bold")
        draw.text((rx + 5, ry + 3), after_str, fill=(20, 20, 20), font=font)

        tampered_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        record["before_text"] = before_str
        record["after_text"] = after_str
        record["region"] = {"x": rx, "y": ry, "w": rw, "h": rh}
        record["normalized_bbox"] = [round(rx / w, 4), round(ry / h, 4), round(rw / w, 4), round(rh / h, 4)]

    elif recipe == "overlay_text":
        rx = int(w * 0.65)
        ry = int(h * 0.45)
        rw = int(w * 0.25)
        rh = int(h * 0.04)

        overlay_val = f"INR {format_inr(new_val)}"
        pil_img = Image.fromarray(cv2.cvtColor(tampered_img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        # Draw opaque white background box
        draw.rectangle([rx, ry, rx + rw, ry + rh], fill=(255, 255, 255), outline=(150, 150, 150))
        font = _get_pil_font(size=19, variant="times")
        draw.text((rx + 6, ry + 4), overlay_val, fill=(0, 0, 0), font=font)

        tampered_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        mask[ry:ry+rh, rx:rx+rw] = 255
        record["before_text"] = before_str
        record["after_text"] = overlay_val
        record["region"] = {"x": rx, "y": ry, "w": rw, "h": rh}
        record["normalized_bbox"] = [round(rx / w, 4), round(ry / h, 4), round(rw / w, 4), round(rh / h, 4)]

    elif recipe == "inpaint_retype":
        rx = int(w * 0.70)
        ry = int(h * 0.40 + random.uniform(0, 0.1) * h)
        rw = int(w * 0.22)
        rh = int(h * 0.035)

        inpaint_mask = np.zeros((h, w), dtype=np.uint8)
        inpaint_mask[ry:ry+rh, rx:rx+rw] = 255
        tampered_img = cv2.inpaint(clean_img, inpaint_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        pil_img = Image.fromarray(cv2.cvtColor(tampered_img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = _get_pil_font(size=18, variant="normal")
        draw.text((rx + 5, ry + 2), after_str, fill=(35, 35, 35), font=font)

        tampered_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        mask[ry:ry+rh, rx:rx+rw] = 255
        record["before_text"] = before_str
        record["after_text"] = after_str
        record["region"] = {"x": rx, "y": ry, "w": rw, "h": rh}
        record["normalized_bbox"] = [round(rx / w, 4), round(ry / h, 4), round(rw / w, 4), round(rh / h, 4)]

    elif recipe == "copy_move":
        # Copy a region from another part of document (e.g. line item or number box)
        src_x = int(w * 0.60)
        src_y = int(h * 0.30)
        box_w = int(w * 0.25)
        box_h = int(h * 0.04)

        dst_x = int(w * 0.60)
        dst_y = int(h * 0.55)

        patch = clean_img[src_y:src_y+box_h, src_x:src_x+box_w]
        tampered_img[dst_y:dst_y+box_h, dst_x:dst_x+box_w] = patch
        mask[dst_y:dst_y+box_h, dst_x:dst_x+box_w] = 255

        record["before_text"] = "original_background"
        record["after_text"] = "cloned_patch"
        record["region"] = {"x": dst_x, "y": dst_y, "w": box_w, "h": box_h}
        record["normalized_bbox"] = [round(dst_x / w, 4), round(dst_y / h, 4), round(box_w / w, 4), round(box_h / h, 4)]

    elif recipe == "splice":
        # Held out recipe: paste a patch from a different document
        box_w = int(w * 0.28)
        box_h = int(h * 0.05)
        dst_x = int(w * 0.62)
        dst_y = int(h * 0.44)

        if other_img is not None:
            oh, ow = other_img.shape[:2]
            src_x = min(int(ow * 0.5), ow - box_w)
            src_y = min(int(oh * 0.3), oh - box_h)
            patch = other_img[src_y:src_y+box_h, src_x:src_x+box_w]
        else:
            # Synthetic external patch
            patch = np.full((box_h, box_w, 3), 245, dtype=np.uint8)
            cv2.putText(patch, "VERIFIED AUTH", (10, box_h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 0, 0), 2)

        tampered_img[dst_y:dst_y+box_h, dst_x:dst_x+box_w] = patch
        mask[dst_y:dst_y+box_h, dst_x:dst_x+box_w] = 255

        record["before_text"] = "original_content"
        record["after_text"] = "spliced_foreign_block"
        record["region"] = {"x": dst_x, "y": dst_y, "w": box_w, "h": box_h}
        record["normalized_bbox"] = [round(dst_x / w, 4), round(dst_y / h, 4), round(box_w / w, 4), round(box_h / h, 4)]

    elif recipe == "style_change":
        # Change font styling / color of a specific field
        rx = int(w * 0.70)
        ry = int(h * 0.42)
        rw = int(w * 0.22)
        rh = int(h * 0.035)

        tampered_img[ry:ry+rh, rx:rx+rw] = 255
        mask[ry:ry+rh, rx:rx+rw] = 255

        pil_img = Image.fromarray(cv2.cvtColor(tampered_img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = _get_pil_font(size=22, variant="bold")  # noticeable size/weight change
        draw.text((rx + 4, ry + 1), before_str, fill=(180, 0, 0), font=font)  # Red color inconsistency

        tampered_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        record["before_text"] = before_str
        record["after_text"] = before_str + " (bold_red)"
        record["region"] = {"x": rx, "y": ry, "w": rw, "h": rh}
        record["normalized_bbox"] = [round(rx / w, 4), round(ry / h, 4), round(rw / w, 4), round(rh / h, 4)]

    elif recipe == "logic_edit":
        # Alter digits so math rule (DOC-LOGIC-01) breaks
        rx = int(w * 0.72)
        ry = int(h * 0.43)
        rw = int(w * 0.22)
        rh = int(h * 0.035)

        tampered_img[ry:ry+rh, rx:rx+rw] = 255
        mask[ry:ry+rh, rx:rx+rw] = 255

        pil_img = Image.fromarray(cv2.cvtColor(tampered_img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        font = _get_pil_font(size=18, variant="normal")
        draw.text((rx + 5, ry + 3), after_str, fill=(25, 25, 25), font=font)

        tampered_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        record["before_text"] = before_str
        record["after_text"] = after_str
        record["region"] = {"x": rx, "y": ry, "w": rw, "h": rh}
        record["normalized_bbox"] = [round(rx / w, 4), round(ry / h, 4), round(rw / w, 4), round(rh / h, 4)]

    return tampered_img, mask, record


def generate_tampered_dataset(clean_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    clean_files = sorted(list(clean_dir.glob("*.json")))

    if not clean_files:
        print("No clean documents found in", clean_dir)
        return []

    print(f"Creating tampered versions for {len(clean_files)} documents...")
    records = []

    # Preload clean images for cross-document splicing
    clean_images = []
    for f in clean_files[:10]:
        img_p = f.with_suffix(".png")
        if img_p.exists():
            clean_images.append(cv2.imread(str(img_p)))

    for i, json_path in enumerate(clean_files):
        with open(json_path, "r", encoding="utf-8") as f:
            clean_meta = json.load(f)

        clean_png_path = json_path.with_suffix(".png")
        if not clean_png_path.exists():
            continue

        clean_img = cv2.imread(str(clean_png_path))
        if clean_img is None:
            continue

        recipe = RECIPES[i % len(RECIPES)]
        sample_id = f"tampered_{i:04d}_{recipe}"

        other_img = clean_images[(i + 1) % len(clean_images)] if clean_images else None
        tampered_img, mask, record = apply_tamper_recipe(
            clean_img, clean_meta, recipe, seed=2000 + i, other_img=other_img
        )

        tampered_png_path = out_dir / f"{sample_id}.png"
        mask_png_path = out_dir / f"{sample_id}_mask.png"
        meta_json_path = out_dir / f"{sample_id}.json"

        cv2.imwrite(str(tampered_png_path), tampered_img)
        cv2.imwrite(str(mask_png_path), mask)

        record["sample_id"] = sample_id
        record["clean_id"] = clean_meta["sample_id"]
        record["template"] = clean_meta["template"]
        record["split"] = clean_meta["split"]
        record["png_path"] = str(tampered_png_path)
        record["mask_path"] = str(mask_png_path)
        record["json_path"] = str(meta_json_path)

        with open(meta_json_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        records.append(record)

    recipe_counts = {}
    for r in records:
        recipe_counts[r["recipe"]] = recipe_counts.get(r["recipe"], 0) + 1
    print(f"Generated {len(records)} tampered documents: {recipe_counts}")
    print(f"Held out recipe '{HELD_OUT_RECIPE}': {sum(1 for r in records if r['held_out'])} samples.")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-dir", default="data/training/clean", help="Path to clean documents")
    parser.add_argument("--out-dir", default="data/training/tampered", help="Path for tampered outputs")
    args = parser.parse_args()

    generate_tampered_dataset(Path(args.clean_dir), Path(args.out_dir))
