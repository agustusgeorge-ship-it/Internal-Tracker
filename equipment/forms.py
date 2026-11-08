"""Forms for employee requests and the manager's stock pages."""

from django import forms
from django.utils import timezone

from .models import Equipment, EquipmentRequest, Handback, type_order


class DateInput(forms.DateInput):
    """Use the browser's own date picker.

    A date input only accepts YYYY-MM-DD. Without this format, the UK
    locale (DD/MM/YYYY) leaves the box empty when editing a request.
    """

    input_type = "date"

    def __init__(self, attrs=None, format="%Y-%m-%d"):
        """Always send dates in the format the date picker reads."""
        super().__init__(attrs=attrs, format=format)


class EquipmentRequestForm(forms.ModelForm):
    """Employee form to request, or change, one item.

    The employee is never a form field: the view sets it from the
    logged-in user, so nobody can request on someone else's behalf.
    """

    class Meta:
        model = EquipmentRequest
        fields = ("equipment", "job_title", "start_date", "note")
        widgets = {
            "start_date": DateInput(),
            "note": forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
        }
        labels = {"equipment": "Equipment"}

    def __init__(self, *args, employee, **kwargs):
        """Offer only available items, plus the one already chosen."""
        super().__init__(*args, **kwargs)
        self.employee = employee
        choices = Equipment.available()
        if self.instance.pk:
            choices = choices | Equipment.objects.filter(
                pk=self.instance.equipment_id
            )
        self.fields["equipment"].queryset = choices.order_by(
            type_order(), "name"
        )
        self.fields["equipment"].empty_label = "Choose an item"

    def clean_start_date(self):
        """New dates cannot be in the past."""
        start_date = self.cleaned_data["start_date"]
        unchanged = (
            self.instance.pk and start_date == self.instance.start_date
        )
        if start_date < timezone.localdate() and not unchanged:
            raise forms.ValidationError(
                "The start date cannot be in the past."
            )
        return start_date

    def clean_equipment(self):
        """Allow one pending request per equipment type for each employee."""
        item = self.cleaned_data["equipment"]
        pending = EquipmentRequest.objects.filter(
            employee=self.employee,
            status=EquipmentRequest.Status.PENDING,
            equipment__equipment_type=item.equipment_type,
        ).exclude(pk=self.instance.pk)
        if pending.exists():
            raise forms.ValidationError(
                "You already have a pending request for a "
                f"{item.get_equipment_type_display().lower()}. "
                "Edit that request instead."
            )
        return item


class EquipmentForm(forms.ModelForm):
    """Manager form to add or edit an item in stock."""

    # Reserved and Assigned are set by requests and handbacks, not by hand.
    MANUAL_STATUSES = (
        Equipment.Status.IN_STOCK,
        Equipment.Status.IN_REPAIR,
        Equipment.Status.RETIRED,
    )

    class Meta:
        model = Equipment
        fields = (
            "name",
            "serial_number",
            "equipment_type",
            "specification",
            "condition",
            "status",
            "location",
            "notes",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        """Lock the status while an item is reserved or with someone."""
        super().__init__(*args, **kwargs)
        status = self.fields["status"]
        if self.instance.status in self.MANUAL_STATUSES:
            status.choices = [
                choice for choice in Equipment.Status.choices
                if choice[0] in self.MANUAL_STATUSES
            ]
        else:
            status.disabled = True
            status.help_text = (
                "Set by the request or handback. Approve, reject or record "
                "a handback to change it."
            )

    def clean_serial_number(self):
        """Store serial numbers in capitals so duplicates are caught."""
        return self.cleaned_data["serial_number"].strip().upper()


class RejectForm(forms.Form):
    """The reason a manager must give when rejecting a request."""

    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=500,
        label="Reason for rejecting",
        help_text="The employee will see this on their requests page.",
    )


class ApproveForm(forms.Form):
    """An optional note a manager can add when approving."""

    note = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        max_length=500,
        required=False,
        label="Note for the employee (optional)",
    )


class HandbackForm(forms.ModelForm):
    """Manager form to record an item coming back from an employee."""

    class Meta:
        model = Handback
        fields = ("returned_on", "condition_on_return", "notes")
        widgets = {
            "returned_on": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "condition_on_return": "Bad sends the item to repair; "
            "Good or Fair puts it back in stock.",
        }

    def clean_returned_on(self):
        """A return cannot be recorded for a future date."""
        returned_on = self.cleaned_data["returned_on"]
        if returned_on > timezone.localdate():
            raise forms.ValidationError(
                "The return date cannot be in the future."
            )
        return returned_on
