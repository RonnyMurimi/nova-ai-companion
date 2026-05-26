import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    USE_GROQ = os.getenv("USE_GROQ", "false").lower() == "true"

    # Server - Use PORT from environment (Railway sets this)
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("PORT", 8000))  # CHANGED: Use PORT env var

    # Paths
    MEMORY_DB_PATH = "./memory_db"
    USER_PROFILES_PATH = "./user_profiles"
    TEMP_AUDIO_PATH = "./temp_audio"
    CHAT_HISTORY_PATH = "./chat_history"
    USERS_PATH = "./users"
    THREADS_PATH = "./threads"

    # AI Settings
    if USE_GROQ:
        GPT_MODEL = "llama-3.3-70b-versatile"
    else:
        GPT_MODEL = "gpt-4o-mini"

    WHISPER_MODEL = "whisper-1"
    TTS_MODEL = "tts-1"
    TTS_VOICE = "nova"

    # Memory Settings
    MAX_MEMORIES_RETRIEVED = 8
    MEMORY_COLLECTION_NAME = "conversation_memory"

    # Auth
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-12345")

    # CORS - Allow frontend domain
    FRONTEND_URL = os.getenv("FRONTEND_URL", "*")

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories"""
        os.makedirs(cls.MEMORY_DB_PATH, exist_ok=True)
        os.makedirs(cls.USER_PROFILES_PATH, exist_ok=True)
        os.makedirs(cls.TEMP_AUDIO_PATH, exist_ok=True)
        os.makedirs(cls.CHAT_HISTORY_PATH, exist_ok=True)
        os.makedirs(cls.USERS_PATH, exist_ok=True)
        os.makedirs(cls.THREADS_PATH, exist_ok=True)


config = Config()
config.ensure_directories()