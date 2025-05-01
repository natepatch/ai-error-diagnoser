from github import Github
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"

def has_existing_pr(error_id: str) -> bool:
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
    branch_name = f"ai/fix-{error_id[:8]}"

    pulls = repo.get_pulls(state='open')
    for pr in pulls:
        if pr.head.ref == branch_name:
            print(f"⚠️ PR already exists for error {error_id} (#{pr.number})")
            return True
    return False

def create_pull_request(filepath: str, line_number: int, diagnosis: str, error_id: str) -> None:
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)

    # Fetch original file contents
    contents = repo.get_contents(filepath)
    lines = contents.decoded_content.decode().splitlines()

    # Extract code lines from diagnosis
    stripped = diagnosis.strip()
    if "```" in stripped:
        stripped = stripped.split("```")[1] if "```" in stripped else stripped
    fix_lines = [line for line in stripped.splitlines() if line.strip() and not line.strip().startswith("#")]

    # Insert fix lines above the error line
    insert_at = min(max(line_number - 1, 0), len(lines))
    lines.insert(insert_at, f"# AI fix for error {error_id}")
    for i, fix_line in enumerate(fix_lines):
        lines.insert(insert_at + 1 + i, fix_line)

    updated_content = "\n".join(lines)

    # Create new branch
    branch_name = f"ai/fix-{error_id[:8]}"
    base_branch = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_branch.commit.sha)

    # Commit updated file
    repo.update_file(
        path=filepath,
        message=f"AI fix suggestion for {error_id}",
        content=updated_content,
        sha=contents.sha,
        branch=branch_name,
    )

    # Open PR
    repo.create_pull(
        title=f"[AI Fix] Patch for {error_id}",
        body=f"This PR includes an automated fix suggestion:\n\n```\n{diagnosis.strip()}\n```",
        head=branch_name,
        base="main"
    )

    print(f"✅ Pull request created: ai/fix-{error_id[:8]}")
