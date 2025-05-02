from github import Github
import os
import re
import subprocess
import tempfile
import json
from analyze_error import diagnose_log
from dotenv import load_dotenv

load_dotenv()
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
                "--format", "simple",
                "--only", "Layout,Style,Lint",
                "--except", "Style/Documentation",
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

def autocorrect_with_rubocop(ruby_code: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".rb", delete=False) as tmp_file:
        tmp_file.write(ruby_code)
        tmp_file.flush()
        tmp_path = tmp_file.name

    try:
        subprocess.run(
            [
                "rubocop",
                "-A",
                "--only", "Layout,Style,Lint",
                "--except", "Style/Documentation",
                tmp_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        with open(tmp_path, "r") as f:
            corrected_code = f.read()
        return corrected_code
    except Exception as e:
        print(f"❌ RuboCop autocorrect failed: {e}")
        return ruby_code
    finally:
        os.remove(tmp_path)

def reindent_ruby_method(lines: list[str], indent: int = 2) -> list[str]:
    if len(lines) < 2:
        return lines
    indented = [lines[0]]
    body = lines[1:-1]
    end = lines[-1]
    indented_body = [(" " * indent) + line.strip() for line in body]
    indented.append("\n".join(indented_body))
    indented.append(end)
    return indented

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
    return [line for line in code.splitlines() if line.strip()]

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

def validate_and_correct_ruby_code(method_code_lines: list[str], method_name: str) -> list[str]:
    ruby_code = "\n".join(method_code_lines)
    prompt = f"""
You are a Ruby expert. Review the following Ruby method called `{method_name}`.
If it is valid, return it as-is. If not, fix it. No explanation, only corrected Ruby code.

{ruby_code}
""".strip()

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

def submit_pr_to_github(repo, filepath: str, branch_name: str, file_content: str, error_id: str, corrected_code: str):
    contents = repo.get_contents(filepath)
    base_branch = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_branch.commit.sha)

    repo.update_file(
        path=filepath,
        message=f"AI fix suggestion for {error_id}",
        content=file_content,
        sha=contents.sha,
        branch=branch_name,
    )

    repo.create_pull(
        title=f"[AI Fix] Patch for {error_id}",
        body=f"This PR includes an automated method replacement:\n\n```ruby\n{corrected_code}\n```",
        head=branch_name,
        base="main",
    )

    print(f"✅ Pull request created: {branch_name}")

def create_pull_request(filepath: str, line_number: int, diagnosis: str, error_id: str) -> None:
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
    contents = repo.get_contents(filepath)
    lines = contents.decoded_content.decode().splitlines()

    replacement_code_lines = extract_ruby_code(diagnosis)
    print("🧪 Extracted replacement code:")
    print("\n".join(replacement_code_lines))

    if not replacement_code_lines:
        print(f"⚠️ No Ruby code extracted from AI output. Diagnosis was:\n{diagnosis}")
        return

    raw_ruby_code = "\n".join(replacement_code_lines)
    corrected_code = autocorrect_with_rubocop(raw_ruby_code)
    print("🧼 RuboCop auto-corrected Ruby code:")
    print(corrected_code)

    is_valid, lint_output = validate_with_rubocop(corrected_code)
    if not is_valid:
        print(f"❌ RuboCop validation failed even after auto-correct:\n{lint_output}")
        print("❌ Skipping PR — unsafe or unformatted Ruby code.")
        return

    corrected_lines = corrected_code.splitlines()
    method_name_match = re.search(r"def\s+(\w+)", corrected_code)
    method_name = method_name_match.group(1) if method_name_match else "current_account"

    if not corrected_lines[0].strip().startswith("def "):
        corrected_lines.insert(0, f"def {method_name}")
        print("⚠️ AI output was missing method declaration — added manually.")
    if corrected_lines[-1].strip() != "end":
        corrected_lines.append("end")

    validated_code = validate_and_correct_ruby_code(corrected_lines, method_name)
    final_code = reindent_ruby_method(validated_code)

    try:
        start, end = find_method_bounds(lines, method_name)
        print(f"🔧 Replacing method `{method_name}`: lines {start+1} to {end+1}")
        lines = lines[:start] + final_code + lines[end + 1:]
    except ValueError as e:
        print(f"❌ Could not replace method: {e}")
        return

    updated_content = "\n".join(lines)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(updated_content)

    try:
        subprocess.run(["rubocop", "-A", filepath], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❗ rubocop -A exited with error — continuing to validate:\n{e}")

    ignorable_offenses = {"Style/Documentation"}
    final_validation = subprocess.run(
        ["rubocop", filepath, "--format", "json"],
        capture_output=True,
        text=True
    )

    if final_validation.returncode != 0:
        try:
            result = json.loads(final_validation.stdout)
            uncorrectable = [
                o for f in result["files"] for o in f["offenses"]
                if o["cop_name"] not in ignorable_offenses
            ]
            if uncorrectable:
                print("❌ RuboCop found uncorrectable offenses:")
                for o in uncorrectable:
                    print(f"- {o['cop_name']}: {o['message']}")
                print("❌ Skipping PR — file still has non-ignorable issues.")
                return
            else:
                print("⚠️ RuboCop returned issues, but only ignorable offenses were present.")
        except json.JSONDecodeError:
            print("❌ Failed to parse RuboCop JSON output. Skipping PR.")
            return

    with open(filepath, "r") as f:
        final_file_content = f.read()

    branch_name = f"ai/fix-{error_id[:8]}"
    submit_pr_to_github(repo, filepath, branch_name, final_file_content, error_id, corrected_code)
