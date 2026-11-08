"""Django admin: a back-office view of all equipment, requests and handbacks.

Day-to-day approving and handbacks happen on the manager pages, which
keep item statuses in step. Here, the status fields that the workflow
controls are read-only so they cannot drift out of step by hand.
"""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import Equipment, EquipmentRequest, Handback


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """Stock list with filters and search."""

    list_display = (
        "name",
        "serial_number",
        "equipment_type",
        "condition",
        "status",
        "assigned_to",
        "location",
    )
    list_filter = ("equipment_type", "condition", "status")
    search_fields = ("name", "serial_number", "location")
    readonly_fields = ("assigned_to", "created_at", "updated_at")


@admin.register(EquipmentRequest)
class EquipmentRequestAdmin(admin.ModelAdmin):
    """Requests, with a bulk Approve action for the back office."""

    list_display = (
        "employee",
        "equipment",
        "job_title",
        "start_date",
        "status",
        "reviewed_by",
    )
    list_filter = ("status", "equipment__equipment_type")
    search_fields = ("employee__username", "equipment__name", "job_title")
    readonly_fields = (
        "status",
        "reviewed_by",
        "reviewed_at",
        "created_at",
        "updated_at",
    )
    actions = ["approve_selected"]

    @admin.action(description="Approve selected pending requests")
    def approve_selected(self, request, queryset):
        """Approve each pending request through the model's own rules."""
        approved = 0
        for equipment_request in queryset:
            try:
                equipment_request.approve(request.user)
            except ValidationError:
                continue
            approved += 1
        self.message_user(
            request,
            f"{approved} request(s) approved. Requests already decided "
            "were skipped. To reject, use the Requests page so the "
            "employee is given a reason.",
            messages.SUCCESS,
        )


@admin.register(Handback)
class HandbackAdmin(admin.ModelAdmin):
    """History of returned equipment (recorded from the manager pages)."""

    list_display = (
        "equipment",
        "employee",
        "returned_on",
        "condition_on_return",
        "checked_by",
    )
    list_filter = ("condition_on_return",)
    search_fields = ("equipment__name", "equipment__serial_number",
                     "employee__username")

    def has_add_permission(self, request):
        """Handbacks are added from the item page so the item is updated."""
        return False
