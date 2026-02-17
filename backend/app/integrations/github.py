import httpx
from typing import List, Dict, Any, Optional
from app.config import GITHUB_TOKEN, GITHUB_USERNAME

class GitHubClient:
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.username = GITHUB_USERNAME
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        } if self.token else {}
    
    async def get_user_repos(self) -> List[Dict[str, Any]]:
        """Fetch all repos for the user"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/{self.username}/repos",
                headers=self.headers,
                params={"sort": "updated", "per_page": 100}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo(self, repo_name: str) -> Dict[str, Any]:
        """Fetch specific repo details"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.username}/{repo_name}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo_commits(self, repo_name: str, per_page: int = 30) -> List[Dict[str, Any]]:
        """Fetch recent commits for a repo"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.username}/{repo_name}/commits",
                headers=self.headers,
                params={"per_page": per_page}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo_pulls(self, repo_name: str, state: str = "all") -> List[Dict[str, Any]]:
        """Fetch pull requests for a repo"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.username}/{repo_name}/pulls",
                headers=self.headers,
                params={"state": state, "per_page": 100}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_repo_issues(self, repo_name: str, state: str = "all") -> List[Dict[str, Any]]:
        """Fetch issues for a repo"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{self.username}/{repo_name}/issues",
                headers=self.headers,
                params={"state": state, "per_page": 100}
            )
            response.raise_for_status()
            return response.json()

# Singleton instance
github_client = GitHubClient()
