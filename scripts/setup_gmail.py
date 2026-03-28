"""
Gmail OAuth2 Setup Script
=========================
Run this ONCE to authorize Gmail access for the inbox labeler.

BEFORE RUNNING THIS:
1. Go to https://console.cloud.google.com/
2. Create a new project (or select an existing one)
3. Enable the Gmail API:
   - APIs & Services → Library → search "Gmail API" → Enable
4. Create OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Download the JSON file and rename it to: credentials.json
5. Place credentials.json in the same folder as this script (scripts/)
6. Run: python setup_gmail.py

A browser window will open asking you to sign in and grant access.
A token.json file will be saved — this is your auth token for future runs.
"""

import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail scopes needed
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify",
]

SCRIPT_DIR = Path(__file__).parent
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"


def setup():
    if not CREDENTIALS_FILE.exists():
        print("❌ ERROR: credentials.json not found!")
        print(f"   Expected at: {CREDENTIALS_FILE}")
        print()
        print("   Please follow these steps:")
        print("   1. Go to https://console.cloud.google.com/")
        print("   2. Create a project and enable the Gmail API")
        print("   3. Create OAuth 2.0 Desktop credentials")
        print("   4. Download and save as credentials.json in this folder")
        sys.exit(1)

    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing existing token...")
            creds.refresh(Request())
        else:
            print("🌐 Opening browser for Gmail authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    print(f"✅ Authentication successful! Token saved to: {TOKEN_FILE}")
    print("   You can now run: python label_inbox.py")


if __name__ == "__main__":
    setup()
