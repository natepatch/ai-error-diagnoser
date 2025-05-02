import re

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
