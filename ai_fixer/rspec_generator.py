
from ai_fixer.spec_utils import get_spec_path, ensure_spec_file_exists, append_test_to_spec
import os
import subprocess
import re

def build_rspec_prompt(class_name: str, method_name: str, method_code: str) -> str:
    return f"""
You are a senior Ruby developer writing RSpec tests.

Write an RSpec test for the following method from the `{class_name}` class.
- Use FactoryBot where needed
- Cover normal and edge-case behavior
- Do NOT include any explanations
- Do NOT use markdown formatting or code fences
- Make sure to reference the class by its fully qualified name: {class_name}

Here is the method:

{method_code}

Return only raw Ruby code that could be pasted directly into a _spec.rb file.
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



def generate_and_write_rspec_test(class_name: str, method_name: str, method_code: str, app_path: str, generate_rspec_block) -> str:
    spec_path = get_spec_path(app_path)
    rails_root = os.getenv("RAILS_REPO_PATH")
    if not rails_root:
        raise RuntimeError("RAILS_REPO_PATH not set")

    abs_spec_path = os.path.join(rails_root, spec_path)
    ensure_spec_file_exists(abs_spec_path, class_name)

    inferred_constant = infer_ruby_constant_from_path(app_path)
    prompt = build_rspec_prompt(inferred_constant, method_name, method_code)
    raw_test_output = generate_rspec_block(prompt)
    print("🧾 Raw AI output:\n", raw_test_output)
    test_block = strip_markdown_fences(raw_test_output)

    # Ensure RSpec.describe line is correct
    test_block = re.sub(
        r"RSpec\.describe\s+[A-Za-z0-9_:]+",
        f"RSpec.describe {inferred_constant}",
        test_block
    )

    print("📦 Final test block to write:\n", test_block)
    append_test_to_spec(abs_spec_path, test_block)

    # Cleanup: remove old empty stubs like `RSpec.describe X do\nend`
    with open(abs_spec_path, "r+") as f:
        content = f.read()
        cleaned = re.sub(r"RSpec\.describe\s+\w+,\s+type: :\w+\s+do\n\s*end\n*", "", content)
        f.seek(0)
        f.write(cleaned)
        f.truncate()

    return spec_path

def guessed_class_name_from_path(filepath: str) -> str:
    filename = os.path.basename(filepath).replace(".rb", "")
    return ''.join(word.capitalize() for word in filename.split('_'))

def run_spec(spec_path: str) -> bool:
    rails_root = os.getenv("RAILS_REPO_PATH")
    if not rails_root:
        print("❌ RAILS_REPO_PATH not set in environment. Skipping spec run.")
        return False

    abs_spec_path = os.path.join(rails_root, spec_path)
    if not os.path.exists(abs_spec_path):
        print(f"❌ Spec file not found at: {abs_spec_path}")
        return False

    # 👇 Add env overrides to disable Datadog
    env = os.environ.copy()
    env.update({
        "DD_TRACE_ENABLED": "false",
        "DD_INSTRUMENTATION_TELEMETRY_ENABLED": "false",
        "DD_REMOTE_CONFIGURATION_ENABLED": "false",
    })

    result = subprocess.run(
        ["bundle", "exec", "rspec", abs_spec_path],
        cwd=rails_root,
        env=env
    )
    return result.returncode == 0

