import os
from search_similar_code import search_similar_snippets

CONTEXT_HINT = os.getenv("PROJECT_CONTEXT_HINT", "")

def build_diagnosis_prompt(
        message: str,
        stack_trace: str = "",
        code_context: str = "",
        runtime_info: dict = None
) -> str:
    similar_snippets = search_similar_snippets(f"{message}\n{stack_trace}", top_k=3)
    similar_text = "\n\n".join([f"# Related snippet {i+1}:\n{snippet}" for i, snippet in enumerate(similar_snippets)])

    code_section = f"🧩 Code Context:\n{code_context}" if code_context else ""
    similar_section = f"🔍 Similar Code from Codebase:\n{similar_text}" if similar_snippets else ""

    runtime_section = ""
    if runtime_info:
        runtime_lines = [f"- {key}: {value}" for key, value in runtime_info.items()]
        runtime_section = f"\n🧠 Runtime Variable Info:\n" + "\n".join(runtime_lines)

    return f"""
You are a senior Ruby on Rails developer.

Your task is to diagnose and fix the following error. This app uses:
- Ruby {os.getenv("RUBY_VERSION", "2.7")}
- Rails {os.getenv("RAILS_VERSION", "7.1")}
- GraphQL (graphql-ruby gem)
- ActiveRecord with PostgreSQL

Context:
- This is a Ruby on Rails monolith using standard patterns: ActiveRecord, GraphQL, and service objects.
- Follow idiomatic Ruby and Rails practices: clear control flow, avoid silent failures, and handle `nil` safely.
- Only return `nil` when the method is explicitly expected to support it — otherwise raise a descriptive error or use a `NullObject`.
- If a method relies on an associated object or dependency being present (e.g. user, agency, organisation), and that assumption fails, treat it as a bug unless the surrounding logic handles it.
- Avoid masking deeper issues with `&.` unless the nil case is explicitly valid in the domain logic.
- Raise descriptive `GraphQL::ExecutionError` exceptions for client-facing APIs when returning `nil` would violate the contract.

---
{CONTEXT_HINT}

🧨 Error Message:
{message}

📉 Stack Trace:
{stack_trace or "Not available"}

{code_section}

{runtime_section}

{similar_section}

---

🎯 Instructions:
1. Identify what likely caused the error based on the stack trace and context.
2. Explain briefly what the issue is in production terms.
3. Propose a fix that is safe, idiomatic, and Rails-appropriate.
4. Then return the corrected Ruby code in triple backticks with `ruby` tag.
4. **You are fixing a full method. Always include both `def` and `end`. Do not remove the method definition.**
""".strip()
