from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.integrations.github import github_client
from app.models import Project, Activity
from app.schemas import ActivityCreate
from uuid import UUID

router = APIRouter(prefix="/api/v1/integrations/github", tags=["github"])

@router.get("/repos")
async def list_github_repos():
    """List all GitHub repos for the user"""
    try:
        repos = await github_client.get_user_repos()
        return {
            "repos": [
                {
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo["description"],
                    "url": repo["html_url"],
                    "stars": repo["stargazers_count"],
                    "forks": repo["forks_count"],
                    "language": repo["language"],
                    "updated_at": repo["updated_at"],
                    "created_at": repo["created_at"],
                }
                for repo in repos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")

@router.post("/sync/{project_id}")
async def sync_project_with_github(project_id: UUID, db: Session = Depends(get_db)):
    """Sync a project with its GitHub repo"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.github_repo:
        raise HTTPException(status_code=400, detail="Project has no GitHub repo configured")
    
    try:
        # Fetch recent commits
        commits = await github_client.get_repo_commits(project.github_repo, per_page=10)
        
        # Create activities for commits
        for commit in commits:
            # Check if activity already exists
            existing = db.query(Activity).filter(
                Activity.project_id == project_id,
                Activity.type == "commit",
                Activity.external_url == commit["html_url"]
            ).first()
            
            if not existing:
                activity = Activity(
                    project_id=project_id,
                    type="commit",
                    description=f"Commit by {commit['commit']['author']['name']}: {commit['commit']['message'][:100]}",
                    external_url=commit["html_url"],
                    extra_data={
                        "sha": commit["sha"][:7],
                        "author": commit["commit"]["author"]["name"],
                    }
                )
                db.add(activity)
        
        db.commit()
        
        return {
            "message": f"Synced {len(commits)} commits",
            "project": project.name,
            "repo": project.github_repo
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@router.get("/commits/{repo_name}")
async def get_repo_commits(repo_name: str, per_page: int = 30):
    """Get commits for a specific repo"""
    try:
        commits = await github_client.get_repo_commits(repo_name, per_page=per_page)
        return {
            "commits": [
                {
                    "sha": commit["sha"][:7],
                    "message": commit["commit"]["message"],
                    "author": commit["commit"]["author"]["name"],
                    "date": commit["commit"]["author"]["date"],
                    "url": commit["html_url"]
                }
                for commit in commits
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")

@router.get("/pulls/{repo_name}")
async def get_repo_pulls(repo_name: str, state: str = "all"):
    """Get pull requests for a specific repo"""
    try:
        pulls = await github_client.get_repo_pulls(repo_name, state=state)
        return {
            "pulls": [
                {
                    "id": pr["id"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "user": {"login": pr["user"]["login"]},
                    "created_at": pr["created_at"],
                    "url": pr["html_url"]
                }
                for pr in pulls
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")

@router.get("/issues/{repo_name}")
async def get_repo_issues(repo_name: str, state: str = "all"):
    """Get issues for a specific repo"""
    try:
        issues = await github_client.get_repo_issues(repo_name, state=state)
        return {
            "issues": [
                {
                    "id": issue["id"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "user": {"login": issue["user"]["login"]},
                    "created_at": issue["created_at"],
                    "url": issue["html_url"]
                }
                for issue in issues
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub API error: {str(e)}")
