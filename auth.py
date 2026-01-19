from pathlib import Path
from typing import Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# testing scopes with full access! In production, use least-privilege scopes.
DEFAULT_SCOPES = (
    "https://www.googleapis.com/auth/calendar",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/tasks",
)

def _resolve(path: str | Path) -> Path:
    p = Path(path).expanduser()
    return p if p.is_absolute() else Path.cwd() / p

def get_credentials(
    scopes: Sequence[str] = DEFAULT_SCOPES,
    credentials_path: str | Path = "credentials.json",
    token_path: str | Path = "token.json",
) -> Credentials:
    """
    Returns valid user credentials. Tries cached token, refreshes if expired,
    otherwise runs the browser consent flow and saves a new token.
    """
    scope_list = list(scopes)
    creds: Credentials | None = None
    credentials_file = _resolve(credentials_path)
    token_file = _resolve(token_path)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scope_list)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # fall back to full flow if refresh fails

    if not creds or not creds.valid:
        if not credentials_file.exists():
            raise FileNotFoundError(
                f"Missing OAuth client file at {credentials_file}. "
                "Download it from Google Cloud Console (OAuth client ID)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), scope_list)
        creds = flow.run_local_server(port=0, prompt="consent")
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json())

    return creds

def build_service(
    api_name: str,
    api_version: str,
    scopes: Sequence[str] = DEFAULT_SCOPES,
    credentials_path: str | Path = "credentials.json",
    token_path: str | Path = "token.json",
    **kwargs,
):
    """
    Builds a Google API client (e.g., calendar, gmail, tasks) with shared auth flow.
    """
    creds = get_credentials(scopes, credentials_path, token_path)
    return build(api_name, api_version, credentials=creds, **kwargs)


if __name__ == "__main__":
    try:
        creds = get_credentials()
        print("Authentication succeeded; token cached at", _resolve("token.json"))
    except Exception as exc:
        print(f"Authentication failed: {exc}")