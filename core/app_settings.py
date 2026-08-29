from MySpaceShared.core.app_settings import (
    ACCENT_COLORS,
    THEME_MODE_OPTIONS,
    AppSettings,
    AppSettingsData,
    accent_seed_value,
    build_theme,
    theme_mode_value,
)

APP_SETTINGS = AppSettings(app_name="mymoney")

__all__ = [
    "ACCENT_COLORS",
    "APP_SETTINGS",
    "THEME_MODE_OPTIONS",
    "AppSettings",
    "AppSettingsData",
    "accent_seed_value",
    "build_theme",
    "theme_mode_value",
]
