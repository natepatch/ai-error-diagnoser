
from ai_fixer.spec_utils import get_spec_path, ensure_spec_file_exists, append_test_to_spec
import os
import subprocess
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
def build_rspec_prompt(
        class_name: str,
        method_name: str,
        method_code: str,
        file_path: str,
        code_context: str = "",
        similar_snippets: list = None
) -> str:
    from pathlib import Path

    try:
        class_context = Path(file_path).read_text()
    except Exception as e:
        class_context = "# Could not read file for context: " + str(e)

    similar_section = ""
    if similar_snippets:
        similar_section = "\n\nSimilar Code from Codebase:\n" + "\n\n".join(
            [f"# Related snippet {i+1}:\n{snippet}" for i, snippet in enumerate(similar_snippets)]
        )

    return f"""
{os.getenv("GRAPHQL_TESTING_HINT", "")}

You are a senior Ruby on Rails developer writing an RSpec test for the method `{method_name}` in the class `{class_name}`.

This class is defined in the file: `{file_path}`.

Here is the method:
```ruby
{method_code}
```

Here is additional context from the file:
```ruby
{code_context or class_context}
```
{similar_section}

Write an RSpec test that:
- Uses FactoryBot where appropriate
- Avoids calling `.new` on GraphQL types or other classes not meant to be manually instantiated
- Stubs any associations or context as needed (e.g. `context[:current_user]`)
- Write no more than 3–5 examples total: 1 success case and 2–4 failure cases that are meaningfully different
- Do not repeat tests or generate unnecessary variations
- Avoid any markdown formatting or explanation
- Output only valid RSpec Ruby code
- Do not assume models have direct foreign key setters (e.g., `thing_id=`). Instead, use `find_by(attribute: value)` or let the test stub the lookup.
- Prefer stubbing repository methods (like `.find_by(...)`) instead of assigning foreign keys directly.
- Use associations only if they are defined in the application (e.g., `create(:record, related_model: object)`), otherwise rely on stubbing.

""".strip()




def strip_markdown_fences(text: str) -> str:
    match = re.search(r"^\s*```ruby\s*\n(.*?)^\s*```", text, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return text.strip()

def infer_ruby_constant_from_path(app_path: str) -> str:
    rel_path = app_path.replace("app/", "").replace(".rb", "")
    parts = rel_path.split("/")
    if parts[0] in {"graphql", "controllers", "helpers", "views"}:
        parts = parts[1:]
    return "::".join("".join(w.capitalize() for w in part.split("_")) for part in parts)

import os
import re
import json
from typing import Callable, Tuple

import re

import re
import json

def parse_rspec_output_to_json(output: str) -> list[dict]:
    full_failures = []
    current_block = []
    collecting = False

    for line in output.splitlines():
        if re.match(r"^\s*\d+\)", line):
            if current_block:
                full_failures.append(current_block)
            current_block = [line]
            collecting = True
        elif collecting:
            if line.strip().startswith("rspec "):
                collecting = False
                if current_block:
                    full_failures.append(current_block)
                    current_block = []
                continue
            current_block.append(line)
            if line.strip() == "":
                # don’t close block just yet – multi-line allowed
                continue

    if current_block:
        full_failures.append(current_block)

    parsed = []

    for block in full_failures:
        if not block:
            continue

        header = block[0].strip()
        index_match = re.match(r"^(\d+)\)\s+(.*)", header)
        if not index_match:
            continue

        index = int(index_match.group(1))
        description = index_match.group(2).strip()

        error_type = ""
        message = ""
        hint = None
        file_paths = []

        for i, line in enumerate(block[1:], start=1):
            stripped = line.strip()

            # 1. Capture error type like GraphQL::ExecutionError:
            if not error_type:
                err_match = re.match(r"^((?:\w+::)*\w+Error):", stripped)
                if err_match:
                    error_type = err_match.group(1)
                    continue

            # 2. Capture message (first non-empty line after error type)
            if error_type and not message:
                if stripped and not stripped.startswith("Did you mean?") and not stripped.startswith("#"):
                    message = stripped
                    continue

            # 3. Hint
            if not hint:
                hint_match = re.match(r"Did you mean\?\s+(.*)", stripped)
                if hint_match:
                    hint = hint_match.group(1)

            # 4. File path
            file_match = re.match(r"#\s+(.+?):(\d+)", stripped)
            if file_match:
                file_paths.append({
                    "path": file_match.group(1),
                    "line": int(file_match.group(2))
                })

        parsed.append({
            "index": index,
            "description": description,
            "error_type": error_type,
            "message": message,
            "hint": hint,
            "file_paths": file_paths
        })

    return parsed


def generate_and_write_rspec_test(
        class_name: str,
        method_name: str,
        method_code: str,
        app_path: str,
        generate_rspec_block: Callable[[str], str],
        run_spec: Callable[[str, bool], Tuple[bool, str]],
        build_rspec_prompt: Callable[[str, str, str, str], str],
        infer_ruby_constant_from_path: Callable[[str], str],
        get_spec_path: Callable[[str], str],
        ensure_spec_file_exists: Callable[[str, str], None],
        append_test_to_spec: Callable[[str, str], None],
        strip_markdown_fences: Callable[[str], str]
) -> Tuple[str | None, str | None]:
    spec_path = get_spec_path(app_path)
    rails_root = os.getenv("RAILS_REPO_PATH")
    if not rails_root:
        raise RuntimeError("RAILS_REPO_PATH not set")

    abs_spec_path = os.path.join(rails_root, spec_path)
    ensure_spec_file_exists(abs_spec_path, class_name)

    inferred_constant = infer_ruby_constant_from_path(app_path)
    prompt = build_rspec_prompt(inferred_constant, method_name, method_code, os.path.join(rails_root, app_path))
    raw_test_output = generate_rspec_block(prompt)
    print("🧾 Raw AI output:\n", raw_test_output)
    test_block = strip_markdown_fences(raw_test_output)

    test_block = re.sub(
        r"RSpec\.describe\s+[A-Za-z0-9_:]+",
        f"RSpec.describe {inferred_constant}",
        test_block
    )

    print("📦 Final test block to write:\n", test_block)
    append_test_to_spec(abs_spec_path, test_block)

    with open(abs_spec_path, "r+") as f:
        content = f.read()
        cleaned = re.sub(r"RSpec\.describe\s+\w+,\s+type: :\w+\s+do\n\s*end\n*", "", content)
        f.seek(0)
        f.write(cleaned)
        f.truncate()

    passed, output = run_spec(spec_path, capture_output=True)

    if not passed:
        print("❌ Spec failed. Here's what failed:")
        failures = parse_rspec_output_to_json(output)
        return None, json.dumps(failures, indent=2)

    return spec_path, None



def guessed_class_name_from_path(filepath: str) -> str:
    filename = os.path.basename(filepath).replace(".rb", "")
    return ''.join(word.capitalize() for word in filename.split('_'))

def run_spec(spec_path: str, capture_output: bool = False) -> tuple[bool, str]:
    rails_root = os.getenv("RAILS_REPO_PATH")
    if not rails_root:
        print("❌ RAILS_REPO_PATH not set in environment. Skipping spec run.")
        return False, ""

    abs_spec_path = os.path.join(rails_root, spec_path)
    if not os.path.exists(abs_spec_path):
        print(f"❌ Spec file not found at: {abs_spec_path}")
        return False, ""

    env = os.environ.copy()
    env.update({
        "DD_TRACE_ENABLED": "false",
        "DD_INSTRUMENTATION_TELEMETRY_ENABLED": "false",
        "DD_REMOTE_CONFIGURATION_ENABLED": "false",
    })

    result = subprocess.run(
        ["bundle", "exec", "rspec", "--format", "documentation", abs_spec_path],
        cwd=rails_root,
        env=env,
        capture_output=True,
        text=True
    )

    # Combine stdout + stderr so we get full trace output
    output = result.stdout + result.stderr
    return result.returncode == 0, output