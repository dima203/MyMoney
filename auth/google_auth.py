"""Google OAuth 2.0 flow для Flet desktop клиента.

Запускает ephemeral localhost HTTP-сервер, открывает браузер для
авторизации Google, перехватывает auth code из redirect, отправляет
его на бэкенд и получает JWT.
"""

from __future__ import annotations

import logging
import secrets
import socket
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests

logger = logging.getLogger(__name__)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_CLIENT_ID = "484764873818-dk4tqe45glgojtubn5p602bultkib681.apps.googleusercontent.com"


class OAuthCallbackError(Exception):
    """Ошибка в OAuth callback (неверный code, и т.д.)."""


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler для перехвата Google OAuth callback."""

    auth_code: str | None = None
    error: str | None = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        if "code" in params:
            _OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Authorization successful!</h2>"
                b"<p>You can close this window.</p></body></html>"
            )
        elif "error" in params:
            _OAuthCallbackHandler.error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>Error: {params['error'][0]}</h2>"
                f"</body></html>".encode()
            )
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class GoogleOAuthFlow:
    """Google OAuth 2.0 flow для desktop приложения.

    Запускает локальный HTTP-сервер, открывает браузер для авторизации,
    перехватывает auth code и отправляет его на бэкенд для получения JWT.
    """

    def __init__(self, backend_url: str, client_id: str | None = None):
        self.backend_url = backend_url.rstrip("/")
        self.client_id = client_id or GOOGLE_CLIENT_ID

    def start(self) -> dict:
        """Запускает OAuth flow и возвращает {'access': ..., 'refresh': ...}."""

        if not self.client_id:
            raise OAuthCallbackError(
                "Google OAuth Client ID is not configured. "
                "Set GOOGLE_CLIENT_ID in auth/google_auth.py"
            )

        port = self._find_available_port()
        redirect_uri = f"http://localhost:{port}/callback"
        state = secrets.token_urlsafe(32)

        auth_url = self._build_auth_url(redirect_uri, state)
        logger.info("Starting Google OAuth flow on port %d", port)

        _OAuthCallbackHandler.auth_code = None
        _OAuthCallbackHandler.error = None

        server = HTTPServer(("localhost", port), _OAuthCallbackHandler)
        server_thread = threading.Thread(target=server.handle_request, daemon=True)
        server_thread.start()

        webbrowser.open(auth_url)
        logger.info("Opened browser for Google auth: %s", auth_url[:80] + "...")

        server_thread.join(timeout=120)
        server.server_close()

        if _OAuthCallbackHandler.error:
            logger.warning("Google OAuth error: %s", _OAuthCallbackHandler.error)
            raise OAuthCallbackError(f"Google OAuth error: {_OAuthCallbackHandler.error}")

        if not _OAuthCallbackHandler.auth_code:
            logger.warning("Google OAuth: no auth code received (timeout)")
            raise OAuthCallbackError("Authorization timed out or was cancelled.")

        code = _OAuthCallbackHandler.auth_code
        logger.info("Received auth code from Google, exchanging for tokens...")

        return self._exchange_code(code, redirect_uri)

    def _exchange_code(self, code: str, redirect_uri: str = "postmessage") -> dict:
        """Отправка auth code на бэкенд для получения JWT."""
        try:
            resp = requests.post(
                f"{self.backend_url}/api/v1/auth/google/",
                json={"code": code, "redirect_uri": redirect_uri},
                timeout=15,
                proxies={"http": None, "https": None},
            )
        except requests.exceptions.ConnectionError as exc:
            raise OAuthCallbackError(f"Backend unreachable: {exc}") from exc

        if resp.status_code != 200:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except ValueError:
                pass
            if "<html" in detail.lower() or len(detail) > 200:
                detail = f"HTTP {resp.status_code}"
            logger.warning("Google auth failed: status=%d detail=%s", resp.status_code, detail)
            raise OAuthCallbackError(detail)

        payload = resp.json()
        logger.info("Google auth successful")
        return {"access": payload["access"], "refresh": payload["refresh"]}

    def _build_auth_url(self, redirect_uri: str, state: str) -> str:
        """Формирование Google OAuth URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email profile",
            "access_type": "offline",
            "state": state,
            "prompt": "consent",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTH_ENDPOINT}?{query}"

    @staticmethod
    def _find_available_port() -> int:
        """Поиск свободного порта для ephemeral HTTP-сервера."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", 0))
            return s.getsockname()[1]


__all__ = ["GoogleOAuthFlow", "OAuthCallbackError"]
