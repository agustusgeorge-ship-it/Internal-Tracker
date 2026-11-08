"""Database models: company equipment, employee requests and handbacks.

The status rules live here, in one place, so every view and the admin
move an item through its life the same way:

    In stock -> Reserved (requested) -> Assigned (approved)
    Reserved -> In stock (request rejected or cancelled)
    Assigned -> In stock or In repair (handed back)
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Case, IntegerField, Q, When
from django.urls import reverse
from django.utils import timezone


class Equipment(models.Model):
    """One physical item owned by the company, identified by serial number."""

    class Type(models.TextChoices):
        """Kinds of equipment an employee can choose from."""

        LAPTOP = "laptop", "Laptop"
        MONITOR = "monitor", "Monitor"
        PHONE = "phone", "Phone"
        PERIPHERAL = "peripheral", "Peripheral"
        INFRASTRUCTURE = "infrastructure", "Infrastructure"

    class Condition(models.TextChoices):
        """How good the item is. Bad items cannot be requested."""

        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        BAD = "bad", "Bad (needs repair)"

    class Status(models.TextChoices):
        """Where the item is in its life."""

        IN_STOCK = "in_stock", "In stock"
        RESERVED = "reserved", "Reserved"
        ASSIGNED = "assigned", "Assigned"
        IN_REPAIR = "in_repair", "In repair"
        RETIRED = "retired", "Retired"

    REQUESTABLE_CONDITIONS = (Condition.GOOD, Condition.FAIR)

    name = models.CharField("name / model", max_length=120)
    serial_number = models.CharField(max_length=64, unique=True)
    equipment_type = models.CharField(
        "type", max_length=20, choices=Type.choices
    )
    specification = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short spec shown to employees, e.g. 16 GB RAM, 512 GB SSD.",
    )
    condition = models.CharField(
        max_length=10, choices=Condition.choices, default=Condition.GOOD
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_STOCK
    )
    location = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="equipment_held",
        help_text="Set automatically when a request is approved.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["equipment_type", "name", "serial_number"]
        verbose_name_plural = "equipment"

    def __str__(self):
        """Readable label used in forms, the admin and messages."""
        return f"{self.name} ({self.serial_number})"

    def get_absolute_url(self):
        """Manager detail page for this item."""
        return reverse("manage-equipment-detail", kwargs={"pk": self.pk})

    @classmethod
    def available(cls):
        """Items an employee may request: in stock and not in bad condition."""
        return cls.objects.filter(
            status=cls.Status.IN_STOCK,
            condition__in=cls.REQUESTABLE_CONDITIONS,
        )

    @property
    def is_requestable(self):
        """True when this item can be requested right now."""
        return (
            self.status == self.Status.IN_STOCK
            and self.condition in self.REQUESTABLE_CONDITIONS
        )

    @property
    def can_be_deleted(self):
        """Only items with no history and not out with someone can be deleted.

        Anything else should be marked Retired, so records stay accurate.
        """
        return (
            self.status not in (self.Status.RESERVED, self.Status.ASSIGNED)
            and not self.requests.exists()
            and not self.handbacks.exists()
        )


def type_order():
    """Sort expression that lists types in their menu order, laptops first."""
    return Case(
        *[
            When(equipment_type=value, then=position)
            for position, value in enumerate(Equipment.Type.values)
        ],
        output_field=IntegerField(),
    )


class EquipmentRequest(models.Model):
    """An employee asking for one item, which a manager approves or rejects."""

    class Status(models.TextChoices):
        """Stages of a request. Cancelling deletes the request."""

        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="equipment_requests",
    )
    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT, related_name="requests"
    )
    job_title = models.CharField(
        max_length=100,
        help_text=(
            "Helps the manager check this is the right kit for the role."
        ),
    )
    start_date = models.DateField(
        help_text="The date you need the equipment from."
    )
    note = models.TextField(
        "note for the manager", max_length=500, blank=True
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    manager_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # The database itself refuses two pending requests for one item.
            models.UniqueConstraint(
                fields=["equipment"],
                condition=Q(status="pending"),
                name="one_pending_request_per_item",
            ),
        ]

    def __str__(self):
        """Readable label for the admin."""
        return f"{self.employee} - {self.equipment} ({self.status})"

    @property
    def is_pending(self):
        """True while the employee can still edit or cancel the request."""
        return self.status == self.Status.PENDING

    def approve(self, manager, note=""):
        """Approve the request and assign the item to the employee."""
        with transaction.atomic():
            request = EquipmentRequest.objects.select_for_update().get(
                pk=self.pk
            )
            if not request.is_pending:
                raise ValidationError("This request has already been decided.")
            item = Equipment.objects.select_for_update().get(
                pk=request.equipment_id
            )
            item.status = Equipment.Status.ASSIGNED
            item.assigned_to_id = request.employee_id
            item.save(update_fields=["status", "assigned_to", "updated_at"])
            self._record_decision(self.Status.APPROVED, manager, note)

    def reject(self, manager, reason):
        """Reject the request with a reason and return the item to stock."""
        if not reason.strip():
            raise ValidationError("Give a reason so the employee knows why.")
        with transaction.atomic():
            request = EquipmentRequest.objects.select_for_update().get(
                pk=self.pk
            )
            if not request.is_pending:
                raise ValidationError("This request has already been decided.")
            release_item(request.equipment_id)
            self._record_decision(self.Status.REJECTED, manager, reason)

    def _record_decision(self, status, manager, note):
        """Save who decided, when, and what they said."""
        self.status = status
        self.reviewed_by = manager
        self.reviewed_at = timezone.now()
        self.manager_note = note.strip()
        self.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "manager_note",
                "updated_at",
            ]
        )


class Handback(models.Model):
    """A record of an employee (usually a leaver) returning an item."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT, related_name="handbacks"
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="handbacks",
    )
    returned_on = models.DateField(default=timezone.localdate)
    condition_on_return = models.CharField(
        max_length=10, choices=Equipment.Condition.choices
    )
    notes = models.TextField(blank=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="handbacks_checked",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-returned_on", "-created_at"]

    def __str__(self):
        """Readable label for the admin."""
        return f"{self.equipment} returned by {self.employee}"

    def apply_to_equipment(self):
        """Put the item back in stock, or into repair if it came back bad."""
        item = self.equipment
        item.condition = self.condition_on_return
        item.status = (
            Equipment.Status.IN_REPAIR
            if self.condition_on_return == Equipment.Condition.BAD
            else Equipment.Status.IN_STOCK
        )
        item.assigned_to = None
        item.save(
            update_fields=["condition", "status", "assigned_to", "updated_at"]
        )


def reserve_item(equipment_id):
    """Lock an item and mark it Reserved, or fail if it was just taken."""
    item = Equipment.objects.select_for_update().get(pk=equipment_id)
    if not item.is_requestable:
        raise ValidationError(
            "Sorry, that item has just been taken. Please choose another."
        )
    item.status = Equipment.Status.RESERVED
    item.save(update_fields=["status", "updated_at"])
    return item


def release_item(equipment_id):
    """Put a Reserved item back in stock (request rejected or cancelled)."""
    Equipment.objects.filter(
        pk=equipment_id, status=Equipment.Status.RESERVED
    ).update(status=Equipment.Status.IN_STOCK, updated_at=timezone.now())
