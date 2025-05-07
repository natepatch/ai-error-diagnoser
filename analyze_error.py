import os
import requests
import time
import re
from openai import OpenAI
from dotenv import load_dotenv
from prompt_builder import build_diagnosis_prompt

load_dotenv(override=True)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "mistral")  # or "gpt-4"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-1106-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if MODEL_BACKEND == "gpt-4":
    client = OpenAI(api_key=OPENAI_API_KEY)


# 🔁 Reusable for general-purpose prompting (used by validate_and_correct_ruby_code)
def ask_model(prompt_text: str) -> str:
    if MODEL_BACKEND == "gpt-4":
        print("🤖 Using GPT-4 via OpenAI API")
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a senior Ruby on Rails developer."},
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
                "model": MODEL_BACKEND,
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

    match = re.search(r"(def\s+\w+.*?end)", stripped_response, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```(.*?)```", stripped_response, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"(^\s*def\s+\w+.*?^end\s*$)", stripped_response, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()

    return ""


def diagnose_log(message: str, stack_trace: str = None, code_context: str = None, runtime_info: dict = None):
    def trim(text: str, max_lines: int = 20) -> str:
        lines = text.splitlines()
        filtered = [
            line for line in lines
            if "Error" in line or "Exception" in line or "undefined method" in line or "uninitialized constant" in line
        ]
        result = filtered if filtered else lines[:max_lines]
        return "\n".join(result[:max_lines])

    trimmed_message = trim(message, 10)
    trimmed_stack = trim(stack_trace or "", 20)

    initial_prompt = build_diagnosis_prompt(
        trimmed_message,
        trimmed_stack,
        code_context,
        runtime_info=runtime_info
    )

    print("\n📨 Final prompt sent to AI:\n")
    print(initial_prompt)

    start = time.time()
    initial_response = ask_model(initial_prompt)
    elapsed = time.time() - start
    print(f"⏱️ AI responded in {elapsed:.2f} seconds.")
    print("🧠 Full AI response from prompt:\n")
    print(initial_response)
    print("-" * 40)

    ruby_code = extract_ruby_code_block(initial_response)
    if not ruby_code:
        print("❌ No Ruby code block found in AI response.")
        return None, None

    review_prompt = f"""
You are reviewing a Ruby code fix for a production GraphQL app.

--- BEGIN FIX ---
{ruby_code}
--- END FIX ---

Please verify and improve it if necessary. Return just the fixed Ruby code.
✅ No explanation
✅ No markdown
❌ Do not include fences
""".strip()

    reviewed_code = ask_model(review_prompt)
    return initial_response, reviewed_code.strip()
