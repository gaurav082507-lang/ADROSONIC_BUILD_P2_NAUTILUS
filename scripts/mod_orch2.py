with open('backend/app/services/orchestrator.py', 'r', encoding='utf-8') as f:
    text = f.read()
target = """                from backend.app.detectors.image.duplicates import index_image
                cid = meta.get("claim_id") or (file_paths.get("claim_id") if isinstance(file_paths, dict) else None)
            uid = meta.get("claimant_user_id") or (file_paths.get("claimant_id") if isinstance(file_paths, dict) else None)
                for idx, img_p in enumerate(images_list):"""
replacement = """                from backend.app.detectors.image.duplicates import index_image
                cid = meta.get("claim_id") or (file_paths.get("claim_id") if isinstance(file_paths, dict) else None)
                uid = meta.get("claimant_user_id") or (file_paths.get("claimant_id") if isinstance(file_paths, dict) else None)
                for idx, img_p in enumerate(images_list):"""
text = text.replace(target, replacement)
with open('backend/app/services/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(text)
