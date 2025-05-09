# ai_fixer/spec_utils.py
from pathlib import Path
import re

def get_spec_path(app_path: str) -> str:
    p = Path(app_path)
    if "app/" not in app_path:
        raise ValueError(f"Unexpected file path: {app_path}")
    return str(p).replace("app/", "spec/").replace(".rb", "_spec.rb")

def ensure_spec_file_exists(spec_path: str, class_name: str):
    spec_file = Path(spec_path)
    if not spec_file.exists():
        spec_file.parent.mkdir(parents=True, exist_ok=True)
        boilerplate = f"""require 'rails_helper'

RSpec.describe {class_name}, type: :model do
end
"""
        spec_file.write_text(boilerplate)

def append_test_to_spec(spec_path: str, test_code: str):
    with open(spec_path, "a") as f:
        f.write("\n\n")
        f.write(test_code.strip())
        f.write("\n")

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
