from MySpaceShared.api.rest_client import (
    ApiError,
    AuthenticationError,
    BackendUnreachableError,
    RestClientError,
)
from MySpaceShared.api.rest_client import (
    RestClient as BaseRestClient,
)


class RestClient(BaseRestClient):
    def __init__(
        self,
        base_url=None,
        token_store=None,
        timeout: float = 15.0,
        trust_proxy: bool | None = None,
    ):
        super().__init__(
            app_name="mymoney",
            base_url=base_url,
            token_store=token_store,
            timeout=timeout,
            trust_proxy=trust_proxy,
        )

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


__all__ = [
    "ApiError",
    "AuthenticationError",
    "BackendUnreachableError",
    "RestClient",
    "RestClientError",
]
