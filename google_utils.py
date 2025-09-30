import json
import logging
from typing import Any

import requests
from google.auth.transport.requests import Request
from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_project_id() -> str | None:
    """
    Get the Google Cloud project ID.
    """
    try:
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
        headers = {"Metadata-Flavor": "Google"}
        response = requests.get(metadata_url, headers=headers, timeout=5)
        if response.status_code != 200:
            logger.info(
                f"Failed to get project ID from Google's metadata service, response: {response}"
            )
            return None

        project_id = response.text
        assert isinstance(project_id, str)
        return project_id

    except Exception:
        logger.error("Failed to get project ID from Google's metadata service", exc_info=True)
        return None


def get_secret(token_name: str) -> str:
    """
    Gets the secret from Google Secret Manager
    """
    client = secretmanager.SecretManagerServiceClient()
    project_id = get_project_id()
    assert project_id, "Project ID not retrievable from Google"
    name = f"projects/{project_id}/secrets/{token_name}/versions/latest"
    response = client.access_secret_version(name=name)
    secret = response.payload.data.decode("UTF-8")

    assert isinstance(secret, str)

    return secret


def add_secret_version(token_name: str, payload: str) -> None:
    """
    Add a new secret version to the given secret with the provided payload.
    """
    client = secretmanager.SecretManagerServiceClient()

    project_id = get_project_id()
    assert project_id, "Project ID not retrievable from Google"
    parent = client.secret_path(project_id, token_name)

    payload_encoded = payload.encode("UTF-8")

    client.add_secret_version(request={"parent": parent, "payload": {"data": payload_encoded}})


def get_google_credentials() -> Credentials:
    """
    Gets credentials to access Google API's.

    It takes the secret from the google secrets manager,
    and updates it if necessary.
    """

    token = get_secret("google-drive-token")
    json_token = json.loads(token)
    credentials = Credentials(
        token=json_token.get("token"),
        refresh_token=json_token.get("refresh_token"),
        token_uri=json_token.get("token_uri"),
        client_id=json_token.get("client_id"),
        client_secret=json_token.get("client_secret"),
        scopes=json_token.get("scopes"),
    )

    if credentials.expired and credentials.refresh_token:
        # Refresh the credentials and store them
        credentials.refresh(Request())
        add_secret_version(token_name="google-drive-token", payload=credentials.to_json())

    return credentials


def build_drive_service() -> Any:
    return build("drive", "v3", credentials=get_google_credentials())
