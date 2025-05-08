from ai_fixer.rspec_generator import generate_and_write_rspec_test, guessed_class_name_from_path
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_BACKEND = os.getenv("MODEL_BACKEND", "mistral")  # or "gpt-4"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-1106-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if MODEL_BACKEND == "gpt-4":
    client = OpenAI(api_key=OPENAI_API_KEY)

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

def generate_rspec_block(prompt: str) -> str:
    return ask_model(prompt)

if __name__ == "__main__":
    from ai_fixer.rspec_generator import run_spec

    class_name = "User"
    method_name = "deactivate_account"
    method_code = """
def deactivate_account
  update!(deactivated: true)
end
"""
    app_path = "app/models/user.rb"

    spec_path = generate_and_write_rspec_test(
        class_name=class_name,
        method_name=method_name,
        method_code=method_code,
        app_path=app_path,
        generate_rspec_block=generate_rspec_block,
    )

    if run_spec(spec_path):
        print("✅ Spec passed — safe to create PR")
    else:
        print("❌ Spec failed — aborting PR")
