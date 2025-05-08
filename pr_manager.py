
import os
import json
import subprocess
import re
from github_client import get_repo, get_existing_pr, submit_pr_to_github
from ruby_linter import validate_with_rubocop, autocorrect_with_rubocop
from ruby_parser import reindent_ruby_method, find_method_bounds
from ai_fixer.rspec_generator import generate_and_write_rspec_test, run_spec, guessed_class_name_from_path
from analyze_error import ask_model
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"

def clean_ai_output(code: str) -> str:
    code = re.sub(r"^```(?:ruby)?\n?", "", code.strip())
    code = re.sub(r"```$", "", code.strip())
    return code.strip()

def create_pull_request(filepath, line_number, diagnosis_text, final_code_str, error_id) -> None:
    repo = get_repo(GITHUB_TOKEN, REPO_NAME)

    if get_existing_pr(repo, error_id):
        print(f"🚫 Skipping PR creation — a matching PR already exists for error {error_id}.")
        return

    contents = repo.get_contents(filepath)
    lines = contents.decoded_content.decode().splitlines()

    def apply_patch(code_str: str) -> tuple[bool, str, str, list[str], str | None]:
        code_str = clean_ai_output(code_str)

        corrected_code = autocorrect_with_rubocop(code_str)
        if not corrected_code:
            print("❌ RuboCop autocorrection failed — skipping.")
            return False, "", "", [], None
        print("🧾 AI-generated code for RuboCop validation:\n" + corrected_code)

        is_valid, lint_output = validate_with_rubocop(corrected_code)
        if not is_valid:
            print("❌ RuboCop validation failed:")
            print("🔎 Full output:\n" + lint_output)
            return False, "", "", [], None

        final_code = reindent_ruby_method(corrected_code.splitlines())
        final_code_str = "\n".join(final_code)
        method_name_match = re.search(r"def\s+(\w+)", corrected_code)
        method_name = method_name_match.group(1) if method_name_match else "unknown_method"

        try:
            start, end = find_method_bounds(lines, method_name)
            print(f"🔧 Replacing method `{method_name}`: lines {start+1} to {end+1}")
            updated_lines = lines[:start] + final_code + lines[end + 1:]
        except ValueError:
            print(f"⚠️ Method '{method_name}' not found — appending it instead.")
            updated_lines = lines + [""] + final_code

        with open(filepath, "w") as f:
            f.write("\n".join(updated_lines))

        try:
            subprocess.run(["rubocop", "-A", filepath], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❗ rubocop -A exited with error — continuing to validate:\n{e}")

        final_validation = subprocess.run(
            ["rubocop", filepath, "--format", "json"],
            capture_output=True,
            text=True
        )

        ignorable_offenses = {"Style/Documentation"}
        uncorrectable = []
        if final_validation.returncode != 0:
            try:
                result = json.loads(final_validation.stdout)
                uncorrectable = [
                    o for f in result["files"] for o in f["offenses"]
                    if o["cop_name"] not in ignorable_offenses
                ]
            except json.JSONDecodeError:
                print("❌ Failed to parse RuboCop JSON output.")
                return False, method_name, final_code_str, [], None

        spec_path, failure_summary = generate_and_write_rspec_test(
            class_name=guessed_class_name_from_path(filepath),
            method_name=method_name,
            method_code=corrected_code,
            app_path=filepath,
            generate_rspec_block=ask_model,
        )

        if not spec_path:
            return False, method_name, final_code_str, uncorrectable, failure_summary

        passed, _ = run_spec(spec_path, capture_output=True)
        return passed, method_name, final_code_str, uncorrectable, None

    failure_summary = None
    passed, method_name, fixed_code, uncorrectable, failure_summary = apply_patch(final_code_str)

    if not passed:
        print("🔁 Retrying with failure context...")

        original_method_block = final_code_str.strip()

        retry_prompt = (
            f"The following Ruby method is failing its associated RSpec tests:\n\n"
            f"📄 Method code:\n```ruby\n{original_method_block}\n```\n\n"
            f"❌ RSpec failures:\n{failure_summary or 'No summary available.'}\n\n"
            f"Please revise the method to ensure all tests pass.\n"
            f"- Use `GraphQL::ExecutionError.new(message, extensions: {{ code: :unauthorized }})` to attach metadata.\n"
            f"- Do NOT use keyword arguments directly in `raise`.\n"
            f"- Ensure all output is valid Ruby that passes RuboCop.\n"
            f"✅ Output only the corrected Ruby method.\n"
            f"❌ Do not include explanations or markdown."
        )

        retry_code = ask_model(retry_prompt).strip()
        passed, method_name, fixed_code, uncorrectable, failure_summary = apply_patch(retry_code)

    if not passed:
        print("❌ All attempts failed. Skipping PR.")
        return

    if uncorrectable:
        print("❌ Uncorrectable RuboCop issues:")
        for o in uncorrectable:
            print(f"- {o['cop_name']}: {o['message']}")
        print("❌ Skipping PR due to lint failures.")
        return

    with open(filepath, "r") as f:
        final_file_content = f.read()

    branch_name = f"ai/fix-{error_id[:8]}"
    explanation = diagnosis_text.split("```ruby")[0].strip()

    pr_body = (
        f"### 🤖 AI Explanation\n\n"
        f"{explanation}\n\n"
        f"---\n\n"
        f"### ✅ Suggested Fix\n\n"
        f"```ruby\n{fixed_code}\n```"
    )

    submit_pr_to_github(repo, filepath, branch_name, final_file_content, error_id, pr_body)
