"""Shared test data: one manager, two employees and some stock."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.utils import timezone

from equipment.models import Equipment, EquipmentRequest

PASSWORD = "Long-test-password-2026!"


def make_item(serial, kind=Equipment.Type.LAPTOP, **fields):
    """Create an item in stock with sensible defaults."""
    fields.setdefault("name", f"Item {serial}")
    return Equipment.objects.create(
        serial_number=serial, equipment_type=kind, **fields
    )


def make_request(employee, item, **fields):
    """Create a pending request and reserve the item, as the view does."""
    fields.setdefault("job_title", "Developer")
    fields.setdefault("start_date", timezone.localdate() + timedelta(days=7))
    item.status = Equipment.Status.RESERVED
    item.save()
    return EquipmentRequest.objects.create(
        employee=employee, equipment=item, **fields
    )


class TrackroomTestCase(TestCase):
    """Base class with users and items ready to use."""

    def setUp(self):
        self.manager = User.objects.create_user(
            "manager", "manager@example.com", PASSWORD, is_staff=True
        )
        self.employee = User.objects.create_user(
            "alex", "alex@example.com", PASSWORD,
            first_name="Alex", last_name="Smith",
        )
        self.other = User.objects.create_user(
            "jordan", "jordan@example.com", PASSWORD
        )
        self.laptop = make_item("LAP-1", name="MacBook Air")
        self.laptop2 = make_item("LAP-2", name="Dell XPS 13")
        self.monitor = make_item(
            "MON-1", Equipment.Type.MONITOR, name="Dell 27 monitor"
        )
        self.broken = make_item(
            "LAP-BAD", name="Broken HP", condition=Equipment.Condition.BAD
        )

    def refresh(self, *objects):
        """Reload objects from the database."""
        for obj in objects:
            obj.refresh_from_db()

    def messages(self, response):
        """Flash messages attached to a response."""
        return [str(m) for m in get_messages(response.wsgi_request)]

    def future(self, days=7):
        """A date in the future, as the form expects it."""
        return (timezone.localdate() + timedelta(days=days)).isoformat()
