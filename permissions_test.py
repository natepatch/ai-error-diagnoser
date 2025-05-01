from github import Github
from dotenv import load_dotenv
import os

load_dotenv()
g = Github(os.getenv("GITHUB_TOKEN"))
repo = g.get_repo("patchworkhealth/PatchworkOnRails")  # Must be exact casing
print(repo.full_name)
