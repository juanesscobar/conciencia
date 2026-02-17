import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "juanesscobar")

# Default repos to track
DEFAULT_REPOS = [
    "openagent",
    # Add other repos here
]
