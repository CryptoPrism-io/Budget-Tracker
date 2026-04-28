# Budget-Tracker

Single-page tracker for the Kathmandu trip. Open `index.html` in a browser.
No backend, no install, no auth. Default plan: **₹1,500/day for 50 days
(₹75,000 runway)** — editable inline.

## Daily flow

1. Open `index.html` (locally, or via GitHub Pages).
2. **Bank email arrived?** Paste into **Paste email** → **Parse & add**.
3. **Cash spent?** Use the **Add manually** row.
4. **Want it from Gmail without copying each one?** → see "Sync via Claude"
   below.

The runway panel up top shows: today's spend vs ₹1,500, total spent vs
₹75,000, day N of 50, average daily pace, and "days left at this pace."
Goes red when your average exceeds the daily budget.

## Sync via Claude

You don't have a backend connecting Gmail to this app — by design. Instead,
when you want to sync, ask Claude (any client with Gmail access — Claude
Desktop with the Gmail MCP, Claude.ai with the Gmail connector, etc.) to
fetch and parse for you. Paste this prompt:

```
Read my Gmail. Find every transaction email from Axis Bank
(alerts@axisbank.com, cc.alerts@axisbank.com, credit_cards@axisbank.com)
and CSB Jupiter (no-reply@jupiter.money, transactions@jupiter.money,
alerts@csb.co.in) from the last 3 days.

For each one, extract:
- id:        "gmail-" + the Gmail message id (stable, used for dedup)
- date:      ISO 8601 timestamp of the email
- bank:      "axis" or "jupiter"
- account:   last 3-6 digits of the account or card (string), or null
- direction: "debit" or "credit"
- amount:    number in INR (no currency symbol, no commas)
- note:      a short merchant/description string, max 160 chars

Reply with ONLY a JSON array. No prose, no code fences.
```

Claude returns a JSON array → copy it → paste into **Sync from Claude** in
the app → **Merge JSON**. The app dedupes by `id`, so you can paste the
same response twice without duplicating anything. Run this once a day, or
whenever you remember.

## Backup

- **Export JSON** downloads `transactions-YYYY-MM-DD.json`. Drop it in the
  repo to keep a versioned snapshot.
- **Import file** merges a JSON file (also dedupes by `id`).
- **Reset all** clears everything.

## Tweaking the parser

Regex lives at the top of the `<script>` block in `index.html`
(`AMOUNT_RE`, `ACCOUNT_RE`, `CARD_RE`, `DEBIT_WORDS`, `CREDIT_WORDS`,
plus the bank-detection `if` chain). If a real email doesn't parse, paste
a redacted sample, look at what the regex misses, and tighten the pattern.

## Hosting (optional)

Enable GitHub Pages on the repo (Settings → Pages → Source: `main` branch)
and the tracker will be available at `https://<user>.github.io/Budget-Tracker/`.
