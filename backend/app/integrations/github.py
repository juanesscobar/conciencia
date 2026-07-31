import httpx
import time
import asyncio
import json
from typing import List, Dict, Any, Optional
from app.config import GITHUB_TOKEN, GITHUB_USERNAME, REDIS_URL

redis_client: Optional[Any] = None
try:
    import redis.asyncio as aioredis
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    pass


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


github_rate_limiter = RateLimiter(
    requests_per_hour=60 if not GITHUB_TOKEN else 5000
)


class GitHubClient:
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.username = GITHUB_USERNAME
        self.base_url = "https://api.github.com"

        if not self.token:
            print("WARNING: GITHUB_TOKEN not set — using unauthenticated requests (60 req/hr)")

        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.headers["Accept"] = "application/vnd.github.v3+json"

    async def _cache_get(self, key: str) -> Optional[Any]:
        if redis_client:
            try:
                val = await redis_client.get(f"github:{key}")
                return json.loads(val) if val else None
            except Exception:
                pass
        return None

    async def _cache_set(self, key: str, value: Any, ttl: int = 300):
        if redis_client:
            try:
                await redis_client.setex(f"github:{key}", ttl, json.dumps(value))
            except Exception:
                pass

    async def _make_request(
        self, method: str, url: str, cache_key: str = None, **kwargs
    ) -> Dict[str, Any]:
        if cache_key:
            cached = await self._cache_get(cache_key)
            if cached:
                return cached

        if not self.token:
            print(f"WARNING: Unauthenticated GitHub request — rate limit very low (60/hr)")

        await github_rate_limiter.acquire()

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, headers=self.headers, **kwargs
            )

            if response.status_code == 403:
                raise Exception(
                    "GitHub API rate limit exceeded or access denied. "
                    "Set GITHUB_TOKEN in .env for higher limits."
                )
            if response.status_code == 404:
                raise Exception(
                    f"GitHub resource not found: {url}. "
                    f"Check that GITHUB_USERNAME ({self.username}) is correct "
                    f"and the repository exists."
                )

            response.raise_for_status()
            data = response.json()

            if cache_key:
                await self._cache_set(cache_key, data)

            return data

    async def get_user_repos(self) -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/users/{self.username}/repos",
            cache_key=f"repos:{self.username}",
            params={"sort": "updated", "per_page": 100, "type": "all"},
        )

    async def get_repo(self, repo_name: str) -> Dict[str, Any]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}",
            cache_key=f"repo:{self.username}/{repo_name}",
        )

    async def get_repo_commits(
        self, repo_name: str, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}/commits",
            cache_key=f"commits:{self.username}/{repo_name}",
            params={"per_page": per_page},
        )

    async def get_repo_pulls(
        self, repo_name: str, state: str = "all"
    ) -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}/pulls",
            cache_key=f"pulls:{self.username}/{repo_name}:{state}",
            params={"state": state, "per_page": 100},
        )

    async def get_repo_issues(
        self, repo_name: str, state: str = "all"
    ) -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET",
            f"{self.base_url}/repos/{self.username}/{repo_name}/issues",
            cache_key=f"issues:{self.username}/{repo_name}:{state}",
            params={"state": state, "per_page": 100},
        )


github_client = GitHubClient()
