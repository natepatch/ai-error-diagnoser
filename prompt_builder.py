import os
import re
from dotenv import load_dotenv
from search_similar_code import search_similar_snippets

load_dotenv()

CONTEXT_HINT = os.getenv("PROJECT_CONTEXT_HINT", "")

def extract_keywords(*texts, max_keywords=15):
    raw_text = " ".join(texts)

    # Extract tokens
    keywords = set()

    # Match Ruby-style symbols or method names
    keywords.update(re.findall(r'[:\.]?[a-z_]{3,}', raw_text))

    # Match constants or class/module names
    keywords.update(re.findall(r'\b[A-Z][A-Za-z:]{2,}\b', raw_text))

    # Match common context and GraphQL references
    special_patterns = [
        r"context\[:[a-z_]+\]",
        r"\.becomes\(",
        r"GraphQL::ExecutionError",
        r"\.find_by\(",
        r"params\[:[a-z_]+\]"
    ]
    for pattern in special_patterns:
        matches = re.findall(pattern, raw_text)
        keywords.update(matches)

    # Normalize, deduplicate, and rank
    normalized = list(dict.fromkeys([kw.strip(":.()").lower() for kw in keywords]))
    return normalized[:max_keywords]


def infer_domain_hints(message: str, stack_trace: str, code_context: str) -> str:
    hints = []

    if "context[:current_user]" in code_context or "context[:current_user]" in stack_trace:
        hints.append("- `context[:current_user]` may be nil. Always check for presence and raise an appropriate error if missing.")
    if ".becomes(" in code_context:
        hints.append("- Avoid using `.becomes(...)` unless polymorphic casting is explicitly safe and required.")
    if "find_by(" in code_context:
        hints.append("- Prefer `.find_by(...)` over direct foreign key assignment unless the association is defined.")

    if hints:
        return "Domain Assumptions:\n" + "\n".join(hints) + "\n"
    return ""

def build_diagnosis_prompt(
        message: str,
        stack_trace: str = "",
        code_context: str = "",
        runtime_info: dict = None
) -> str:
    keywords = extract_keywords(message, stack_trace, code_context)
    keyword_hint = ", ".join(keywords)

    query = f"""
{message}
{stack_trace}

Relevant terms: {keyword_hint}
""".strip()

    TOP_K = int(os.getenv("SIMILAR_SNIPPETS_LIMIT", "5"))
    similar_snippets = search_similar_snippets(query, top_k=TOP_K)
    similar_text = "\n\n".join([f"# Related snippet {i+1}:\n{snippet}" for i, snippet in enumerate(similar_snippets)])

    code_section = f"🧩 Code Context:\n{code_context}" if code_context else ""
    similar_section = f"🔍 Similar Code from Codebase:\n{similar_text}" if similar_snippets else ""

    runtime_section = ""
    if runtime_info:
        runtime_lines = [f"- {key}: {value}" for key, value in runtime_info.items()]
        runtime_section = f"\n🧠 Runtime Variable Info:\n" + "\n".join(runtime_lines)

    domain_hints = infer_domain_hints(message, stack_trace, code_context)

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
- If a method relies on an associated object or dependency being present, treat missing dependencies as errors unless handled explicitly.
- Raise descriptive `GraphQL::ExecutionError` exceptions for client-facing APIs when returning `nil` would violate the contract.

{domain_hints}
{CONTEXT_HINT}

🧨 Error Message:
{message}

📉 Stack Trace:
{stack_trace or "Not available"}

{code_section}

{runtime_section}

{similar_section}

---

Please analyse both the 🧩 Code Context and 🔍 Similar Code from Codebase sections to inform your diagnosis and proposed fix. Prioritize patterns seen in Similar Code if they help resolve the error or demonstrate idiomatic Rails usage.

🎯 Instructions:
1. Identify what likely caused the error based on the stack trace and context.
2. Explain briefly what the issue is in production terms.
3. Propose a fix that is safe, idiomatic, and Rails-appropriate.
4. Then return the corrected Ruby code in triple backticks with `ruby` tag.
4. **You are fixing a full method. Always include both `def` and `end`. Do not remove the method definition.**
""".strip()
