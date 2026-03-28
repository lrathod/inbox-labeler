# Gmail Inbox AI Labeler 🦾📧

An AI-powered Gmail inbox organizer that uses **Claude Sonnet 4.6** to automatically classify and label your emails based on importance, category, and action required.

## 🚀 Features
- **Intelligent Classification**: Uses frontier AI to understand email context.
- **Efficient Filtering**: Server-side Gmail searching to skip already-labeled mail.
- **Delta Runs**: Only processes new, unlabeled emails to save on API costs.
- **Automation Ready**: Includes scripts for daily automation via `cron`.
- **Clean UI**: Uses a organized `AI/` label hierarchy without emojis for maximum stability.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- Python 3.10+
- A Google Cloud Project with the **Gmail API** enabled.
- An **Anthropic API Key**.

### 2. Installation
Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/YOUR_USERNAME/inbox-labeler.git
cd inbox-labeler
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # If requirements.txt exists, or:
pip install anthropic google-api-python-client google-auth-oauthlib google-auth-httplib2
```

### 3. Google API Authentication
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create OAuth 2.0 Credentials (Desktop App).
3. Download the JSON file and save it as `scripts/credentials.json`.
4. Run the authentication script to generate your `token.json`:
   ```bash
   python scripts/setup_gmail.py
   ```

### 4. Configuration
Create a `.env` file in the root directory:
```bash
ANTHROPIC_API_KEY="your-api-key-here"
```

---

## 📖 Usage

### Manual Run
Process the most recent 50 unlabeled emails:
```bash
source .venv/bin/activate
export ANTHROPIC_API_KEY="your-key-here"
python scripts/label_inbox.py --limit 50
```

### Dry Run (Preview only)
```bash
python scripts/label_inbox.py --limit 10 --dry-run
```

### Automation
You can use the provided shell script to automate the process:
```bash
chmod +x scripts/run_labeler.sh
./scripts/run_labeler.sh
```

---

## 📁 Project Structure
- `scripts/label_inbox.py`: Main classification logic.
- `scripts/run_labeler.sh`: Shell wrapper for automation.
- `scripts/setup_gmail.py`: Helper for OAuth2 authentication.
- `.env`: Private environment variables (ignored by git).
- `.gitignore`: Ensures your credentials are never pushed to GitHub.
