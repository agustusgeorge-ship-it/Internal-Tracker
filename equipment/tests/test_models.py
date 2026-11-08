"""Tests for the status rules in equipment.models."""

from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction

from equipment.models import Equipment, EquipmentRequest, Handback

from .helpers import TrackroomTestCase, make_request


class AvailabilityTests(TrackroomTestCase):
    """Only in-stock items in good or fair condition can be requested."""

    def test_available_excludes_bad_and_reserved_items(self):
        make_request(self.employee, self.laptop2)
        available = set(Equipment.available())
        self.assertEqual(available, {self.laptop, self.monitor})

    def test_is_requestable(self):
        self.assertTrue(self.laptop.is_requestable)
        self.assertFalse(self.broken.is_requestable)

    def test_database_blocks_two_pending_requests_for_one_item(self):
        make_request(self.employee, self.laptop)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EquipmentRequest.objects.create(
                employee=self.other, equipment=self.laptop,
                job_title="Tester", start_date="2030-01-01",
            )


class DecisionTests(TrackroomTestCase):
    """Approving and rejecting move the item to the right status."""

    def test_approve_assigns_item_to_employee(self):
        request = make_request(self.employee, self.laptop)
        request.approve(self.manager, "Enjoy")
        self.refresh(request, self.laptop)
        self.assertEqual(request.status, EquipmentRequest.Status.APPROVED)
        self.assertEqual(request.reviewed_by, self.manager)
        self.assertIsNotNone(request.reviewed_at)
        self.assertEqual(request.manager_note, "Enjoy")
        self.assertEqual(self.laptop.status, Equipment.Status.ASSIGNED)
        self.assertEqual(self.laptop.assigned_to, self.employee)

    def test_reject_needs_a_reason(self):
        request = make_request(self.employee, self.laptop)
        with self.assertRaises(ValidationError):
            request.reject(self.manager, "   ")
        self.refresh(request)
        self.assertTrue(request.is_pending)

    def test_reject_returns_item_to_stock(self):
        request = make_request(self.employee, self.laptop)
        request.reject(self.manager, "Developers get the MacBook Pro")
        self.refresh(request, self.laptop)
        self.assertEqual(request.status, EquipmentRequest.Status.REJECTED)
        self.assertEqual(self.laptop.status, Equipment.Status.IN_STOCK)

    def test_a_request_cannot_be_decided_twice(self):
        request = make_request(self.employee, self.laptop)
        request.approve(self.manager)
        with self.assertRaises(ValidationError):
            request.reject(self.manager, "Changed my mind")
        with self.assertRaises(ValidationError):
            request.approve(self.manager)


class HandbackTests(TrackroomTestCase):
    """Returned items go back to stock, or to repair if bad."""

    def assign(self, item):
        """Approve a request so the item is with the employee."""
        make_request(self.employee, item).approve(self.manager)
        item.refresh_from_db()

    def test_good_return_goes_back_in_stock(self):
        self.assign(self.laptop)
        handback = Handback.objects.create(
            equipment=self.laptop, employee=self.employee,
            condition_on_return=Equipment.Condition.FAIR,
            checked_by=self.manager,
        )
        handback.apply_to_equipment()
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.IN_STOCK)
        self.assertEqual(self.laptop.condition, Equipment.Condition.FAIR)
        self.assertIsNone(self.laptop.assigned_to)

    def test_bad_return_goes_to_repair(self):
        self.assign(self.laptop)
        handback = Handback.objects.create(
            equipment=self.laptop, employee=self.employee,
            condition_on_return=Equipment.Condition.BAD,
        )
        handback.apply_to_equipment()
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.IN_REPAIR)


class DeletionRuleTests(TrackroomTestCase):
    """Items with history must be retired, not deleted."""

    def test_new_item_can_be_deleted(self):
        self.assertTrue(self.monitor.can_be_deleted)

    def test_item_with_request_history_cannot_be_deleted(self):
        request = make_request(self.employee, self.laptop)
        request.reject(self.manager, "No")
        self.refresh(self.laptop)
        self.assertFalse(self.laptop.can_be_deleted)


class SeedCommandTests(TrackroomTestCase):
    """The demo data command adds items once only."""

    def test_seed_is_safe_to_run_twice(self):
        call_command("seed_equipment", stdout=StringIO())
        count = Equipment.objects.count()
        call_command("seed_equipment", stdout=StringIO())
        self.assertEqual(Equipment.objects.count(), count)
        self.assertTrue(
            Equipment.objects.filter(serial_number="LAP-MBA-0001").exists()
        )
        self.assertEqual(
            Equipment.objects.get(serial_number="LAP-HPE-0001").status,
            Equipment.Status.IN_REPAIR,
        )
