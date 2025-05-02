from github import Github
from github.GithubException import UnknownObjectException, GithubException
import os

def get_repo(token: str, repo_name: str):
    if not token:
        raise RuntimeError("❌ GITHUB_TOKEN is missing. Check your .env or environment variables.")

    gh = Github(token)
    print(f"🔍 Looking for repo: {repo_name}")

    try:
        return gh.get_repo(repo_name)
    except UnknownObjectException:
        raise RuntimeError(f"❌ Repo '{repo_name}' not found. Check if the repo exists and the token has access.")
    except GithubException as e:
        raise RuntimeError(f"❌ GitHub API error ({e.status}): {e.data.get('message')}")

def get_existing_pr(repo, fingerprint: str):
    open_prs = repo.get_pulls(state="open", sort="created", base="main")
    for pr in open_prs:
        if fingerprint in pr.title or fingerprint in (pr.body or ""):
            return pr
    return None

def submit_pr_to_github(repo, filepath: str, branch_name: str, file_content: str, error_id: str, pr_body):
    contents = repo.get_contents(filepath)
    base_branch = repo.get_branch("main")
    ref = f"refs/heads/{branch_name}"

    try:
        repo.get_git_ref(ref)
        print(f"⚠️ Branch {branch_name} already exists. Using existing branch.")
    except:
        repo.create_git_ref(ref=ref, sha=base_branch.commit.sha)

    repo.update_file(
        path=filepath,
        message=f"AI fix suggestion for {error_id}",
        content=file_content,
        sha=contents.sha,
        branch=branch_name,
    )

    # 🛠️ Safely handle pr_body before passing to .strip()
    if isinstance(pr_body, dict):
        pr_body = json.dumps(pr_body, indent=2)
    elif isinstance(pr_body, str):
        pr_body = pr_body.strip()
    else:
        pr_body = str(pr_body).strip()

    repo.create_pull(
        title=f"[AI Fix] Patch for {error_id}",
        body=f"This PR includes an AI-generated fix for `{filepath}`.\n\n{pr_body}",
        head=branch_name,
        base="main",
    )

    print(f"✅ Pull request created: {branch_name}")
