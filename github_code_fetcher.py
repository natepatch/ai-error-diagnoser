import os
from github import Github

# Load GitHub access token and repo name from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"  # ✅ Use correct org/repo name (case-sensitive)

# Initialize GitHub client
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def fetch_file_contents(path: str, ref: str = "main") -> str:
    """
    Fetches the contents of a file in the GitHub repo.

    Args:
        path (str): Path to the file in the repo (e.g. "app/models/user.rb")
        ref (str): Branch or commit SHA (default is "main")

    Returns:
        str: The file content as a string (UTF-8 decoded)
    """
    try:
        contents = repo.get_contents(path, ref=ref)
        return contents.decoded_content.decode()
    except Exception as e:
        print(f"❌ Failed to fetch {path}: {e}")
        return ""
