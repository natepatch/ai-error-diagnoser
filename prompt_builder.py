import os

def build_diagnosis_prompt(message: str, stack: str, code_context: str = None, ruby_version: str = "2.7", rails_version: str = "7.1") -> str:
    context_hint = os.getenv("PROJECT_CONTEXT_HINT", "")

    if code_context and len(code_context) > 3000:
        code_context = code_context[:3000] + "\n... (code context truncated)"

    return f"""
You are a senior Ruby on Rails developer.

Your task is to diagnose and fix the following error. This app uses:
- Ruby {ruby_version}
- Rails {rails_version}
- GraphQL (graphql-ruby gem)
- ActiveRecord with PostgreSQL

Context:
- Assume the app is a standard Ruby on Rails monolith unless stated otherwise.
- Follow best practices: avoid swallowing errors silently, prefer clear control flow, and handle nils safely.
- If a `NullObject` pattern is appropriate, use it explicitly.
- When changing method signatures, explain why in your reasoning.

---
{context_hint}

🧨 Error Message:
{message}

📉 Stack Trace:
{stack or "Not available"}

{f"🧩 Code Context:\n{code_context}" if code_context else ""}

---

🎯 Instructions:
1. Identify what likely caused the error based on the stack trace and context.
2. Explain briefly what the issue is in production terms.
3. Propose a fix that is safe, idiomatic, and Rails-appropriate.
4. You are fixing a full method. Always include both `def` and `end`. Do not remove the method definition.
5. Then return the corrected Ruby code in triple backticks with `ruby` tag.
""".strip()
