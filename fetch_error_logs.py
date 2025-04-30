import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from analyze_error import diagnose_log
from github_code_fetcher import fetch_file_contents

load_dotenv()

DATADOG_SITE = os.getenv("DATADOG_SITE", "https://api.datadoghq.eu")
DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY")

headers = {
    "DD-API-KEY": DATADOG_API_KEY,
    "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    "Content-Type": "application/json"
}

# Use timezone-aware datetime
now = datetime.now(timezone.utc)
range_minutes = int(os.getenv("DATADOG_LOG_RANGE_MINUTES", "10"))
start_time = (now - timedelta(minutes=range_minutes)).isoformat()

query = 'status:error service:patchwork-on-rails'

payload = {
    "time": {
        "from": start_time,
        "to": now.isoformat()
    },
    "query": query,
    "limit": 10
}

url = f"{DATADOG_SITE}/api/v1/logs-queries/list"

response = requests.post(url, headers=headers, json=payload)

if response.status_code != 200:
    print("❌ Failed to fetch logs:", response.status_code, response.text)
    exit(1)

logs = response.json().get("logs", [])
print(f"✅ Fetched {len(logs)} error logs.\n")

seen_messages = set()

for log in logs:
    content = log.get("content", {})
    msg = content.get("message")

    if not msg or msg in seen_messages:
        continue
    seen_messages.add(msg)

    print("--- Error Log ---")
    print("Timestamp:", content.get("timestamp"))
    print("Message:", msg)

    # Hardcoded test file for now
    file_path = "app/workers/external_application.rb"
    code = fetch_file_contents(file_path)

    print("🧠 Thinking...", end="", flush=True)
    try:
        diagnosis = diagnose_log(msg, code_context=code)
        print("\r💡 Diagnosis:")
        if diagnosis.strip():
            print(diagnosis.strip())
        else:
            print("⚠️ No diagnosis returned.")
    except Exception as e:
        print("\n❌ Analysis failed:", e)

    print()
