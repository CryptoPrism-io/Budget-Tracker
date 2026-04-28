# Budget-Tracker

Kathmandu trip budget tracker. A GitHub Actions cron polls Gmail every 15
minutes, parses bank-transaction emails from **Axis** (multi-account) and
**CSB Jupiter**, and appends each transaction to `transactions.json`.

No server. No database. Just a JSON file in the repo.

## How it works

```
Gmail  ──fetch.py──>  parse  ──>  transactions.json  ──>  git commit
   ^                                                            │
   └──────────────── GitHub Actions cron (*/15) ────────────────┘
```

Each transaction is keyed by Gmail `message_id`, so re-runs are idempotent.
The parsers extract: direction (debit/credit), amount, account suffix
(last 3-6 digits, useful for tagging which Axis account), and the email
subject + snippet for review.

## One-time setup

### 1. Create Gmail OAuth credentials

1. Go to https://console.cloud.google.com → create a project.
2. Enable the **Gmail API**.
3. OAuth consent screen → External → add yourself as a test user.
4. Credentials → Create OAuth client ID → **Desktop app** → download JSON.
5. Save as `credentials.json` in the repo root (gitignored).

### 2. Generate a refresh token locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python auth_setup.py
```

A browser opens, you grant **read-only** Gmail access, and `token.json` is
written.

### 3. Add GitHub secrets

In the repo: **Settings → Secrets and variables → Actions → New secret**.

| Name                     | Value                              |
| ------------------------ | ---------------------------------- |
| `GMAIL_CREDENTIALS_JSON` | Full contents of `credentials.json` |
| `GMAIL_TOKEN_JSON`       | Full contents of `token.json`       |

### 4. Done

The workflow runs every 15 minutes. Trigger it once manually from the
**Actions** tab to confirm it works (Run workflow → fetch).

## Tuning the parsers

The parsers in `fetch.py` (`parse_axis`, `parse_jupiter`) use generic regex
that handles common Indian-bank email formats. If a real email comes in
that doesn't parse, the run logs `skipped (unparsed): <subject>`. Open
that email, copy a representative line, and tighten the regex.

The bank sender list is in `BANK_SENDERS` at the top of `fetch.py`. Add
addresses there if your alerts come from a domain not yet listed.

## Local dry-run

```bash
python fetch.py
```

Reads `token.json`, fetches the last 3 days, prints what it found, and
updates `transactions.json` in place.
