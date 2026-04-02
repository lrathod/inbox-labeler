# Gmail Inbox Labeler - Project Guidelines

## Project Overview
An AI-powered Gmail classification system that uses Claude to intelligently label emails in the user's inbox under an `AI/` namespace. It categorizes emails into priority, personal, financial, official, informational, and junk labels.

## Tech Stack
- **Language**: Python 3.8+
- **APIs**: Gmail API (Google Cloud), Anthropic API (Claude)
- **Environment**: Virtual environment (`.venv`) with credentials in `.env` or `scripts/`

## Quick Start & Common Commands
Always run commands from the `inbox-labeler/scripts/` directory or ensure paths are correct.

### Setup & Authentication
```bash
# Install dependencies
pip install -r inbox-labeler/scripts/requirements.txt

# Run Gmail authentication (first time only)
python inbox-labeler/scripts/setup_gmail.py
```

### Running the Labeler
```bash
# Standard run (50 most recent)
python inbox-labeler/scripts/label_inbox.py

# Dry run (preview without applying)
python inbox-labeler/scripts/label_inbox.py --dry-run

# Custom limit and unread only
python inbox-labeler/scripts/label_inbox.py --limit 100 --unread-only
```

## Coding Standards & Guidelines
- **Python Style**: Follow PEP 8 guidelines.
- **Type Hints**: Use type hints for all function signatures.
- **Error Handling**: Use try-except blocks for API calls (Gmail and Anthropic) with descriptive error messages.
- **Environment Variables**: Never hardcode API keys; use `.env` and `python-dotenv`.
- **Classification Specifics**: 
  - `AI/🏦 Banking` is for banks/credit cards specifically.
  - `AI/💬 Personal` is for real human-to-human messages only.
  - `AI/🏛️ Government` covers official communication (.gov, .nic).
  - Use the most specific matching label when multiple categories apply.
- **Testing**: Before large-scale modifications, run with the `--dry-run` flag to verify classification logic.
