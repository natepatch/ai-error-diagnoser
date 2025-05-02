import subprocess
import tempfile
import os

def validate_with_rubocop(ruby_code: str) -> tuple[bool, str]:
    """
    Run RuboCop against a given Ruby method string.
    Returns (is_valid, output)
    """
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".rb", delete=False) as tmp_file:
        tmp_file.write(ruby_code)
        tmp_file.flush()
        tmp_path = tmp_file.name

    try:
        result = subprocess.run(
            ["rubocop", "--force-exclusion", "--format", "simple", "--only", "Layout,Style,Lint", tmp_path],
            capture_output=True,
            text=True,
            timeout=10
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
        # Run autocorrect
        subprocess.run(
            ["rubocop", "--auto-correct", "--only", "Layout,Style,Lint", tmp_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Read corrected content
        with open(tmp_path, "r") as f:
            corrected_code = f.read()

        return corrected_code.strip()

    except Exception as e:
        print(f"❌ RuboCop autocorrect failed: {e}")
        return ruby_code
    finally:
        os.remove(tmp_path)
