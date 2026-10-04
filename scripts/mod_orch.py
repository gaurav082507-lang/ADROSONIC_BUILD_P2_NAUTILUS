with open('backend/app/services/orchestrator.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = """        try:
            from backend.app.detectors.image.duplicates import index_image
            cid = meta.get("claim_id")"""

replacement = """        try:
            skip_idx = meta.get("index") is False or meta.get("data_source") == "synthetic_history"
            if skip_idx:
                pass # skip
            else:
                from backend.app.detectors.image.duplicates import index_image
                cid = meta.get("claim_id")"""

target2 = """            for idx, img_p in enumerate(images_list):
                slot_name = f"img_{idx + 1}" if (mode == "claim" or len(images_list) > 1) else "image"
                thumb_path = os.path.join(result_artifacts_dir, f"preview_img_{idx + 1}.jpg")
                index_image(
                    image_path=img_p,
                    claim_id=cid,
                    claimant_id=uid,
                    result_id=res_id,
                    slot=slot_name,
                    thumbnail_path=thumb_path if os.path.exists(thumb_path) else None
                )"""

replacement2 = """                for idx, img_p in enumerate(images_list):
                    slot_name = f"img_{idx + 1}" if (mode == "claim" or len(images_list) > 1) else "image"
                    thumb_path = os.path.join(result_artifacts_dir, f"preview_img_{idx + 1}.jpg")
                    index_image(
                        image_path=img_p,
                        claim_id=cid,
                        claimant_id=uid,
                        result_id=res_id,
                        slot=slot_name,
                        thumbnail_path=thumb_path if os.path.exists(thumb_path) else None
                    )"""

text = text.replace(target, replacement).replace(target2, replacement2)

with open('backend/app/services/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(text)
