import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("lucen_ai.models")

LOCAL_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../models/ai_detector")
)
FALLBACK_MODEL_ID = "Ateeqq/ai-vs-human-image-detector"
TAMPER_CNN_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../models/tamper_cnn.pt")
)
ANOMALY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../models/anomaly.joblib")
)


class ModelRegistry:
    def __init__(self):
        self.models: Dict[str, bool] = {
            "ai_detector": False,
            "tamper_cnn": False,
            "anomaly": False,
            "ocr": False,
            "face_engine": False,
        }
        self.ai_model: Optional[Any] = None
        self.ai_processor: Optional[Any] = None
        self.ai_class_idx: int = 0
        self.ai_class_label: str = "ai"

        self.tamper_cnn: Optional[Any] = None
        self.tamper_cnn_temp: float = 2.0
        self.anomaly_model: Optional[Any] = None
        self.ocr_engine: Optional[Any] = None

        self.face_engine_name: str = "sface"
        self.yunet_detector: Optional[Any] = None
        self.sface_recognizer: Optional[Any] = None
        self.arcface_app: Optional[Any] = None

    def load_all(self):
        self.load_ai_detector()
        self.load_tamper_cnn()
        self.load_anomaly_model()
        self.load_ocr()
        self.load_face_engine()

    def load_ai_detector(self):
        """Loads Ateeqq/ai-vs-human-image-detector once into memory."""
        import os
        if os.environ.get("LITE_MODE") == "1":
            logger.info("LITE_MODE=1: Skipping AI Detector loading to save memory.")
            self.models["ai_detector"] = False
            return
            
        try:
            from transformers import AutoModelForImageClassification, AutoImageProcessor

            model_path = LOCAL_MODEL_DIR if os.path.isdir(LOCAL_MODEL_DIR) else FALLBACK_MODEL_ID
            logger.info(f"Loading AI Detector from {model_path}...")

            self.ai_processor = AutoImageProcessor.from_pretrained(model_path)
            self.ai_model = AutoModelForImageClassification.from_pretrained(model_path)
            self.ai_model.eval()

            # Programmatically map the AI-generated class (never hardcode label strings)
            id2label = getattr(self.ai_model.config, "id2label", {0: "ai", 1: "hum"})
            logger.info(f"AI Detector labels detected: {id2label}")

            ai_keywords = ("ai", "fake", "synthetic", "generated", "artificial")
            matched_idx = None
            matched_lbl = None

            for idx, label in id2label.items():
                lbl_lower = str(label).lower().strip()
                if any(kw == lbl_lower or lbl_lower.startswith(kw) for kw in ai_keywords):
                    matched_idx = int(idx)
                    matched_lbl = str(label)
                    break

            if matched_idx is not None:
                self.ai_class_idx = matched_idx
                self.ai_class_label = matched_lbl
            else:
                logger.warning("Could not automatically map AI class from id2label; defaulting to index 0.")
                self.ai_class_idx = 0
                self.ai_class_label = str(id2label.get(0, "ai"))

            logger.info(f"AI class mapped to index {self.ai_class_idx} (label='{self.ai_class_label}')")
            self.models["ai_detector"] = True

        except Exception as e:
            logger.error(f"Failed to load AI detector model: {e}", exc_info=True)
            self.models["ai_detector"] = False
            self.ai_model = None
            self.ai_processor = None

    def load_tamper_cnn(self):
        """Loads trained PyTorch EfficientNet-B0 Tamper CNN weights."""
        import os
        if os.environ.get("LITE_MODE") == "1":
            logger.info("LITE_MODE=1: Skipping Tamper CNN loading to save memory.")
            self.models["tamper_cnn"] = False
            return
            
        try:
            import torch
            import timm

            if not os.path.exists(TAMPER_CNN_PATH):
                logger.warning(f"Tamper CNN weights not found at {TAMPER_CNN_PATH}")
                self.models["tamper_cnn"] = False
                return

            logger.info(f"Loading Tamper CNN from {TAMPER_CNN_PATH}...")
            ckpt = torch.load(TAMPER_CNN_PATH, map_location="cpu")
            m = timm.create_model("efficientnet_b0", pretrained=False, num_classes=1)
            m.load_state_dict(ckpt["state_dict"])
            m.eval()

            self.tamper_cnn = m
            self.tamper_cnn_temp = float(ckpt.get("temperature", 2.0))
            self.models["tamper_cnn"] = True
            logger.info(f"Tamper CNN loaded successfully (temperature={self.tamper_cnn_temp:.2f}).")
        except Exception as e:
            logger.error(f"Failed to load Tamper CNN: {e}", exc_info=True)
            self.models["tamper_cnn"] = False
            self.tamper_cnn = None

    def load_anomaly_model(self):
        """Loads word-level Isolation Forest anomaly detector."""
        try:
            import joblib

            if not os.path.exists(ANOMALY_PATH):
                logger.warning(f"Anomaly model not found at {ANOMALY_PATH}")
                self.models["anomaly"] = False
                return

            logger.info(f"Loading Anomaly model from {ANOMALY_PATH}...")
            data = joblib.load(ANOMALY_PATH)
            self.anomaly_model = data.get("model") if isinstance(data, dict) else data
            self.models["anomaly"] = True
            logger.info("Anomaly Isolation Forest loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Anomaly model: {e}", exc_info=True)
            self.models["anomaly"] = False
            self.anomaly_model = None

    def load_ocr(self):
        """Initializes RapidOCR ONNX engine."""
        import os
        if os.environ.get("LITE_MODE") == "1":
            logger.info("LITE_MODE=1: Skipping RapidOCR loading to save memory.")
            self.models["ocr"] = False
            return
            
        try:
            from rapidocr_onnxruntime import RapidOCR
            logger.info("Initializing RapidOCR engine...")
            self.ocr_engine = RapidOCR()
            self.models["ocr"] = True
            logger.info("RapidOCR initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR: {e}", exc_info=True)
            self.models["ocr"] = False
            self.ocr_engine = None

    def load_face_engine(self):
        """Loads SFace (OpenCV YuNet + SFace) or ArcFace (InsightFace buffalo_l)."""
        import os
        if os.environ.get("LITE_MODE") == "1":
            logger.info("LITE_MODE=1: Skipping Face Engine loading to save memory.")
            self.models["face_engine"] = False
            return
            
        from backend.app.core.config import settings
        self.face_engine_name = settings.FACE_ENGINE
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        yunet_full = os.path.join(repo_root, settings.FACE_YUNET_PATH)
        sface_full = os.path.join(repo_root, settings.FACE_SFACE_PATH)

        if self.face_engine_name == "arcface":
            try:
                import insightface
                from insightface.app import FaceAnalysis
                logger.info("Loading InsightFace buffalo_l FaceAnalysis...")
                app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
                app.prepare(ctx_id=0, det_size=(640, 640))
                self.arcface_app = app
                self.models["face_engine"] = True
                logger.info("ArcFace engine loaded successfully.")
                return
            except Exception as e:
                logger.warning(f"Failed to load ArcFace engine: {e}. Falling back to SFace.")
                self.face_engine_name = "sface"

        # Load SFace
        try:
            import cv2
            if not os.path.exists(yunet_full) or not os.path.exists(sface_full):
                logger.warning(f"YuNet or SFace weights not found at {yunet_full} or {sface_full}")
                self.models["face_engine"] = False
                return
            logger.info("Loading OpenCV YuNet FaceDetector and SFace FaceRecognizer...")
            self.yunet_detector = cv2.FaceDetectorYN.create(yunet_full, "", (320, 320), 0.6, 0.3, 5000)
            self.sface_recognizer = cv2.FaceRecognizerSF.create(sface_full, "")
            self.models["face_engine"] = True
            logger.info("SFace engine loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SFace engine: {e}", exc_info=True)
            self.models["face_engine"] = False


model_registry = ModelRegistry()
