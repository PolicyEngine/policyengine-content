"""Google Docs content parser."""

import os
import re
from typing import Any, Optional

# Google API imports - optional dependency
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]


def get_google_credentials() -> Any:
    """Get Google OAuth credentials.

    Uses environment variables for credential paths:
    - GOOGLE_CREDENTIALS_FILE: Path to OAuth client credentials
    - GOOGLE_TOKEN_FILE: Path to cached token

    Returns:
        Google credentials object
    """
    if not GOOGLE_API_AVAILABLE:
        raise ImportError(
            "Google API libraries not installed. "
            "Install with: pip install google-auth-oauthlib google-api-python-client"
        )

    token_path = os.environ.get(
        "GOOGLE_TOKEN_FILE",
        os.path.expanduser("~/.config/policyengine/google-token.json"),
    )
    credentials_file = os.environ.get(
        "GOOGLE_CREDENTIALS_FILE",
        os.path.expanduser("~/.config/policyengine/google-credentials.json"),
    )

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


class GoogleDocsParser:
    """Parser for Google Docs content."""

    # Pattern to match Google Docs URLs and extract document ID
    DOC_ID_PATTERN = re.compile(
        r"(?:https?://)?docs\.google\.com/document/d/([a-zA-Z0-9_-]+)"
    )

    def extract_doc_id(self, url: str) -> str:
        """Extract document ID from a Google Docs URL.

        Args:
            url: Google Docs URL in various formats

        Returns:
            Document ID string

        Raises:
            ValueError: If URL is not a valid Google Docs URL
        """
        match = self.DOC_ID_PATTERN.search(url)
        if not match:
            raise ValueError(f"Invalid Google Docs URL: {url}")
        return match.group(1)

    def fetch_content(self, doc_id: str) -> str:
        """Fetch document content from Google Docs API.

        Args:
            doc_id: Google Docs document ID

        Returns:
            Plain text content of the document
        """
        creds = get_google_credentials()
        service = build("docs", "v1", credentials=creds)

        document = service.documents().get(documentId=doc_id).execute()

        return self._extract_text(document)

    def _extract_text(self, document: dict) -> str:
        """Extract plain text from a Google Docs document structure.

        Args:
            document: Google Docs API document response

        Returns:
            Plain text content
        """
        content = document.get("body", {}).get("content", [])
        text_parts = []

        for item in content:
            if "paragraph" in item:
                paragraph = item["paragraph"]
                for element in paragraph.get("elements", []):
                    if "textRun" in element:
                        text_parts.append(element["textRun"]["content"])

        return "".join(text_parts)

    def fetch_document(self, url: str) -> dict:
        """Fetch and parse a Google Docs document.

        Args:
            url: Google Docs URL

        Returns:
            Dictionary with title and content
        """
        doc_id = self.extract_doc_id(url)
        creds = get_google_credentials()
        service = build("docs", "v1", credentials=creds)

        document = service.documents().get(documentId=doc_id).execute()

        return {
            "title": document.get("title", "Untitled"),
            "content": self._extract_text(document),
            "doc_id": doc_id,
        }


def parse_google_doc(url: str) -> dict:
    """Parse a Google Docs document from URL.

    Convenience function for parsing Google Docs.

    Args:
        url: Google Docs URL

    Returns:
        Dictionary with:
        - title: Document title
        - content: Plain text content
        - doc_id: Document ID
    """
    parser = GoogleDocsParser()
    return parser.fetch_document(url)
