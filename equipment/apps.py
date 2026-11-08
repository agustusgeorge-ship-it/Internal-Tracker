"""App config for equipment: stock, requests, approvals and handbacks."""

from django.apps import AppConfig


class EquipmentConfig(AppConfig):
    """Default settings for the equipment app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "equipment"
