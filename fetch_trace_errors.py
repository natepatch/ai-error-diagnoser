import os
import requests
import json
import hashlib
import re
from dotenv import load_dotenv
from analyze_error import diagnose_log
from github_code_fetcher import fetch_code_context
from pr_manager import has_existing_pr, create_pull_request

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
                "from": "now-24h",
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

VALID_PATH_PREFIXES = ["app/", "lib/", "config/", "db/"]
INVALID_PATH_PARTS = ["/gems/", "/usr/", "/ruby/", "/vendor/", "<", "(eval)"]

def is_valid_code_path(path: str) -> bool:
    if not path:
        return False
    normalized = path.lstrip("/")
    return (
            any(normalized.startswith(prefix) for prefix in VALID_PATH_PREFIXES)
            and not any(bad in normalized for bad in INVALID_PATH_PARTS)
    )

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

    print("🎩 Span Error Summary:")
    print(f"Trace ID: {trace_id}")
    print(f"Span ID: {span_id}")
    print(f"Resource: {resource}")

    if error_info:
        error_id = generate_error_id(error_info)
        print(f"Issue Fingerprint: {error_id}")

        if has_existing_pr(error_id):
            print(f"⚠️ Skipping — PR already exists for fingerprint: {error_id}")
            continue

        message = error_info.get("message", "")
        stack = error_info.get("stack", "")
        code_context = None

        raw_filepath = error_info.get("file", "")
        filepath = raw_filepath.lstrip("/")
        while filepath.startswith("app/app/"):
            filepath = filepath.replace("app/", "", 1)

        line_number = None

        # Extract line from stack trace
        if is_valid_code_path(filepath) and stack:
            for line in stack.splitlines():
                if filepath in line:
                    match = re.search(r"{}:(\d+)".format(re.escape(filepath)), line)
                    if match:
                        line_number = int(match.group(1))
                        code_context = fetch_code_context(filepath, line_number)
                        break
        else:
            print(f"⚠️ Skipping — file path not in allowed directories: {raw_filepath}")
            continue

        print("\n🧠 Analyzing error with AI...")
        ruby_code = diagnose_log(message, stack_trace=stack, code_context=code_context)

        if not ruby_code:
            print("⚠️ Skipping PR — no valid Ruby code returned.")
            continue

        print("🧪 Extracted replacement code:\n")
        print(ruby_code)

        try:
            print(f"📂 File path to be used in PR: {filepath}")
            create_pull_request(filepath, line_number, ruby_code, error_id)
            print(f"✅ Pull request created for error ID: {error_id}")
        except Exception as e:
            print(f"❌ Failed to create PR: {e}")
    else:
        print("\n⚠️ No error info in `custom.error`")

    print("-" * 60)
