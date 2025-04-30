import requests

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "mistral"

def diagnose_log(message: str) -> str:
    lines = message.splitlines()

    filtered = [
        line for line in lines
        if "Error" in line or "Exception" in line or "undefined method" in line or "uninitialized constant" in line
    ]

    if not filtered:
        filtered = lines[:3]

    trimmed_message = "\n".join(filtered)

    prompt = f"""
Rails error log:

{trimmed_message}

What caused it and how can a developer fix it?
"""

    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": MODEL_NAME,
            "prompt": prompt.strip(),
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
