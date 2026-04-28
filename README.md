# Budget-Tracker

Single-page budget tracker for the Kathmandu trip. Open `index.html` in a
browser. No backend, no install, no auth.

## Use

1. Open `index.html` (locally, or via GitHub Pages).
2. When a bank email arrives (Axis or Jupiter), copy the body, paste into
   the **Paste email** box, hit **Parse & add**. The script pulls out the
   amount, direction (debit/credit), and account suffix.
3. For cash or anything that doesn't parse, use **Add manually**.
4. Totals (Spent / Received / Net) and a per-account breakdown update
   live. Data is stored in your browser's `localStorage`.

## Backup

- **Export JSON** downloads `transactions-YYYY-MM-DD.json`. Drop it in the
  repo to keep a versioned snapshot.
- **Import JSON** loads a previously exported file (replaces current data).
- **Reset all** clears everything.

## Tweaking the parser

Regex lives at the top of the `<script>` block in `index.html`
(`AMOUNT_RE`, `ACCOUNT_RE`, `CARD_RE`, `DEBIT_WORDS`, `CREDIT_WORDS`,
plus the bank-detection `if` chain). If a real email doesn't parse, paste
a redacted sample, look at what the regex misses, and tighten the pattern.

## Hosting (optional)

Enable GitHub Pages on the repo (Settings → Pages → Source: `main` branch)
and the tracker will be available at `https://<user>.github.io/Budget-Tracker/`.
