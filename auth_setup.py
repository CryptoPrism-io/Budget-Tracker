"""One-time local OAuth flow. Produces token.json with a refresh token.

Usage:
    1. Create OAuth client (Desktop) in Google Cloud Console, enable Gmail API,
       download credentials.json into this folder.
    2. python auth_setup.py
    3. Copy contents of credentials.json -> GitHub secret GMAIL_CREDENTIALS_JSON
       Copy contents of token.json       -> GitHub secret GMAIL_TOKEN_JSON
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main() -> None:
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)
    with open("token.json", "w") as f:
        f.write(creds.to_json())
    print("Wrote token.json")


if __name__ == "__main__":
    main()
