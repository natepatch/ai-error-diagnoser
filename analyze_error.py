import requests

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "mistral"

def diagnose_log(message: str, code_context: str = None) -> str:
    lines = message.splitlines()

    filtered = [
        line for line in lines
        if "Error" in line or "Exception" in line or "undefined method" in line or "uninitialized constant" in line
    ]

    if not filtered:
        filtered = lines[:3]

    trimmed_message = "\n".join(filtered)

    prompt = f"""
You are a senior Ruby on Rails developer.

Rails error log:
{trimmed_message}

{f"Relevant code:\n{code_context}" if code_context else ""}

What caused this error, and how should a developer fix it?
""".strip()

    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 256
            }
        }
    )

    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")

    return response.json()["response"].strip()
