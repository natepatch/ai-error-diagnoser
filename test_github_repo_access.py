from github import Github
import os

token = os.getenv("GITHUB_TOKEN")
repo_name = "patchworkhealth/PatchworkOnRails"

gh = Github(token)
print(f"🔍 Trying to fetch repo: {repo_name}")
repo = gh.get_repo(repo_name)
print(f"✅ Repo found: {repo.full_name}")
