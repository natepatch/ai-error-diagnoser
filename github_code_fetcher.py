from github import Github
import os

def fetch_code_context(filepath: str, line_number: int, context_lines: int = 10) -> str:
    token = os.getenv("GITHUB_TOKEN")
    repo = Github(token).get_repo("patchworkhealth/PatchworkOnRails")

    # Clean up the file path (e.g., remove `/app/` if needed)
    if filepath.startswith("/app/"):
        filepath = filepath[5:]

    try:
        contents = repo.get_contents(filepath)
        lines = contents.decoded_content.decode().splitlines()

        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        snippet = lines[start:end]
        return "\n".join(f"{i+1:4d}: {line}" for i, line in enumerate(snippet, start=start))
    except Exception as e:
        return f"⚠️ Failed to fetch context for {filepath}:{line_number} — {e}"
