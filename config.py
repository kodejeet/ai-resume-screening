import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Application configuration and environment manager for AI Resume Screening."""
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip()
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    @classmethod
    def validate(cls):
        """Validate critical configuration settings."""
        if not cls.GEMINI_API_KEY:
            print("[WARNING] Config: GEMINI_API_KEY environment variable is missing or empty!")
            return False
        return True

    @classmethod
    def get_safe_status(cls):
        """Return configuration status safe for frontend consumption (key masked)."""
        has_key = bool(cls.GEMINI_API_KEY)
        masked_key = ""
        if has_key:
            if len(cls.GEMINI_API_KEY) > 8:
                masked_key = cls.GEMINI_API_KEY[:4] + "..." + cls.GEMINI_API_KEY[-4:]
            else:
                masked_key = "*****"
                
        return {
            "api_key_configured": has_key,
            "masked_key": masked_key,
            "model": cls.GEMINI_MODEL,
            "engine": "Google Gemini API"
        }
