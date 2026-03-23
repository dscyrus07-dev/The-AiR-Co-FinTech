import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Airco Insights Engine"
    VERSION: str = "1.0.0"
    API_PREFIX: str = ""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")

    # File handling
    MAX_FILE_SIZE_MB: int = 20
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_MIME_TYPES: list = ["application/pdf"]
    TEMP_DIR: str = os.getenv("TEMP_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "tmp"))

    # PDF detection
    PDF_TEXT_THRESHOLD: int = 500
    PDF_SCAN_PAGES: int = 3

    # AI classification
    AI_BATCH_SIZE: int = 25

    # Processing
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://test.theairco.ai",
        "https://theairco.ai",
    ]


settings = Settings()
