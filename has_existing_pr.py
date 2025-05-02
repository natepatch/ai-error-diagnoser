from github import Github
from github.GithubException import UnknownObjectException, GithubException
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"

def has_existing_pr(fingerprint: str) -> bool:
    if not GITHUB_TOKEN:
        raise RuntimeError("❌ GITHUB_TOKEN is missing. Check your .env or environment variables.")

    gh = Github(GITHUB_TOKEN)
    print(f"🔍 Looking for repo: {REPO_NAME}")

    try:
        repo = gh.get_repo(REPO_NAME)
    except UnknownObjectException:
        raise RuntimeError(f"❌ Repo '{REPO_NAME}' not found. Check if the repo exists and the token has access.")
    except GithubException as e:
        raise RuntimeError(f"❌ GitHub API error ({e.status}): {e.data.get('message')}")

    open_prs = repo.get_pulls(state="open", sort="created", base="main")

    for pr in open_prs:
        if fingerprint in pr.title or fingerprint in (pr.body or ""):
            return True

    return False

