"""App config for accounts: registration plus login and logout messages."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Connect the login and logout signal handlers when Django starts."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        """Import signals so their receivers are registered."""
        from . import signals  # noqa: F401
