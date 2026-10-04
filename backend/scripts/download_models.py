import os
import sys
import hashlib
import logging
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MODELS_ROOT = os.path.join(REPO_ROOT, "models")
AI_DETECTOR_DIR = os.path.join(MODELS_ROOT, "ai_detector")

MODEL_ID = "Ateeqq/ai-vs-human-image-detector"

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
LANDMARKER_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

def compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()

def download_file(url: str, dest_path: str, description: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        logger.info(f"{description} already exists at '{dest_path}' ({os.path.getsize(dest_path)} bytes). Skipping download.")
        return True
    
    logger.info(f"Downloading {description} from {url} to {dest_path}...")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_path = dest_path + ".tmp"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=60) as response, open(temp_path, "wb") as out_file:
            data = response.read()
            out_file.write(data)
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(temp_path, dest_path)
        sha = compute_sha256(dest_path)
        logger.info(f"{description} downloaded successfully. Size: {os.path.getsize(dest_path)} bytes | SHA256: {sha}")
        return True
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        logger.error(f"Failed to download {description} from {url}: {e}")
        print(f"[MANUAL ACTION REQUIRED] Could not automatically download {description}.")
        print(f"Please download it from: {url}")
        print(f"And place it at: {dest_path}")
        return False

def download_ai_detector():
    if os.path.exists(AI_DETECTOR_DIR) and len(os.listdir(AI_DETECTOR_DIR)) >= 2:
        logger.info(f"AI detector already present in '{AI_DETECTOR_DIR}'. Skipping.")
        return
    logger.info(f"Downloading model '{MODEL_ID}' to '{AI_DETECTOR_DIR}'...")
    try:
        from transformers import AutoModelForImageClassification, AutoImageProcessor
        os.makedirs(AI_DETECTOR_DIR, exist_ok=True)
        processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        processor.save_pretrained(AI_DETECTOR_DIR)
        model = AutoModelForImageClassification.from_pretrained(MODEL_ID)
        model.save_pretrained(AI_DETECTOR_DIR)
        logger.info("AI Detector saved successfully.")
    except Exception as e:
        logger.error(f"Failed to download AI detector: {e}")

def download_buffalo_l():
    try:
        import insightface
        from insightface.app import FaceAnalysis
        logger.info("Attempting to initialize InsightFace FaceAnalysis('buffalo_l')...")
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace buffalo_l models ready.")
    except Exception as e:
        logger.warning(f"InsightFace buffalo_l download/init skipped or failed: {e}")
        print(f"[NOTE] InsightFace buffalo_l could not be loaded automatically ({e}).")
        print("SFace (OpenCV YuNet + SFace) will be used as the primary face engine.")

def download():
    os.makedirs(MODELS_ROOT, exist_ok=True)
    
    # 1. Image AI detector
    download_ai_detector()
    
    # 2. YuNet face detector
    yunet_path = os.path.join(MODELS_ROOT, "face_detection_yunet_2023mar.onnx")
    download_file(YUNET_URL, yunet_path, "YuNet Face Detector")

    # 3. SFace face recognizer
    sface_path = os.path.join(MODELS_ROOT, "face_recognition_sface_2021dec.onnx")
    download_file(SFACE_URL, sface_path, "SFace Face Recognizer")

    # 4. MediaPipe Face Landmarker
    landmarker_path = os.path.join(MODELS_ROOT, "face_landmarker.task")
    download_file(LANDMARKER_URL, landmarker_path, "MediaPipe Face Landmarker")

    # 5. Optional InsightFace buffalo_l
    download_buffalo_l()

    logger.info("Model download and verification complete.")

if __name__ == "__main__":
    download()
