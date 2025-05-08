# ai_fixer/spec_utils.py
from pathlib import Path

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
