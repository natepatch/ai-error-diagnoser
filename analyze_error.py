import requests

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "mistral"

def diagnose_log(message: str, stack_trace: str = None, code_context: str = None) -> str:
    def trim(text):
        lines = text.splitlines()
        filtered = [
            line for line in lines
            if "Error" in line or "Exception" in line or "undefined method" in line or "uninitialized constant" in line
        ]
        return "\n".join(filtered if filtered else lines[:3])

    trimmed_message = trim(message)
    trimmed_stack = trim(stack_trace or "")

    prompt = f"""
You are a senior Ruby on Rails developer.

An error has occurred in a production system. Here are the details:

🚨 Error Message:
{trimmed_message}

📚 Stack Trace:
{trimmed_stack if trimmed_stack else "Not available."}

{f"🧩 Code Context:\n{code_context}" if code_context else ""}

👉 What caused this error, and how should a developer fix it? Be specific.
""".strip()

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

    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")

    return response.json()["response"].strip()
