import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "codellama:instruct",
        "prompt": "How do I fix a NoMethodError in Rails?",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 256
        }
    }
)

print(response.status_code)
print(response.json()["response"].strip())
