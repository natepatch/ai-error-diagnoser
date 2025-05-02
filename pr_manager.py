from github import Github
import os
import re
import subprocess
import tempfile
from analyze_error import diagnose_log
from dotenv import load_dotenv  # ✅ Add this

load_dotenv()  # ✅ Load .env values automatically
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"


def validate_with_rubocop(ruby_code: str) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".rb", delete=False) as tmp_file:
        tmp_file.write(ruby_code)
        tmp_file.flush()
        tmp_path = tmp_file.name

    try:
        result = subprocess.run(
            [
                "rubocop",
                "--force-exclusion",
                "--format",
                "simple",
                "--only",
                "Layout,Style,Lint",
                tmp_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        is_clean = result.returncode == 0
        output = result.stdout.strip()
        return is_clean, output
    except FileNotFoundError:
        return False, "Rubocop not found. Is it installed and available in your PATH?"
    except subprocess.TimeoutExpired:
        return False, "Rubocop validation timed out."
    finally:
        os.remove(tmp_path)


def has_existing_pr(error_id: str) -> bool:
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
    branch_name = f"ai/fix-{error_id[:8]}"
    pulls = repo.get_pulls(state="open")
    for pr in pulls:
        if pr.head.ref == branch_name:
            print(f"⚠️ PR already exists for error {error_id} (#{pr.number})")
            return True
    return False


def extract_ruby_code(diagnosis: str) -> list[str]:
    code = diagnosis.strip()
    if "```" in code:
        parts = code.split("```")
        code = next((p for p in parts if "ruby" not in p.lower()), parts[-1])

    lines = code.splitlines()
    valid_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not re.search(r"[a-zA-Z0-9_\[\]\(\)\.:=]", stripped):
            continue
        if line.startswith("  ") or stripped.startswith(
            ("def ", "end", "return", "if ", "unless ", "context", "Account", "User")
        ):
            valid_lines.append(line)
    return valid_lines


def validate_and_correct_ruby_code(
    method_code_lines: list[str], method_name: str
) -> list[str]:
    ruby_code = "\n".join(method_code_lines)
    prompt = f"""
You are a Ruby expert. Review the following Ruby method called `{method_name}`.
If it is valid, return it as-is. If not, fix it. No explanation, only corrected Ruby code.

{ruby_code}

css
Copy
Edit
"""
    try:
        ai_response = diagnose_log(prompt)
        corrected = ai_response.strip()
        if "```" in corrected:
            parts = corrected.split("```")
            corrected = next((p for p in parts if "ruby" not in p.lower()), parts[-1])
        corrected_lines = [line for line in corrected.splitlines() if line.strip()]
        print("🥪 AI-corrected Ruby method:\n" + "\n".join(corrected_lines))
        return corrected_lines
    except Exception as e:
        print(f"⚠️ Failed to validate Ruby method with AI: {e}")
        return method_code_lines


def find_method_bounds(lines: list[str], method_name: str) -> tuple[int, int]:
    start = None
    depth = 0
    for i, line in enumerate(lines):
        if re.match(rf"^\s*def\s+{re.escape(method_name)}\b", line):
            start = i
            depth = 1
            continue
        if start is not None:
            if re.match(r"^\s*def\b", line):
                depth += 1
            elif re.match(r"^\s*end\b", line):
                depth -= 1
                if depth == 0:
                    return start, i
    raise ValueError(f"Method '{method_name}' not found or unbalanced in file.")


def create_pull_request(
    filepath: str, line_number: int, diagnosis: str, error_id: str
) -> None:
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
    contents = repo.get_contents(filepath)
    lines = contents.decoded_content.decode().splitlines()

    replacement_code = extract_ruby_code(diagnosis)
    print("🧪 Extracted replacement code:")
    print("\n".join(replacement_code))

    if not replacement_code:
        print(f"⚠️ No Ruby code extracted from AI output. Diagnosis was:\n{diagnosis}")
        return

    corrected_code = autocorrect_with_rubocop(ruby_code_str)
    print("🧼 RuboCop auto-corrected Ruby code:")
    print(corrected_code)

    # Then continue with validation or PR creation
    replacement_code = corrected_code.splitlines()

    method_name_match = next(
        (
            re.search(r"def\s+(\w+)", line)
            for line in replacement_code
            if "def " in line
        ),
        None,
    )
    method_name = method_name_match.group(1) if method_name_match else "current_account"

    if not replacement_code[0].strip().startswith("def "):
        replacement_code.insert(0, f"def {method_name}")
        print("⚠️ AI output was missing method declaration — added manually.")

    while replacement_code and replacement_code[-1].strip() == "end":
        replacement_code.pop()
    replacement_code.append("end")

    replacement_code = validate_and_correct_ruby_code(replacement_code, method_name)

    try:
        start, end = find_method_bounds(lines, method_name)
        print(f"🔧 Replacing method `{method_name}`: lines {start+1} to {end+1}")
        lines = lines[:start] + replacement_code + lines[end + 1 :]
    except ValueError as e:
        print(f"❌ Could not replace method: {e}")
        return

    updated_content = "\n".join(lines)
    branch_name = f"ai/fix-{error_id[:8]}"
    base_branch = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_branch.commit.sha)

    repo.update_file(
        path=filepath,
        message=f"AI fix suggestion for {error_id}",
        content=updated_content,
        sha=contents.sha,
        branch=branch_name,
    )

    repo.create_pull(
        title=f"[AI Fix] Patch for {error_id}",
        body=f"This PR includes an automated method replacement:\n\n```ruby\n{ruby_code_str}\n```",
        head=branch_name,
        base="main",
    )

    print(f"✅ Pull request created: ai/fix-{error_id[:8]}")
