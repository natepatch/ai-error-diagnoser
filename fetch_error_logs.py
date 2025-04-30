import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

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
now = datetime.utcnow()
start_time = (now - timedelta(minutes=10)).isoformat() + "Z"

query = 'status:error service:patchwork-on-rails'

payload = {
    "time": {
        "from": start_time,
        "to": now.isoformat() + "Z"
    },
    "query": query,
    "limit": 10
}

url = f"{DATADOG_SITE}/api/v1/logs-queries/list"

response = requests.post(
    url,
    headers=headers,
    json=payload,
)

if response.status_code != 200:
    print("❌ Failed to fetch logs:", response.status_code, response.text)
    exit(1)

logs = response.json().get("logs", [])
print(f"✅ Fetched {len(logs)} error logs.\n")

for log in logs:
    content = log.get("content", {})
    print("--- Error Log ---")
    print("Timestamp:", content.get("timestamp"))
    print("Message:", content.get("message"))
    print()
