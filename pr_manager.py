import os
import json
import subprocess
import re
from github_client import get_repo, get_existing_pr, submit_pr_to_github
from ruby_linter import validate_with_rubocop, autocorrect_with_rubocop
from ruby_parser import extract_ruby_code, find_method_bounds, reindent_ruby_method
from ai_diagnosis import validate_and_correct_ruby_code
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"

def create_pull_request(filepath: str, line_number: int, diagnosis: str, error_id: str) -> None:
    repo = get_repo(GITHUB_TOKEN, REPO_NAME)

    if get_existing_pr(repo, error_id):
        print(f"🚫 Skipping PR creation — a matching PR already exists for error {error_id}.")
        return

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
    corrected_code = re.sub(r"\n\s*else\s*(?:#.*)?\s*\n\s*end", "\nend", corrected_code)
    print("🧼 RuboCop auto-corrected Ruby code:")
    print(corrected_code)

    is_valid, lint_output = validate_with_rubocop(corrected_code)
    if not is_valid:
        print(f"❌ RuboCop validation failed even after auto-correct:\n{lint_output}")
        print("❌ Skipping PR — unsafe or unformatted Ruby code.")
        return

    corrected_lines = corrected_code.splitlines()
    method_name_match = re.search(r"def\s+(\w+)", corrected_code)
    method_name = method_name_match.group(1) if method_name_match else "unknown_method"

    if not corrected_lines[0].strip().startswith("def "):
        corrected_lines.insert(0, f"def {method_name}")
        print("⚠️ AI output was missing method declaration — added manually.")
    if corrected_lines[-1].strip() != "end":
        corrected_lines.append("end")

    final_ruby_code = validate_and_correct_ruby_code(corrected_lines, method_name)
    final_code = reindent_ruby_method(final_ruby_code)

    final_code_str = "\n".join(final_code)

    try:
        start, end = find_method_bounds(lines, method_name)
        print(f"🔧 Replacing method `{method_name}`: lines {start+1} to {end+1}")
        lines = lines[:start] + final_code + lines[end + 1:]
    except ValueError:
        print(f"⚠️ Method '{method_name}' not found — appending it instead.")
        lines.append("\n")
        lines += final_code

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

    explanation = "This fix was generated automatically to resolve a production error."
    pr_body = f"""
### 🤖 AI Explanation

{explanation}

---

### ✅ Final Suggested Fix

```ruby
{final_code_str}
```
""".strip()

    submit_pr_to_github(repo, filepath, branch_name, final_file_content, error_id, pr_body)