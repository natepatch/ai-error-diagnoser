# 💡 AI Error Diagnoser for Rails Monolith

This tool diagnoses production errors in a Ruby on Rails monolith by pulling recent errors from Datadog APM, analyzing them using an AI model (local or remote), and automatically generating contextual GitHub pull requests with proposed fixes.

---

## ✨ Features

- ✅ Fetches recent `status:error` spans from Datadog APM
- ✅ Analyzes the root cause using an AI model (Mistral or GPT-4)
- ✅ Enriches errors with GitHub source context
- ✅ Suggests safe Ruby fixes using best practices
- ✅ Validates output with RuboCop (optional)
- ✅ Automatically opens GitHub PRs for valid, clean fixes
- ✅ Fingerprint deduplication to prevent duplicate PRs

---

## 🧰 Requirements

- Python 3.8+
- [Ollama](https://ollama.com/download) running locally **if using Mistral**
- OpenAI API key **if using GPT-4**
- GitHub personal access token with `repo` scope
- Ruby 3.0+ (only needed for local RuboCop validation)
- `.env` file with:

```env
DATADOG_API_KEY=...
DATADOG_APP_KEY=...
DATADOG_SITE=https://api.datadoghq.eu
GITHUB_TOKEN=...
OPENAI_API_KEY=...
MODEL_BACKEND=mistral  # or 'gpt-4'
OPENAI_MODEL=gpt-4-1106-preview
OLLAMA_HOST=http://localhost:11434
```

---

## 📦 Installation

```bash
git clone https://github.com/natepatch/ai-error-diagnoser.git
cd ai-error-diagnoser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Usage

### Run the diagnoser

```bash
python fetch_trace_errors.py
```

This will:
- Fetch recent spans from Datadog with `status:error`
- Analyze errors using your configured model
- (Optionally) fetch matching code lines from GitHub
- Validate and review the fix
- Open a GitHub pull request if valid

---

## 🤖 Model Switching

Use the `MODEL_BACKEND` environment variable:

- `mistral` — local model via [Ollama](https://ollama.com)
- `gpt-4` — uses OpenAI API (`OPENAI_MODEL` required)

---

## 🧪 Optional: RuboCop Validation

If `rubocop` is available in your `PATH`, the tool will:
- Check AI-generated Ruby for lint and format issues
- Skip PR creation if it fails validation

You can install it via:

```bash
gem install rubocop
```

️⃣ Requires Ruby ≥ 2.7 due to `prism` dependency.

---

## 📬 PR Naming & Deduplication

Each error span is fingerprinted by:
- Stack trace
- Message
- File path

A branch is created like `ai/fix-<fingerprint>`. Existing PRs are detected and skipped.

---

## 📌 Roadmap

- [x] GPT-4 + Ollama model switching
- [x] Fingerprint deduplication
- [x] RuboCop validation
- [x] Code context fetching from GitHub
- [x] Pull request creation
- [ ] Auto-detect obsolete methods safely
- [ ] Interactive CLI flow
- [ ] Slack integration

---

## 🧠 Philosophy

This tool isn’t just about AI-generated code — it’s about **context-aware diagnostics** that align with your team’s Ruby, Rails, and GraphQL standards. Every patch is reviewed with discipline and annotated intelligently.

---

## 📞 Need Help?

Open an issue or ping [@natepatch](https://github.com/natepatch).
