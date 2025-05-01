import os
import requests
import time
import re
from openai import OpenAI

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "mistral")  # or "gpt-4"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-1106-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def diagnose_log(message: str, stack_trace: str = None, code_context: str = None) -> str:
    def trim(text: str, max_lines: int = 20) -> str:
        lines = text.splitlines()
        filtered = [
            line for line in lines
            if "Error" in line or "Exception" in line or "undefined method" in line or "uninitialized constant" in line
        ]
        result = filtered if filtered else lines[:max_lines]
        return "\n".join(result[:max_lines])

    def ask_model(prompt_text: str) -> str:
        if MODEL_BACKEND == "gpt-4":
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a senior Ruby on Rails developer."},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.2,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        else:
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt_text,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 1024},
                },
            )
            if response.status_code != 200:
                raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")
            return response.json()["response"].strip()

    def extract_ruby_code_block(response: str) -> str:
        stripped_lines = []
        for line in response.splitlines():
            match = re.match(r"^\s*\d+:\s*(.*)", line)
            stripped_lines.append(match.group(1) if match else line)
        stripped_response = "\n".join(stripped_lines)

        match = re.search(r"```ruby\s+(.*?)\s+```", stripped_response, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"```(.*?)```", stripped_response, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"(^\s*def\s+\w+.*?^end\s*$)", stripped_response, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    def extract_failing_line(stack: str) -> str:
        match = re.search(r"\n(/.*?):(\d+):in `(.*?)'", stack)
        if match:
            path, line_number, method = match.groups()
            return f"{path}:{line_number} in `{method}`"
        return ""

    trimmed_message = trim(message, 10)
    trimmed_stack = trim(stack_trace or "", 20)
    failing_line = extract_failing_line(trimmed_stack)

    if code_context and len(code_context) > 3000:
        code_context = code_context[:3000] + "\n... (code context truncated)"

    extra_hint = ""
    if "undefined method" in trimmed_message and "for nil" in trimmed_message:
        extra_hint = (
            f"This line is failing:\n{failing_line}\n"
            f"With error: `{trimmed_message}`\n\n"
            "This usually means you're calling a method on `nil`.\n"
            "You likely need to use Ruby's safe navigation operator `&.` to guard against nil.\n"
        )

    prompt = f"""
You are a very experienced Ruby on Rails developer.

An error has occurred in a production system. Here are the details:

Error Message:
{trimmed_message}

Stack Trace:
{trimmed_stack if trimmed_stack else "Not available."}

{f"Code Context:\n{code_context}" if code_context else ""}

{extra_hint}

What caused this error, and how should a developer fix it? Be specific. Consider what impact this change has on the system.

Use best practices for Ruby and Rails development:
- Use safe navigation (`&.`) to avoid nil errors
- Prefer guard clauses to nested conditionals
- Use meaningful, descriptive method and variable names
- Keep methods short and single-purpose
- Avoid global state
- Prefer composition over inheritance
- Use `find_by` when querying optional associations
- Use `raise` to fail fast on invalid input
- Respect GraphQL `field` declarations and resolvers
- Format as if run through `rubocop --safe --lint --only Layout,Style,Lint`

Return only the corrected Ruby code — no explanation.
""".strip()

    start = time.time()
    initial_fix = ask_model(prompt)
    elapsed = time.time() - start
    approx_tokens = len(prompt.split())

    print(f"🧮 Estimated token count: ~{approx_tokens} tokens")
    print(f"⏱️ AI responded in {elapsed:.2f} seconds.\n")

    review_prompt = f"""
You are reviewing a Ruby code fix for a GraphQL Ruby on Rails project.

Below is the proposed fix (a partial diff):

--- BEGIN FIX ---
{initial_fix}
--- END FIX ---

Your job is to verify and correct this Ruby method.

Checklist:
1. Does the method correspond to a GraphQL `field` declaration or provide a resolver?
2. Does it preserve original behavior, including type casting, authentication, and return values?
3. Has unnecessary logic been removed? If so, ensure it is not used elsewhere.
4. Is the code idiomatic and valid Ruby that passes `rubocop --safe --lint`?
5. Does it follow common Ruby best practices:
   - safe navigation (`&.`)
   - guard clauses
   - short, clear methods
   - descriptive naming
   - object composition
   - fail-fast logic

✅ Return only the corrected Ruby method
❌ No explanation
❌ No markdown or fences
❌ Do not ignore RuboCop or you'll break the build
""".strip()

    reviewed_response = ask_model(review_prompt)
    print("🧠 Raw AI output:\n")
    print(reviewed_response)

    ruby_code = extract_ruby_code_block(reviewed_response)

    if not ruby_code:
        print("⚠️ No Ruby code extracted from AI output. Skipping PR.")
    else:
        print("🧪 Extracted replacement code:\n")
        print(ruby_code)

    return ruby_code
