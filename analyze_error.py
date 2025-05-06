import os
import requests
import time
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "mistral")  # or "gpt-4"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-1106-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if MODEL_BACKEND == "gpt-4":
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

def extract_ruby_code_block(response: str) -> str:
    stripped_lines = []
    for line in response.splitlines():
        match = re.match(r"^\s*\d+:\s*(.*)", line)
        stripped_lines.append(match.group(1) if match else line)
    stripped_response = "\n".join(stripped_lines)

    # Match ```ruby\n<code>```
    match = re.search(r"(def\s+\w+.*?end)", stripped_response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: any fenced code block
    match = re.search(r"```(.*?)```", stripped_response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Final fallback: detect method by def...end
    match = re.search(r"(^\s*def\s+\w+.*?^end\s*$)", stripped_response, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()

    return ""

def diagnose_log(
        message: str, stack_trace: str = None, code_context: str = None
) -> str:
    def trim(text: str, max_lines: int = 20) -> str:
        lines = text.splitlines()
        filtered = [
            line
            for line in lines
            if "Error" in line
               or "Exception" in line
               or "undefined method" in line
               or "uninitialized constant" in line
        ]
        result = filtered if filtered else lines[:max_lines]
        return "\n".join(result[:max_lines])

    def ask_model(prompt_text: str) -> str:
        if MODEL_BACKEND == "gpt-4":
            print("🤖 Using GPT-4 via OpenAI API")
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior Ruby on Rails developer.",
                    },
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        else:
            print(f"🤖 Using {MODEL_BACKEND} via Ollama at {OLLAMA_HOST}")
            response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": MODEL_BACKEND,  # dynamic model name
                    "prompt": prompt_text,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 1024},
                },
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama returned {response.status_code}: {response.text}"
                )
            return response.json()["response"].strip()


    trimmed_message = trim(message, 10)
    trimmed_stack = trim(stack_trace or "", 20)

    if code_context and len(code_context) > 3000:
        code_context = code_context[:3000] + "\n... (code context truncated)"

    # 🔍 Prompt for explanation + initial fix
    initial_prompt = f"""
You are a senior Ruby on Rails developer.

Your task is to diagnose and fix the following error. This app uses:
- Ruby {os.getenv("RUBY_VERSION", "2.7")}
- Rails {os.getenv("RAILS_VERSION", "7.1")}
- GraphQL (graphql-ruby gem)
- ActiveRecord with PostgreSQL
1. Diagnose the root cause of the error using the message, stack trace, and code context.


Context:
- Assume the app is a standard Ruby on Rails monolith unless stated otherwise.
- Follow best practices: avoid swallowing errors silently, prefer clear control flow, and handle nils safely.
- If a `NullObject` pattern is appropriate, use it explicitly.
- When changing method signatures, explain why in your reasoning.- Avoid `rescue nil` and silent failures.
- Prefer `safe_navigation (&.)` over nil checks unless it harms clarity.
- When uncertain about a model method, use ActiveRecord-style access patterns.

---

🧨 Error Message:
{trimmed_message}

📉 Stack Trace:
{trimmed_stack or "Not available"}

{f"🧩 Code Context:\n{code_context}" if code_context else ""}

---

🎯 Instructions:
1. Identify what likely caused the error based on the stack trace and context.
2. Explain briefly what the issue is in production terms.
3. Propose a fix that is safe, idiomatic, and Rails-appropriate.
4. Then return the corrected Ruby code in triple backticks with `ruby` tag.

Example:

Explanation...

```ruby
# fixed code
```
""".strip()

    start = time.time()
    initial_response = ask_model(initial_prompt)
    elapsed = time.time() - start
    approx_tokens = len(initial_prompt.split())

    print(f"🧮 Estimated token count: ~{approx_tokens} tokens")
    print(f"⏱️ AI responded in {elapsed:.2f} seconds.\n")
    print("🧠 Full AI response from prompt:\n")
    print(initial_response)
    print("-" * 40)

    # ✅ Extract code and explanation
    ruby_code = extract_ruby_code_block(initial_response)

    if not ruby_code:
        print("❌ No Ruby code block found in AI response.")
        return None

    # 🧪 Optional second-pass refinement
    review_prompt = f"""
You are reviewing a Ruby code fix for a production GraphQL app.

Fix quality criteria:
- The code must be idiomatic Ruby.
- It should handle nils safely and be readable.
- Avoid rescue blocks that suppress errors silently.
- Make sure the code integrates with Rails/GraphQL conventions.

--- BEGIN FIX ---
{ruby_code}
--- END FIX ---

Please verify and improve it if necessary. Return just the fixed Ruby code.

✅ No explanation
✅ No markdown
❌ Do not include fences
""".strip()

    reviewed_code = ask_model(review_prompt)
    print("✅ Final reviewed Ruby code:")
    print(reviewed_code)

    return reviewed_code.strip()
