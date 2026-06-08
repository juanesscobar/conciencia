import httpx
import time
import asyncio
from typing import List, Dict, Any, Optional
from functools import lru_cache
from app.config import GITHUB_TOKEN, GITHUB_USERNAME
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, requests_per_hour: int = 60):
        self.requests_per_hour = requests_per_hour
        self.requests: List[float] = []
    
    async def acquire(self):
        now = time.time()
        self.requests = [r for r in self.requests if now - r < 3600]
        
        if len(self.requests) >= self.requests_per_hour:
            sleep_time = 3600 - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                self.requests = []
        
        self.requests.append(now)
    
    def get_remaining(self) -> int:
        now = time.time()
        self.requests = [r for r in self.requests if now - r < 3600]
        return max(0, self.requests_per_hour - len(self.requests))

class Cache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = (value, time.time())
    
    def clear(self):
        self.cache.clear()

github_rate_limiter = RateLimiter(requests_per_hour=60 if not GITHUB_TOKEN else 5000)
github_cache = Cache(ttl_seconds=300)

class GitHubClient:
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.username = GITHUB_USERNAME
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        } if self.token else {}
    
    async def _make_request(self, method: str, url: str, cache_key: str = None, **kwargs) -> Dict[str, Any]:
        if cache_key:
            cached = github_cache.get(cache_key)
            if cached:
                return cached
        
        await github_rate_limiter.acquire()
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            data = response.json()
            
            if cache_key:
                github_cache.set(cache_key, data)
            
            return data
    
    async def get_user_repos(self) -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/users/{self.username}/repos",
            cache_key=f"repos:{self.username}",
            params={"sort": "updated", "per_page": 100}
        )
    
    async def get_repo(self, repo_name: str) -> Dict[str, Any]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}",
            cache_key=f"repo:{self.username}/{repo_name}"
        )
    
    async def get_repo_commits(self, repo_name: str, per_page: int = 30) -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}/commits",
            cache_key=f"commits:{self.username}/{repo_name}",
            params={"per_page": per_page}
        )
    
    async def get_repo_pulls(self, repo_name: str, state: str = "all") -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}/pulls",
            cache_key=f"pulls:{self.username}/{repo_name}:{state}",
            params={"state": state, "per_page": 100}
        )
    
    async def get_repo_issues(self, repo_name: str, state: str = "all") -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}/issues",
            cache_key=f"issues:{self.username}/{repo_name}:{state}",
            params={"state": state, "per_page": 100}
        )

github_client = GitHubClient()
