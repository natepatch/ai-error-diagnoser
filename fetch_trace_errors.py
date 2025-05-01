import os
import requests
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY")
DATADOG_SITE = os.getenv("DATADOG_SITE", "https://api.datadoghq.eu")
range_minutes = int(os.getenv("DATADOG_LOG_RANGE_MINUTES", "10"))

headers = {
    "DD-API-KEY": DATADOG_API_KEY,
    "DD-APPLICATION-KEY": DATADOG_APP_KEY,
    "Content-Type": "application/json"
}

now = datetime.now(timezone.utc)
start_time = (now - timedelta(minutes=range_minutes)).isoformat()

# ✅ Wrap payload in `data` to conform to Datadog Spans API
payload = {
    "data": {
        "type": "search_request",
        "attributes": {
            "filter": {
                "from": start_time,
                "to": now.isoformat(),
                "query": "service:patchwork-on-rails status:error"
            },
            "page": {
                "limit": 1
            },
            "sort": "-timestamp"
        }
    }
}

url = f"{DATADOG_SITE}/api/v2/spans/events/search"

response = requests.post(url, headers=headers, json=payload)

if response.status_code != 200:
    print("❌ Failed to fetch spans:", response.status_code, response.text)
    exit(1)

logs = response.json().get("data", [])
print(f"✅ Fetched {len(logs)} span(s).\n")

for log in logs:
    attr = log.get("attributes", {})
    tags = attr.get("tags", [])
    trace_id = attr.get("trace_id")
    span_id = attr.get("span_id")
    service = attr.get("service")
    resource = attr.get("resource_name")
    start = attr.get("start_timestamp")
    end = attr.get("end_timestamp")
    span_type = attr.get("type")

    print("🧩 Span")
    print(f"Service: {service}")
    print(f"Resource: {resource}")
    print(f"Trace ID: {trace_id}")
    print(f"Span ID: {span_id}")
    print(f"Start: {start}")
    print(f"End: {end}")
    print(f"Type: {span_type}")
    print(f"Tags: {tags}")

    # 🕵️ Show raw for inspection
    print("\n🔍 Raw Attributes:")
    print(json.dumps(attr, indent=2))

    break  # Only show the first one for now
