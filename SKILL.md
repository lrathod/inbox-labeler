---
name: Gmail Inbox Labeler
description: Automatically reads the user's Gmail inbox, uses AI to intelligently classify each email, and applies appropriate Gmail labels — Critical, Action Needed, Important, Personal, Banking, Finance, Government, Legal, Health, Work, Travel, Newsletter, Promo, Spam, Can Delete.
---

# Gmail Inbox Labeler Skill

## Overview
This skill connects to the user's Gmail account, reads recent inbox emails, and uses Claude AI to intelligently classify and label them. Labels are created under the `AI/` namespace inside Gmail so they stay organized and separate from any existing labels.

## Labels Applied

### 🔺 Priority
| Label | Meaning |
|---|---|
| `AI/🔴 Critical` | Extremely urgent — needs attention today (account suspended, security breach, legal deadline) |
| `AI/🟠 Action Needed` | Requires a reply, task, approval, or follow-up |
| `AI/⭐ Important` | Key info to keep, no action/urgency needed |

### 👤 Personal
| Label | Meaning |
|---|---|
| `AI/💬 Personal` | Direct one-to-one email from a real human (friend, family, colleague) — NOT automated |

### 💳 Financial
| Label | Meaning |
|---|---|
| `AI/🏦 Banking` | Bank/credit-card alerts, OTPs, account statements, EMI reminders, loan notifications |
| `AI/💰 Finance` | Invoices, bills, receipts, payment confirmations, salary slips, subscription charges |

### 🏛️ Official & Institutional
| Label | Meaning |
|---|---|
| `AI/🏛️ Government` | Tax authority, passport, Aadhaar/PAN, voter ID, municipal body, .gov/.nic domains |
| `AI/⚖️ Legal` | Contracts, NDAs, legal notices, compliance requirements, court orders |
| `AI/🏥 Health` | Medical appointments, lab reports, hospital bills, health insurance, pharmacy orders |

### 📋 Informational
| Label | Meaning |
|---|---|
| `AI/💼 Work` | Job, employer, clients, HR communications, B2B services, professional context |
| `AI/✈️ Travel` | Flights, hotels, cabs, visa documents, trip itineraries, travel insurance |
| `AI/📰 Newsletter` | Newsletters, blog digests, curated link subscriptions |
| `AI/📢 Promo` | Promotions, discounts, sales, marketing campaigns |

### 🗑️ Junk
| Label | Meaning |
|---|---|
| `AI/🚨 Spam` | Spam, phishing, scams, suspicious/unsolicited senders |
| `AI/🗑️ Can Delete` | Low-value, safe to permanently delete |

## Prerequisites
1. Python 3.8+
2. A Google Cloud project with Gmail API enabled
3. `credentials.json` OAuth file placed in `scripts/`
4. An Anthropic API key set as `ANTHROPIC_API_KEY` environment variable

## First-Time Setup
Run the following to install dependencies and authenticate:
```bash
cd scripts/
pip install -r requirements.txt
python setup_gmail.py
```
This will open a browser window asking you to authorize Gmail access. A `token.json` file will be saved for future use.

## Running the Labeler
```bash
cd scripts/
python label_inbox.py
```

### Options
| Flag | Default | Description |
|---|---|---|
| `--limit` | `50` | Number of recent inbox emails to process |
| `--unread-only` | False | Only process unread emails |
| `--dry-run` | False | Preview labels without applying them |
| `--batch-size` | `5` | Emails classified per API call |

Example — process 100 unread emails in dry-run mode:
```bash
python label_inbox.py --limit 100 --unread-only --dry-run
```

## How Classification Works
1. For each email, the subject, sender, date, and a trimmed snippet of the body are extracted.
2. A batch of emails is sent to Claude with a structured classification prompt.
3. Claude returns the **most specific** matching label and a short reason for each email.
4. The script creates the Gmail label if it doesn't exist, then applies it.
5. A summary report is printed at the end, ordered by priority.

## Classification Rules
- `banking` is for emails from banks/credit-card issuers specifically — NOT generic `finance`
- `personal` is only for genuine human-to-human messages, never automated company emails
- `government` covers any official government communication (.gov, .nic, tax dept, UIDAI, etc.)
- `legal` covers contracts, NDAs, notices, compliance
- When two categories could apply, the more **specific** one wins

## When to Use This Skill
- When the user says things like "label my inbox", "clean up my Gmail", "sort my emails", "classify my emails".
- Confirm how many emails to process (default: 50).
- After running, show the user a summary of what was labeled and how.

## Steps to Execute
1. Check that `scripts/credentials.json` exists. If not, remind the user to set up Google Cloud credentials (see `scripts/setup_gmail.py` header comments).
2. Check that `scripts/token.json` exists. If not, run `python scripts/setup_gmail.py` first.
3. Run `python scripts/label_inbox.py` with any user-specified flags.
4. Report the labeling summary back to the user.
