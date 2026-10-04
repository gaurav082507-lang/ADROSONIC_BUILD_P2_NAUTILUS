import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, SecretStr


def mask_secret(secret: SecretStr | str | None) -> str:
    """Mask secret value showing only the last 4 characters."""
    if not secret:
        return "<none>"
    val = secret.get_secret_value() if isinstance(secret, SecretStr) else str(secret)
    if not val:
        return "<none>"
    if len(val) <= 4:
        return "****"
    return f"****{val[-4:]}"


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=("backend/.env", ".env"), extra="ignore")

    # Upload / processing limits
    MAX_UPLOAD_MB: int = 15
    MAX_PDF_PAGES: int = 10
    RETENTION_HOURS: int = 24
    MAX_CONCURRENT_JOBS: int = 2
    DETECTOR_TIMEOUT_S: int = 30
    JOB_TIMEOUT_S: int = 120
    RATE_LIMIT_PER_MINUTE: int = 20

    # Scoring thresholds
    BAND_LOW_MAX: float = 0.35
    BAND_MED_MAX: float = 0.65

    # Model paths
    IMAGE_MODEL_ID: str = "Ateeqq/ai-vs-human-image-detector"
    MODELS_DIR: str = "models/"
    OCR_ENGINE: str = "paddle"

    # LLM
    LLM_PROVIDER: str = ""
    LLM_API_KEY: str = ""
    LLM_ENABLED: bool = True

    # Mock mode
    MOCK_ANALYSIS: bool = False

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # Auth
    AUTH_SECRET: str = "supersecret"
    JWT_SECRET: str = ""
    AUTH_TOKEN_HOURS: int = 8

    def get_jwt_secret(self) -> str:
        if self.JWT_SECRET:
            return self.JWT_SECRET
        if not self.DEMO_MODE:
            raise RuntimeError("JWT_SECRET must be configured when DEMO_MODE=false")
        return self.AUTH_SECRET or "demo-secret-key-lucen-ai-jwt-hs256"

    # Entity hashing
    ENTITY_HASH_SALT: str = "salt"

    SQLITE_DB_PATH: str = os.environ.get('SQLITE_DB_PATH', os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')), 'data', 'runtime', 'lucen.db'))

    # Demo / feature flags
    DEMO_MODE: bool = True
    LAZY_LOAD_BONUS_MODELS: bool = True
    OCCLUSION_ENABLED: bool = False

    # v2: Voice / Bhashini
    BHASHINI_CONFIG_URL: str = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
    BHASHINI_USER_ID: SecretStr = SecretStr("")
    BHASHINI_UDYAT_KEY: SecretStr = SecretStr("")
    BHASHINI_INFERENCE_KEY: SecretStr = SecretStr("")
    BHASHINI_PIPELINE_ID: str = ""
    VOICE_MODEL_ID: str = ""
    MAX_AUDIO_SECONDS: int = 90
    MAX_AUDIO_MB: int = 10

    # v2: Identity / Liveness
    FACE_ENGINE: str = "sface"  # sface | arcface (default sface)
    FACE_YUNET_PATH: str = "models/face_detection_yunet_2023mar.onnx"
    FACE_SFACE_PATH: str = "models/face_recognition_sface_2021dec.onnx"
    MEDIAPIPE_LANDMARKER_PATH: str = "models/face_landmarker.task"
    LIVENESS_YAW_DEG: int = 15
    LIVENESS_SESSION_S: int = 120
    AADHAAR_QR_MODE: str = "demo_key"
    UIDAI_CERT_PATH: str = ""
    DEMO_QR_PUBKEY_PATH: str = "models/uidai/test_key.pem"

    # v2: Story / Decision
    STORY_ENABLED: bool = True
    STORY_SCORING: bool = False
    DECISION_DRAFT_ENABLED: bool = True
    DECISION_DRAFT_TIMEOUT_S: int = 6


settings = Settings()
