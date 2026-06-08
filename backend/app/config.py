import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "juanesscobar")

def get_cors_origins() -> List[str]:
    origins_str = os.getenv("CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",") if o.strip()]
    if ENVIRONMENT == "production":
        return []
    return ["http://localhost:5173", "http://localhost:3000"]

DEFAULT_REPOS = ["openagent"]
