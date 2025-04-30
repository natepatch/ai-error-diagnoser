# 🧠 AI Error Diagnoser for Rails Monolith

This project fetches recent production errors from Datadog logs, diagnoses their root cause using a local AI model (via [Ollama](https://ollama.com)), and (optionally) inspects related source code from GitHub to suggest fixes.

---

## 🚀 What It Does

- ✅ Pulls recent error logs from Datadog
- ✅ Uses a local LLM (e.g. Mistral) to analyze the problem
- ✅ Fetches relevant code files from GitHub (optional)
- ✅ Prepares context-aware diagnosis
- 🔜 Creates GitHub pull requests (coming soon)

---

## 🧰 Requirements

- Python 3.8+
- [Ollama](https://ollama.com/download) installed and running
- A `.env` file with your API keys

---

## 📦 Installation

```bash
git clone https://github.com/natepatch/ai-error-diagnoser.git
cd ai-error-diagnoser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
