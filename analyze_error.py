import requests
import time

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "mistral"

def diagnose_log(message: str, stack_trace: str = None, code_context: str = None) -> str:
    def trim(text):
        lines = text.splitlines()
        filtered = [
            line for line in lines
            if "Error" in line or "Exception" in line or "undefined method" in line or "uninitialized constant" in line
        ]
        return "\n".join(filtered if filtered else lines[:15])

    # Trim the error message
    trimmed_message = trim(message)

    # Trim and truncate the stack trace
    trimmed_stack = trim(stack_trace or "")
    stack_lines = trimmed_stack.splitlines()
    if len(stack_lines) > 20:
        trimmed_stack = "\n".join(stack_lines[:20]) + "\n... (stack trace truncated)"

    # Optionally trim code context if it’s too large
    if code_context and len(code_context) > 3000:
        code_context = code_context[:3000] + "\n... (code context truncated)"

    prompt = f"""
You are a very experienced Ruby on Rails developer.

An error has occurred in a production system. Here are the details:

🚨 Error Message:
{trimmed_message}

📚 Stack Trace:
{trimmed_stack if trimmed_stack else "Not available."}

{f"🧩 Code Context:\n{code_context}" if code_context else ""}

👉 What caused this error, and how should a developer fix it? Be specific.
""".strip()

    start = time.time()

    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512
            }
        }
    )

    duration = time.time() - start

    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")

    result = response.json()["response"].strip()

    return f"{result}\n\n⏱️ AI response generated in {duration:.2f} seconds."
