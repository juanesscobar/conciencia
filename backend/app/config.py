import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "juanesscobar")

# Database — PostgreSQL always
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://missioncontrol:missioncontrol@localhost:5432/missioncontrol"
)

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# JWT — must be set in production
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY and ENVIRONMENT == "production":
    raise RuntimeError("SECRET_KEY must be set in production environment")
if not SECRET_KEY:
    SECRET_KEY = "dev-secret-key-do-not-use-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Lead Hunter — descubrimiento automático de leads B2B
LEADHUNTER_CRON = os.getenv("LEADHUNTER_CRON", "0 9 * * 1")  # lunes 09:00 local (vacío = off)
LEADHUNTER_BBOX = os.getenv("LEADHUNTER_BBOX", "-25.55,-57.75,-25.15,-57.40")  # Asunción: sur,oeste,norte,este
LEADHUNTER_MAX_PER_SOURCE = int(os.getenv("LEADHUNTER_MAX_PER_SOURCE", "50"))


def get_cors_origins() -> List[str]:
    origins_str = os.getenv("CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",") if o.strip()]
    if ENVIRONMENT == "production":
        return ["http://46.62.196.151"]
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://46.62.196.151",
        "http://46.62.196.151:80"
    ]


DEFAULT_REPOS = ["openagent"]
