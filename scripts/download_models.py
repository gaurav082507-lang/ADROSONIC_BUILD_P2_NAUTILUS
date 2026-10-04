"""
Lucen AI - Model Download Script
Downloads offline models including CLIP and Face models.
"""
import os
import sys
from pathlib import Path

# Force UTF-8 on Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def download_models():
    print("[1/2] Downloading CLIP model: openai/clip-vit-base-patch32...")
    try:
        from transformers import CLIPProcessor, CLIPModel
        model_id = "openai/clip-vit-base-patch32"
        CLIPProcessor.from_pretrained(model_id)
        CLIPModel.from_pretrained(model_id)
        print("[OK] CLIP model downloaded successfully.")
    except Exception as e:
        print(f"[FAIL] Failed to download CLIP model: {e}")
        print("Please ensure internet access or place openai/clip-vit-base-patch32 into HuggingFace cache.")

    print("\n[2/2] Checking SFace / Face models...")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    yunet_path = models_dir / "face_detection_yunet_2023mar.onnx"
    sface_path = models_dir / "face_recognition_sface_2021dec.onnx"
    
    import urllib.request
    if not yunet_path.exists():
        try:
            url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
            print(f"Downloading YuNet to {yunet_path}...")
            urllib.request.urlretrieve(url, yunet_path)
            print("[OK] YuNet downloaded.")
        except Exception as e:
            print(f"[FAIL] Could not download YuNet: {e}")
            print(f"Place face_detection_yunet_2023mar.onnx in {yunet_path.resolve()}")
    else:
        print("[OK] YuNet already present.")

    if not sface_path.exists():
        try:
            url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
            print(f"Downloading SFace to {sface_path}...")
            urllib.request.urlretrieve(url, sface_path)
            print("[OK] SFace downloaded.")
        except Exception as e:
            print(f"[FAIL] Could not download SFace: {e}")
            print(f"Place face_recognition_sface_2021dec.onnx in {sface_path.resolve()}")
    else:
        print("[OK] SFace already present.")

    print("\n[3/3] Downloading synthetic voice detector: mo-thecreator/Deepfake-audio-detection...")
    try:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        voice_model_id = "mo-thecreator/Deepfake-audio-detection"
        AutoFeatureExtractor.from_pretrained(voice_model_id)
        AutoModelForAudioClassification.from_pretrained(voice_model_id)
        print("[OK] Synthetic voice detector downloaded successfully.")
    except Exception as e:
        print(f"[FAIL] Could not download voice model: {e}")

if __name__ == "__main__":
    download_models()

