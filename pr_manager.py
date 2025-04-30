import os
from github import Github

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"  # change if needed

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def has_existing_pr(error_id: str) -> bool:
    """Check if a PR already exists for this error ID."""
    for pr in repo.get_pulls(state="open"):
        if error_id in pr.title or error_id in pr.body:
            return True
    return False

def create_pr(error_id: str, message: str, diagnosis: str):
    """Placeholder to eventually auto-create a PR."""
    print(f"📦 Would create PR for error {error_id}")
    print("Message:", message)
    print("Diagnosis:", diagnosis)
