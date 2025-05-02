import subprocess
import tempfile
import os

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
        return result.returncode == 0, result.stdout.strip()
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
            return f.read()
    except Exception as e:
        print(f"❌ RuboCop autocorrect failed: {e}")
        return ruby_code
    finally:
        os.remove(tmp_path)
