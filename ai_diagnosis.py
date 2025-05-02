from analyze_error import diagnose_log

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
        return [line for line in corrected.splitlines() if line.strip()]
    except Exception as e:
        print(f"⚠️ Failed to validate Ruby method with AI: {e}")
        return method_code_lines
