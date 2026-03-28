"""
Gmail Inbox AI Labeler
======================
Reads your Gmail inbox and uses Claude AI to intelligently classify
and label each email.

Usage:
    python label_inbox.py [options]

Options:
    --limit N          Number of emails to process (default: 50)
    --unread-only      Only process unread emails
    --dry-run          Preview labels without applying them to Gmail
    --batch-size N     Emails per Claude API call (default: 5)

Examples:
    python label_inbox.py
    python label_inbox.py --limit 100 --unread-only
    python label_inbox.py --dry-run --limit 20
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
TOKEN_FILE = SCRIPT_DIR / "token.json"
CREDENTIALS_FILE = SCRIPT_DIR / "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Label definitions: (display name, background color, text color)
LABELS = {
    # ── Priority labels ──────────────────────────────────────────
    "critical":      ("AI/Critical",            "#ac2b16", "#ffffff"),
    "action_needed": ("AI/Action Needed",       "#ffad47", "#000000"),
    "important":     ("AI/Important",           "#4a86e8", "#ffffff"),

    # ── Personal & relationship ───────────────────────────────────
    "personal":      ("AI/Personal",            "#cf8933", "#ffffff"),

    # ── Financial ────────────────────────────────────────────────
    "banking":       ("AI/Banking",             "#1c4587", "#ffffff"),
    "finance":       ("AI/Finance",             "#0b804b", "#ffffff"),

    # ── Official & institutional ──────────────────────────────────
    "government":    ("AI/Government",          "#653e9b", "#ffffff"),
    "legal":         ("AI/Legal",               "#434343", "#ffffff"),
    "health":        ("AI/Health",              "#149e60", "#ffffff"),

    # ── Informational / subscriptions ────────────────────────────
    "work":          ("AI/Work",                "#3c78d8", "#ffffff"),
    "travel":        ("AI/Travel",              "#285bac", "#ffffff"),
    "newsletter":    ("AI/Newsletter",          "#8e63ce", "#ffffff"),
    "promo":         ("AI/Promo",               "#cc3a21", "#ffffff"),

    # ── Junk ─────────────────────────────────────────────────────
    "ai_assistants": ("AI/AI Assistants",        "#efefef", "#000000"),
    "spam":          ("AI/Spam",                 "#666666", "#ffffff"),
    "can_delete":    ("AI/Can Delete",           "#999999", "#ffffff"),
}

LABEL_KEYS = list(LABELS.keys())

# Ordered by priority for the summary display
LABEL_DISPLAY_ORDER = [
    "critical", "action_needed", "important",
    "personal",
    "banking", "finance",
    "government", "legal", "health",
    "work", "travel",
    "newsletter", "promo",
    "spam", "can_delete",
]

CLASSIFICATION_PROMPT = """You are an expert email classifier. Classify each email into EXACTLY ONE of the categories below.
Pick the MOST SPECIFIC matching category — prefer specific over generic.

CATEGORIES:

  PRIORITY
  - critical       → Extremely urgent: security breach, account suspended/locked, legal deadline, court notice,
                     OTP or auth issues, system outages affecting the user — needs attention TODAY.
  - action_needed  → Needs a reply, approval, signature, booking, payment, or any user follow-up (but not critical urgency).
  - important      → Key info to keep but nothing to do right now (policy updates, confirmations without action needed).

  PERSONAL & RELATIONSHIP
  - personal       → Direct one-to-one email from a real human (friend, family, colleague reaching out personally).
                     NOT newsletters, NOT automated company emails, NOT group announcements.

  FINANCIAL
  - banking        → Alerts/OTPs from banks or credit-card issuers, account statements, transaction alerts,
                     EMI due reminders, loan/FD notifications from financial institutions.
  - finance        → Invoices, bills, receipts, payment confirmations, salary slips, reimbursements,
                     subscription charges — NOT from a bank itself.

  OFFICIAL & INSTITUTIONAL
  - government     → Emails from government portals, tax authorities (IT dept, GST, TDS), passport office,
                     driving licence, municipal body, Aadhaar/PAN, voter ID, any .gov/.nic domain.
  - legal          → Contracts, NDAs, legal notices, compliance requirements, court orders, regulatory filings.
  - health         → Appointments, lab reports, prescriptions, hospital bills, health insurance, pharmacy orders.

  INFORMATIONAL / PROFESSIONAL
  - work           → Professional emails related to job, employer, clients, B2B services, HR communications,
                     team updates — sent in a work context.
  - travel         → Flight/train/bus bookings, hotel reservations, cab confirmations, visa documents,
                     trip itineraries, travel insurance.
  - newsletter     → Newsletters, blog digests, curated link emails, subscription-based content.
  - promo          → Discounts, sales, marketing campaigns, offers from brands/apps/e-commerce.

  JUNK
  - ai_assistants  → Emails from Anthropic, Claude, or other AI service providers.
  - spam           → Spam, phishing, scams, suspicious unsolicited email, fake prize notifications.
  - can_delete     → Low value: automated system pings, resolved notifications, social-media activity digests,
                     read receipts, missed-call texts forwarded to email, anything safe to permanently delete.

RULES:
- Use `ai_assistants` for any emails from Anthropic/Claude or AI services.
- Use `banking` for bank/credit-card alerts, NOT `finance`.
- Use `personal` only for genuine human-to-human messages.
- Use `government` for any official govt communication.
- When in doubt between two categories, pick the more specific one.

Respond with a JSON array, one object per email:
[
  {"id": "<email_id>", "label": "<category key>", "reason": "<one short sentence why>"},
  ...
]

Only output valid JSON. No markdown code blocks. No extra text.

Emails to classify:
"""


# ─────────────────────────────────────────────
# Gmail helpers
# ─────────────────────────────────────────────

def get_gmail_service():
    """Authenticate and return Gmail API service."""
    if not TOKEN_FILE.exists():
        print("❌ token.json not found. Please run: python setup_gmail.py")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            print("🔄 Refreshing Gmail token...")
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            print("❌ Gmail token expired. Please run: python setup_gmail.py")
            sys.exit(1)

    return build("gmail", "v1", credentials=creds, static_discovery=False)


def decode_body(payload) -> str:
    """Recursively extract plain text body from email payload."""
    body = ""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    elif mime_type in ("multipart/alternative", "multipart/mixed", "multipart/related"):
        for part in payload.get("parts", []):
            result = decode_body(part)
            if result:
                body = result
                break
    return body


def fetch_emails(service, limit: int, unread_only: bool) -> list[dict]:
    """Fetch unlabeled emails from inbox using efficient server-side filtering."""
    
    # ── Dynamic Query Building ──
    # We tell Gmail to exclude all emails that already have one of our AI labels.
    # This is much faster than fetching full details and checking in Python.
    base_query = "in:inbox"
    if unread_only:
        base_query += " is:unread"
    
    # Exclude all existing labels defined in the script
    exclusions = " ".join([f'-label:"{lbl[0]}"' for lbl in LABELS.values()])
    query = f"{base_query} {exclusions}"

    print(f"📬 Searching for exactly {limit} unlabeled emails...")

    emails = []
    next_page_token = None
    checked_count = 0

    while len(emails) < limit:
        # Fetch a page of messages (only IDs that match our unlabeled query)
        results = service.users().messages().list(
            userId="me", 
            q=query, 
            maxResults=max(20, limit - len(emails)),
            pageToken=next_page_token
        ).execute()

        message_summaries = results.get("messages", [])
        next_page_token = results.get("nextPageToken")

        if not message_summaries:
            break

        for msg_summary in message_summaries:
            checked_count += 1
            msg_id = msg_summary["id"]
            
            # Fetch message details (we know it's unlabeled because of the query)
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            subject = headers.get("Subject", "(no subject)")
            sender = headers.get("From", "(unknown sender)")
            date = headers.get("Date", "")
            snippet = msg.get("snippet", "")

            body = decode_body(msg["payload"])
            if not body:
                body = snippet

            body_trimmed = body[:800].strip()

            emails.append({
                "id": msg_id,
                "subject": subject,
                "sender": sender,
                "date": date,
                "body": body_trimmed,
                "existing_labels": msg.get("labelIds", []),
            })

            if len(emails) >= limit:
                break

        if not next_page_token:
            break
        
        print(f"   Collected {len(emails)} emails...")

    print(f"✅ Found {len(emails)} unlabeled emails after searching {checked_count} total results.\n")
    return emails
# ─────────────────────────────────────────────
# Gmail label management
# ─────────────────────────────────────────────

def get_or_create_label(service, label_full_name: str, label_cache: dict) -> Optional[str]:
    """Get or create a Gmail label (and its parents) and return its ID."""
    if label_full_name in label_cache:
        return label_cache[label_full_name]

    # ── Recursive Parent Creation ──
    # If the label has a slash (e.g., AI/Category), ensure the parent (AI) exists.
    parts = label_full_name.split("/")
    if len(parts) > 1:
        parent_name = "/".join(parts[:-1])
        get_or_create_label(service, parent_name, label_cache)

    try:
        # Check if label already exists
        existing = service.users().labels().list(userId="me").execute()
        for lbl in existing.get("labels", []):
            if lbl["name"] == label_full_name:
                label_cache[label_full_name] = lbl["id"]
                return lbl["id"]

        # Create new label if not found
        print(f"   ✨ Creating Gmail label: {label_full_name}")
        
        # Determine colors (only for our known AI labels, else default)
        bg_color, text_color = "#efefef", "#000000"
        for key, config in LABELS.items():
            if config[0] == label_full_name:
                bg_color, text_color = config[1], config[2]
                break

        label_object = {
            "name": label_full_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        
        # Only add color if it's one of our defined categories
        if any(config[0] == label_full_name for config in LABELS.values()):
            label_object["color"] = {
                "backgroundColor": bg_color.lower(),
                "textColor": text_color.lower()
            }

        created = service.users().labels().create(userId="me", body=label_object).execute()
        label_cache[label_full_name] = created["id"]
        return created["id"]
    except Exception as e:
        print(f"   ⚠️  Could not create label '{label_full_name}': {e}")
        return None


def apply_label(service, email_id: str, label_id: str):
    """Apply a label to an email."""
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={"addLabelIds": [label_id]},
    ).execute()


# ─────────────────────────────────────────────
# AI Classification
# ─────────────────────────────────────────────

def classify_batch(client: anthropic.Anthropic, emails: list[dict]) -> list[dict]:
    """Send a batch of emails to Claude for classification."""
    email_text = ""
    for i, email in enumerate(emails, 1):
        email_text += (
            f"\n--- EMAIL {i} ---\n"
            f"id: {email['id']}\n"
            f"From: {email['sender']}\n"
            f"Date: {email['date']}\n"
            f"Subject: {email['subject']}\n"
            f"Body snippet:\n{email['body']}\n"
        )

    prompt = CLASSIFICATION_PROMPT + email_text

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code blocks if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        results = json.loads(raw)
        # Validate each result
        validated = []
        for r in results:
            label = r.get("label", "").lower().replace(" ", "_")
            if label not in LABEL_KEYS:
                label = "can_delete"  # Default fallback
            validated.append({
                "id": r.get("id", ""),
                "label": label,
                "reason": r.get("reason", ""),
            })
        return validated
    except json.JSONDecodeError:
        print(f"   ⚠️  Claude returned unparseable JSON, skipping batch")
        return []


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AI-powered Gmail inbox labeler")
    parser.add_argument("--limit", type=int, default=50, help="Number of emails to process")
    parser.add_argument("--unread-only", action="store_true", help="Only unread emails")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying labels")
    parser.add_argument("--batch-size", type=int, default=5, help="Emails per Claude API call")
    args = parser.parse_args()

    # Check for Anthropic API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set.")
        print("   export ANTHROPIC_API_KEY='your-api-key-here'")
        sys.exit(1)

    print("🤖 Gmail Inbox AI Labeler")
    print("=" * 50)
    if args.dry_run:
        print("⚠️  DRY RUN MODE — labels will NOT be applied to Gmail\n")

    # Initialize clients
    anthropic_client = anthropic.Anthropic(api_key=api_key)
    gmail_service = get_gmail_service()

    # Fetch emails
    emails = fetch_emails(gmail_service, args.limit, args.unread_only)
    if not emails:
        return

    print(f"\n🧠 Classifying {len(emails)} emails using Claude AI...")
    print("   (Using Claude Sonnet 4.6 for frontier-level classification)\n")

    # Process in batches
    batches = [emails[i:i + args.batch_size] for i in range(0, len(emails), args.batch_size)]
    classifications = {}

    for batch_num, batch in enumerate(batches, 1):
        print(f"   Batch {batch_num}/{len(batches)} ({len(batch)} emails)...")
        results = classify_batch(anthropic_client, batch)

        for r in results:
            classifications[r["id"]] = r

        # Small delay to avoid rate limits
        if batch_num < len(batches):
            time.sleep(0.5)

    print(f"\n✅ Classification complete. {len(classifications)} emails classified.\n")

    # Apply labels
    label_cache = {}
    stats = {key: 0 for key in LABEL_KEYS}
    errors = 0

    print(f"{'DRY RUN — ' if args.dry_run else ''}Applying labels...")
    print("-" * 60)

    for email in emails:
        email_id = email["id"]
        classification = classifications.get(email_id)

        if not classification:
            continue

        label_key = classification["label"]
        label_name = LABELS[label_key][0]
        reason = classification["reason"]

        # Truncate subject for display
        subject = email["subject"][:55] + "..." if len(email["subject"]) > 55 else email["subject"]
        print(f"  {label_name:<25}  {subject}")
        print(f"  {'':25}  → {reason}")
        print()

        stats[label_key] += 1

        if not args.dry_run:
            try:
                label_id = get_or_create_label(gmail_service, label_name, label_cache)
                if label_id:
                    apply_label(gmail_service, email_id, label_id)
            except Exception as e:
                print(f"   ⚠️  Failed to apply label for email '{subject}': {e}")
                errors += 1

    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    for key in LABEL_DISPLAY_ORDER:
        count = stats.get(key, 0)
        if count > 0:
            label_name = LABELS[key][0]
            bar = "█" * min(count, 20) + "░" * (20 - min(count, 20))
            print(f"  {label_name:<30}  {bar}  {count}")

    total = sum(stats.values())
    print(f"\n  Total emails processed: {total}")
    if errors:
        print(f"  Errors: {errors}")
    if args.dry_run:
        print("\n  ℹ️  This was a dry run. Run without --dry-run to apply labels.")

    print("\n✨ Done!")


if __name__ == "__main__":
    main()
