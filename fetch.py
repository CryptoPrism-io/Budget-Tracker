"""Fetch new bank transaction emails from Gmail and append to transactions.json.

Run by GitHub Actions on a cron. Idempotent: each transaction is keyed by
Gmail message id, so re-runs do not create duplicates.
"""
from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "transactions.json"
TOKEN_FILE = ROOT / "token.json"

# Senders to watch. Adjust if your banks use different addresses.
BANK_SENDERS = {
    "axis": [
        "alerts@axisbank.com",
        "cc.alerts@axisbank.com",
        "credit_cards@axisbank.com",
    ],
    "jupiter": [
        "no-reply@jupiter.money",
        "noreply@jupiter.money",
        "transactions@jupiter.money",
        "alerts@csb.co.in",
    ],
}

# How far back to look on each run. We dedupe by message id, so a generous
# window is safe and lets us recover from missed runs.
LOOKBACK_DAYS = 3

AMOUNT_RE = re.compile(
    r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE
)
ACCOUNT_RE = re.compile(r"(?:A/?c(?:\s*no\.?)?|account)\s*(?:XX|X+|\*+)?(\d{3,6})", re.IGNORECASE)
CARD_RE = re.compile(r"card\s*(?:ending\s*(?:in|with))?\s*(?:XX|X+|\*+)?(\d{3,6})", re.IGNORECASE)


@dataclass
class Transaction:
    message_id: str
    bank: str
    account: str | None
    direction: str  # "debit" or "credit"
    amount: float
    currency: str
    date: str  # ISO 8601
    subject: str
    snippet: str


def load_credentials() -> Credentials:
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        else:
            raise RuntimeError("token.json is invalid and cannot be refreshed")
    return creds


def gmail_query() -> str:
    senders = " OR ".join(
        f"from:{addr}" for addrs in BANK_SENDERS.values() for addr in addrs
    )
    return f"({senders}) newer_than:{LOOKBACK_DAYS}d"


def extract_text(payload: dict) -> str:
    """Return the email body as plain text, walking multipart trees."""
    if "parts" in payload:
        chunks: list[str] = []
        for part in payload["parts"]:
            chunks.append(extract_text(part))
        return "\n".join(c for c in chunks if c)

    body = payload.get("body", {})
    data = body.get("data")
    if not data:
        return ""
    raw = base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")
    mime = payload.get("mimeType", "")
    if "html" in mime:
        return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    return raw


def identify_bank(sender: str) -> str | None:
    sender = sender.lower()
    for bank, addrs in BANK_SENDERS.items():
        if any(a in sender for a in addrs):
            return bank
    return None


def parse_amount(text: str) -> float | None:
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_direction(text: str) -> str | None:
    lo = text.lower()
    debit_words = ("debited", "spent", "paid", "withdrawn", "purchase", "sent")
    credit_words = ("credited", "received", "deposited", "refund")
    if any(w in lo for w in debit_words):
        return "debit"
    if any(w in lo for w in credit_words):
        return "credit"
    return None


def parse_account(text: str) -> str | None:
    m = ACCOUNT_RE.search(text) or CARD_RE.search(text)
    return m.group(1) if m else None


def parse_axis(text: str) -> tuple[str | None, float | None, str | None]:
    return parse_direction(text), parse_amount(text), parse_account(text)


def parse_jupiter(text: str) -> tuple[str | None, float | None, str | None]:
    return parse_direction(text), parse_amount(text), parse_account(text)


PARSERS: dict[str, Callable[[str], tuple[str | None, float | None, str | None]]] = {
    "axis": parse_axis,
    "jupiter": parse_jupiter,
}


def header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def to_iso(date_header: str) -> str:
    try:
        return parsedate_to_datetime(date_header).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat()


def load_existing() -> tuple[list[dict], set[str]]:
    if not DATA_FILE.exists():
        return [], set()
    data = json.loads(DATA_FILE.read_text() or "[]")
    return data, {t["message_id"] for t in data}


def save(transactions: list[dict]) -> None:
    transactions.sort(key=lambda t: t["date"], reverse=True)
    DATA_FILE.write_text(json.dumps(transactions, indent=2) + "\n")


def main() -> int:
    creds = load_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    existing, seen = load_existing()
    query = gmail_query()
    print(f"Gmail query: {query}")

    resp = service.users().messages().list(userId="me", q=query, maxResults=100).execute()
    messages = resp.get("messages", [])
    print(f"Found {len(messages)} messages in window")

    new_count = 0
    for m in messages:
        if m["id"] in seen:
            continue
        msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = msg["payload"].get("headers", [])
        sender = header(headers, "From")
        bank = identify_bank(sender)
        if not bank:
            continue

        text = extract_text(msg["payload"]) or msg.get("snippet", "")
        direction, amount, account = PARSERS[bank](text)
        if amount is None or direction is None:
            print(f"  skipped (unparsed): {header(headers, 'Subject')[:80]}")
            continue

        tx = Transaction(
            message_id=m["id"],
            bank=bank,
            account=account,
            direction=direction,
            amount=amount,
            currency="INR",
            date=to_iso(header(headers, "Date")),
            subject=header(headers, "Subject"),
            snippet=msg.get("snippet", "")[:240],
        )
        existing.append(asdict(tx))
        seen.add(m["id"])
        new_count += 1
        print(f"  + {bank} {direction} {amount} acct={account}")

    save(existing)
    print(f"Added {new_count} new transactions. Total: {len(existing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
