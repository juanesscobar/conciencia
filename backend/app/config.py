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

# Geografía first-class (spec §7-9): país default PY, allowlist, scope explícito.
# LEADHUNTER_SCOPE (bbox|country) sigue como compat; SEARCH_SCOPE lo reemplaza.
SEARCH_DEFAULT_COUNTRY = os.getenv("SEARCH_DEFAULT_COUNTRY", "PY")
SEARCH_ALLOWED_COUNTRIES = os.getenv("SEARCH_ALLOWED_COUNTRIES", "PY,BR,AR,UY")
SEARCH_DEFAULT_REGION = os.getenv("SEARCH_DEFAULT_REGION", "") or None
SEARCH_DEFAULT_CITY = os.getenv("SEARCH_DEFAULT_CITY", "") or None
SEARCH_SCOPE = os.getenv("SEARCH_SCOPE", "") or None  # city|region|country|multi|global (None = legacy)
SEARCH_GEO_PROVIDER = os.getenv("SEARCH_GEO_PROVIDER", "osm")
SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL", "86400"))  # segundos (24h)

# Fase 5 — búsqueda semántica (spec §14)
EMBEDDING_ENABLED = os.getenv("EMBEDDING_ENABLED", "0")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")  # openai | deepseek | ollama | otro OpenAI-compatible
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "memory")  # memory | pgvector
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "")


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
