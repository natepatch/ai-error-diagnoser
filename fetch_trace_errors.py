import os
import requests
import json
import hashlib
from dotenv import load_dotenv

load_dotenv()

DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY")
DATADOG_SITE = os.getenv("DATADOG_SITE", "https://api.datadoghq.eu")

headers = {
    "DD-API-KEY": DATADOG_API_KEY,
    "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    "Content-Type": "application/json"
}

payload = {
    "data": {
        "type": "search_request",
        "attributes": {
            "filter": {
                "from": "now-15m",
                "to": "now",
                "query": "env:prod status:error service:patchwork-on-rails"
            },
            "options": {
                "timezone": "GMT"
            },
            "page": {
                "limit": 1
            },
            "sort": "timestamp"
        }
    }
}

url = f"{DATADOG_SITE}/api/v2/spans/events/search"

response = requests.post(url, headers=headers, json=payload)

if response.status_code != 200:
    print("❌ Failed to fetch spans:", response.status_code, response.text)
    exit(1)

spans = response.json().get("data", [])
print(f"✅ Fetched {len(spans)} span(s).\n")

def generate_error_id(error_info: dict) -> str:
    components = [
        error_info.get("message", ""),
        error_info.get("file", ""),
        error_info.get("stack", "")
    ]
    return hashlib.md5("::".join(components).encode()).hexdigest()

for span in spans:
    attr = span.get("attributes", {})
    trace_id = attr.get("trace_id")
    span_id = attr.get("span_id")
    resource = attr.get("resource_name")
    custom = attr.get("custom", {})
    error_info = custom.get("error", {})

    print("🧩 Span Error Summary:")
    print(f"Trace ID: {trace_id}")
    print(f"Span ID: {span_id}")
    print(f"Resource: {resource}")

    if error_info:
        error_id = generate_error_id(error_info)
        print(f"Issue Fingerprint: {error_id}")

        print("\n💥 Error Message:")
        print(error_info.get("message", "—"))

        print("\n📚 Stack Trace:")
        print(error_info.get("stack", "—"))
    else:
        print("\n⚠️ No error info in `custom.error`")

    print("-" * 60)
