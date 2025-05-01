import requests
import time

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "mistral"

def diagnose_log(message: str, stack_trace: str = None, code_context: str = None) -> str:
    def trim(text: str, max_lines: int = 20) -> str:
        lines = text.splitlines()
        filtered = [
            line for line in lines
            if "Error" in line or "Exception" in line or "undefined method" in line or "uninitialized constant" in line
        ]
        result = filtered if filtered else lines[:max_lines]
        if len(result) > max_lines:
            result = result[:max_lines]
        return "\n".join(result)

    trimmed_message = trim(message, 10)
    trimmed_stack = trim(stack_trace or "", 20)

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
    elapsed = time.time() - start

    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")

    approx_tokens = len(prompt.split())  # crude approximation
    print(f"🧮 Estimated token count: ~{approx_tokens} tokens")

    print(f"⏱️ AI responded in {elapsed:.2f} seconds.\n")
    return response.json()["response"].strip()
