"""HTTP-клиент к бэкенду MyMoney."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx

from .token_store import TokenData, TokenStore


class RestClientError(Exception):
    """Базовая ошибка API-клиента."""


class AuthenticationError(RestClientError):
    """Не удалось аутентифицировать/обновить токен."""


class ApiError(RestClientError):
    """Бэкенд вернул ошибку (не 2xx)."""

    def __init__(self, status_code: int, message: str = "", detail=None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(message or f"HTTP {status_code}")


class BackendUnreachableError(RestClientError):
    """Бэкенд недоступен (сеть/таймаут)."""


class RestClient:
    def __init__(
        self,
        base_url: str | None = None,
        token_store: TokenStore | None = None,
        timeout: float = 15.0,
        trust_proxy: bool | None = None,
    ):
        from core.config import SETTINGS

        self.base_url = (base_url or SETTINGS.BACKEND_URL).rstrip("/")
        self.token_store = token_store or TokenStore()
        if trust_proxy is None:
            trust_proxy = SETTINGS.BACKEND_TRUST_PROXY
        self._http = httpx.Client(timeout=timeout, trust_env=trust_proxy)
        self._access_token = ""
        self._refresh_token = ""

    def _url(self, url: str) -> str:
        if url.startswith("http"):
            return url
        return urljoin(self.base_url + "/", url.lstrip("/"))

    # ------------------------------------------------------------------ auth

    def refresh(self) -> bool:
        refresh = self._refresh_token or self.token_store.load().refresh
        if not refresh:
            return False
        try:
            resp = self._http.post(
                self._url("/api/v1/auth/token/refresh/"),
                json={"refresh": refresh},
            )
        except httpx.HTTPError:
            return False
        if resp.status_code != 200:
            self.logout()
            return False
        payload = resp.json()
        self._access_token = payload["access"]
        self._refresh_token = refresh
        self.token_store.save(
            TokenData(
                access=self._access_token,
                refresh=self._refresh_token,
                username=self.token_store.load().username,
            )
        )
        return True

    def logout(self) -> None:
        self._access_token = ""
        self._refresh_token = ""
        self.token_store.clear()

    def me(self) -> dict:
        return self._request("GET", "/api/v1/auth/me/", auth=True)

    def update_profile(self, **kwargs) -> dict:
        return self._request("PATCH", "/api/v1/auth/me/", json=kwargs, auth=True)

    # ---------------------------------------------------------------- domain

    def list_resources(self, **params) -> list:
        return self._request("GET", "/api/v1/resources/", params=params)

    def create_resource(self, payload: dict) -> dict:
        return self._request("POST", "/api/v1/resources/", json=payload)

    def delete_resource(self, resource_id: int) -> None:
        self._request("DELETE", f"/api/v1/resources/{resource_id}/")

    def list_accounts(self, **params) -> list:
        return self._request("GET", "/api/v1/accounts/", params=params)

    def create_account(self, payload: dict) -> dict:
        return self._request("POST", "/api/v1/accounts/", json=payload)

    def update_account(self, account_id: int, payload: dict) -> dict:
        return self._request("PATCH", f"/api/v1/accounts/{account_id}/", json=payload)

    def delete_account(self, account_id: int) -> None:
        self._request("DELETE", f"/api/v1/accounts/{account_id}/")

    def list_transactions(self, **params) -> list:
        return self._request("GET", "/api/v1/transactions/", params=params)

    def create_transaction(self, payload: dict) -> dict:
        return self._request("POST", "/api/v1/transactions/", json=payload)

    def update_transaction(self, tx_id: int, payload: dict) -> dict:
        return self._request("PATCH", f"/api/v1/transactions/{tx_id}/", json=payload)

    def delete_transaction(self, tx_id: int) -> None:
        self._request("DELETE", f"/api/v1/transactions/{tx_id}/")

    def list_planned_transactions(self, **params) -> list:
        return self._request("GET", "/api/v1/interactions/planned-transactions/", params=params)

    # ------------------------------------------------------------ internals

    def _request(
        self,
        method: str,
        url: str,
        *,
        auth: bool = True,
        params: dict | None = None,
        json: dict | None = None,
    ):
        headers = {}
        if auth:
            token = self._access_token or self.token_store.load().access
            if token:
                headers["Authorization"] = f"Bearer {token}"

        try:
            resp = self._http.request(method, self._url(url), headers=headers, params=params, json=json)
            if resp.status_code == 401 and auth:
                if self.refresh():
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    resp = self._http.request(
                        method,
                        self._url(url),
                        headers=headers,
                        params=params,
                        json=json,
                    )
        except httpx.HTTPError as exc:
            raise BackendUnreachableError(f"Backend unreachable: {exc}") from exc
        return self._decode(resp)

    @staticmethod
    def _decode(resp: httpx.Response):
        if 200 <= resp.status_code < 300:
            if resp.status_code == 204:
                return None
            try:
                return resp.json()
            except ValueError:
                return resp.text
        detail = None
        try:
            body = resp.json()
            detail = body.get("detail", body)
        except ValueError:
            body = resp.text
        raise ApiError(resp.status_code, detail=detail)


__all__ = [
    "RestClient",
    "RestClientError",
    "AuthenticationError",
    "ApiError",
    "BackendUnreachableError",
]
