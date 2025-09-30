#!/usr/bin/env python3
"""
Generate OAuth2 token for Google APIs.

This script authenticates with Google services and generates a token.json file
that should be uploaded to Google Secret Manager for production use.

Usage:
    python generate_google_token.py
"""

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Configure required API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.readonly",
]

# File paths
CREDENTIALS_PATH = "./credentials.json"
TOKEN_PATH = "./token.json"


def main() -> None:
    """Authenticate and generate OAuth2 token for Google APIs."""
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_PATH):
        print(f"Loading existing token from {TOKEN_PATH}...")
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Refresh or generate new token as needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"Error: Credentials file not found at {CREDENTIALS_PATH}")
                print("\nTo get credentials:")
                print("1. Go to https://console.cloud.google.com/apis/credentials")
                print("2. Create an OAuth 2.0 Client ID (Web application)")
                print("3. Add redirect URI: http://localhost:8080/")
                print("4. Download the credentials JSON file")
                print(f"5. Save it as {CREDENTIALS_PATH} in this directory")
                return

            print(f"Generating new token using credentials from {CREDENTIALS_PATH}...")
            print("\nA browser window will open for authentication.")
            print("Please log in with your Google account and authorize the application.")

            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save token for future use
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    print(f"Token saved to {TOKEN_PATH}")
    print(
        "\nUpload this token file to Google Secret Manager and grant your service account access "
        "to the secret"
    )


if __name__ == "__main__":
    main()
