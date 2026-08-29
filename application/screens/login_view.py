import flet as ft
from MySpaceShared.screens.login_view import LoginView as SharedLoginView


def _authenticate(backend_url: str) -> tuple[bool, str]:
    from application.api.token_store import TokenData, TokenStore
    from auth.google_auth import GoogleOAuthFlow, OAuthCallbackError

    logger = __import__("logging").getLogger(__name__)
    logger.info("Starting authentication flow, backend_url=%s", backend_url)
    try:
        flow = GoogleOAuthFlow(backend_url=backend_url)
        tokens = flow.start()
        logger.info("OAuth flow completed, saving tokens to store")

        store = TokenStore(app_name="mymoney")
        store.save(
            TokenData(
                access=tokens.get("access", ""),
                refresh=tokens.get("refresh", ""),
            )
        )

        return True, ""
    except OAuthCallbackError as exc:
        logger.error("OAuth callback error: %s", exc)
        return False, str(exc)
    except Exception as exc:
        logger.exception("Unexpected error during authentication")
        return False, f"Не удалось подключиться к серверу: {exc}"


class LoginView(SharedLoginView):
    def __init__(self, backend_url: str, on_success):
        super().__init__(
            backend_url=backend_url,
            on_success=on_success,
            app_title="MyMoney",
            app_icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
            on_authenticate=_authenticate,
        )


__all__ = ["LoginView"]
