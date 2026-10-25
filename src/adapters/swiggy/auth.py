"""OAuth 2.1 PKCE Flow and Token Lifecycle Manager for Swiggy Builders Club MCP.

Implements:
1. Dynamic Client Registration (RFC 7591) at POST /auth/register
2. PKCE S256 Authorization at GET /auth/authorize
3. Code exchange at POST /auth/token
4. Automatic token refresh at POST /auth/token (grant_type=refresh_token)
5. Proactive refresh when <= 60s remain and reactive refresh on 401 / -32001
6. Server-side session revocation at POST /auth/logout
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

SWIGGY_BASE_URL = "https://mcp.swiggy.com"
AUTH_SERVER_URL = f"{SWIGGY_BASE_URL}/auth"
REDIRECT_URI = "http://localhost:8000/callback"
CALLBACK_PORT = 8000


def get_token_file_path() -> Path:
    """Returns the secure local path where the token is persisted."""
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return Path("/tmp/tokens.json")

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    try:
        token_dir = base / "price_history"
        token_dir.mkdir(parents=True, exist_ok=True)
        return token_dir / "tokens.json"
    except (OSError, PermissionError):
        return Path("/tmp/tokens.json")


def save_tokens(token_payload: Dict[str, Any]) -> None:
    """Saves OAuth tokens securely with calculated expires_at."""
    token_file = get_token_file_path()

    # Calculate exact unix timestamp for expiry
    expires_in = token_payload.get("expires_in", 432000)  # Default 5 days
    token_payload["expires_at"] = time.time() + expires_in

    with open(token_file, "w", encoding="utf-8") as f:
        json.dump(token_payload, f, indent=2)

    # Restrict permissions on POSIX systems (chmod 600)
    if os.name != "nt":
        try:
            os.chmod(token_file, 0o600)
        except Exception:
            pass


def load_token_payload() -> Optional[Dict[str, Any]]:
    """Loads full token metadata payload from disk."""
    token_file = get_token_file_path()
    if token_file.exists():
        try:
            with open(token_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Exchanges a refresh token for a fresh 30-day access and rotated refresh token."""
    url = f"{AUTH_SERVER_URL}/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            res = client.post(url, json=payload)
            if res.status_code == 200:
                new_tokens = res.json()
                save_tokens(new_tokens)
                logger.info("Successfully refreshed Swiggy MCP access token.")
                return new_tokens
            else:
                logger.warning(f"Token refresh failed ({res.status_code}): {res.text}")
                return None
    except Exception as e:
        logger.error(f"Error during token refresh: {e}")
        return None


def get_valid_access_token() -> Optional[str]:
    """Returns a valid access token, proactively refreshing if <= 60s remain."""
    # 1. Environment variable override
    env_token = os.environ.get("SWIGGY_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()

    # 2. Stored token payload
    payload = load_token_payload()
    if not payload:
        return None

    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_at = payload.get("expires_at", 0)

    # Proactive refresh when <= 60 seconds remain before expiration
    if time.time() >= (expires_at - 60):
        if refresh_token:
            refreshed = refresh_access_token(refresh_token)
            if refreshed:
                return refreshed.get("access_token")
        return None

    return access_token


# Alias for backward compatibility
load_saved_token = get_valid_access_token


def revoke_session() -> bool:
    """Revokes the current session on Swiggy's auth server and deletes local tokens."""
    payload = load_token_payload()
    if payload and "access_token" in payload:
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    f"{AUTH_SERVER_URL}/logout",
                    headers={"Authorization": f"Bearer {payload['access_token']}"},
                )
        except Exception as e:
            logger.warning(f"Server-side logout warning: {e}")

    token_file = get_token_file_path()
    if token_file.exists():
        try:
            token_file.unlink()
        except Exception:
            pass
    return True


def _generate_pkce_pair() -> tuple[str, str]:
    """Generates PKCE code_verifier and code_challenge (S256)."""
    verifier_bytes = secrets.token_bytes(32)
    code_verifier = base64.urlsafe_b64encode(verifier_bytes).decode("utf-8").rstrip("=")

    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

    return code_verifier, code_challenge


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Temporary local HTTP server to receive the OAuth redirect."""

    auth_code: Optional[str] = None
    auth_state: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            if "code" in params:
                OAuthCallbackHandler.auth_code = params["code"][0]
                OAuthCallbackHandler.auth_state = params.get("state", [""])[0]

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Swiggy Authentication Successful</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #f7f9fa; }
                        .card { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; max-width: 420px; }
                        h1 { color: #FC8019; margin-bottom: 12px; font-size: 24px; }
                        p { color: #535766; line-height: 1.5; font-size: 15px; }
                        .badge { display: inline-block; background: #E8F5E9; color: #2E7D32; padding: 6px 14px; border-radius: 20px; font-weight: 600; margin-top: 16px; font-size: 14px; }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>Swiggy Connected!</h1>
                        <p>Your authentication was successful. Your local Price History app is now authorized.</p>
                        <div class="badge">&#10003; You can safely close this window</div>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode("utf-8"))
            else:
                OAuthCallbackHandler.error = params.get("error_description", ["Authorization failed"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Authentication Error: {OAuthCallbackHandler.error}".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def run_oauth_flow() -> Dict[str, Any]:
    """Runs the end-to-end OAuth 2.1 PKCE authorization flow."""
    # Step 1: Dynamic Client Registration (RFC 7591)
    dcr_payload = {
        "client_name": "price-history",
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    with httpx.Client(timeout=15.0) as client:
        dcr_res = client.post(f"{AUTH_SERVER_URL}/register", json=dcr_payload)
        dcr_res.raise_for_status()
        client_id = dcr_res.json().get("client_id", "swiggy-mcp")

    # Step 2: Generate PKCE keys & CSRF state
    code_verifier, code_challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    # Step 3: Construct Swiggy Authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "scope": "mcp:tools",
    }
    authorize_url = f"{AUTH_SERVER_URL}/authorize?{urlencode(auth_params)}"

    # Step 4: Start local loopback HTTP server
    server = HTTPServer(("localhost", CALLBACK_PORT), OAuthCallbackHandler)
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.auth_state = None
    OAuthCallbackHandler.error = None

    server_thread = threading.Thread(target=server.handle_request)
    server_thread.daemon = True
    server_thread.start()

    # Step 5: Open Swiggy consent UI in default browser
    webbrowser.open(authorize_url)

    # Wait for callback
    server_thread.join(timeout=180.0)
    server.server_close()

    if not OAuthCallbackHandler.auth_code:
        err = OAuthCallbackHandler.error or "Login timed out after 3 minutes or was cancelled."
        raise TimeoutError(f"OAuth authorization failed: {err}")

    # Verify CSRF state
    if OAuthCallbackHandler.auth_state != state:
        raise ValueError("OAuth state mismatch (potential CSRF detected). Aborting.")

    # Step 6: Exchange authorization code for tokens
    token_exchange_payload = {
        "grant_type": "authorization_code",
        "code": OAuthCallbackHandler.auth_code,
        "code_verifier": code_verifier,
        "redirect_uri": REDIRECT_URI,
    }

    with httpx.Client(timeout=15.0) as client:
        token_res = client.post(f"{AUTH_SERVER_URL}/token", json=token_exchange_payload)
        token_res.raise_for_status()
        tokens = token_res.json()

    # Step 7: Persist tokens locally
    save_tokens(tokens)
    return tokens
