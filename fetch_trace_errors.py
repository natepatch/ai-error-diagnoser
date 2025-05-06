
import os
import requests
import json
import hashlib
import re
import traceback
from dotenv import load_dotenv
from analyze_error import diagnose_log
from github_code_fetcher import fetch_code_context
from github_client import get_repo, get_existing_pr, submit_pr_to_github
from pr_manager import create_pull_request

load_dotenv()

DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY")
DATADOG_SITE = os.getenv("DATADOG_SITE", "https://api.datadoghq.eu")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "patchworkhealth/PatchworkOnRails"

if not DATADOG_API_KEY or not DATADOG_APP_KEY or not GITHUB_TOKEN:
    raise RuntimeError("❌ Missing required environment variables.")

repo = get_repo(GITHUB_TOKEN, REPO_NAME)

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
                "query": "env:prod status:error service:patchwork-on-rails -operation_name:rack.request"
            },
            "options": {
                "timezone": "GMT"
            },
            "page": {
                "limit": 3
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
            any(normalized.startswith(prefix) for prefix in VALID_PATH_PREFIXES) and
            not any(bad in normalized for bad in INVALID_PATH_PARTS)
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

        existing_pr = get_existing_pr(repo, error_id)
        if existing_pr:
            print(f"⚠️ Skipping — PR already exists: {existing_pr.html_url}")
            continue

        message = error_info.get("message", "")
        stack = error_info.get("stack", "")
        code_context = None

        raw_filepath = error_info.get("file", "")
        filepath = raw_filepath.lstrip("/")
        while filepath.startswith("app/app/"):
            filepath = filepath.replace("app/", "", 1)

        line_number = None

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
        diagnosis_text, final_code_str = diagnose_log(message, stack_trace=stack, code_context=code_context)

        if not diagnosis_text or not final_code_str:
            print("⚠️ Skipping PR — AI failed to return usable explanation or code.")
            continue

        print("🧪 Extracted replacement code:\n")
        print(final_code_str)

        try:
            print(f"📂 File path to be used in PR: {filepath}")
            create_pull_request(filepath, line_number, diagnosis_text, final_code_str, error_id)
            print(f"✅ Pull request created for error ID: {error_id}")
        except Exception as e:
            print(f"❌ Failed to create PR: {e}")
            traceback.print_exc()
    else:
        print("\n⚠️ No error info in `custom.error`")

    print("-" * 60)
