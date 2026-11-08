"""Views for the dashboard, employee requests and the manager area.

Access rules are enforced here on the server, not only by hiding links:
- Every page except home needs a login (LoginRequiredMixin).
- Employees can only reach their own requests: every lookup is filtered
  by ``employee=request.user``, so another person's request is a 404.
- Manager pages use ManagerRequiredMixin, which returns 403 to employees.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    ApproveForm,
    EquipmentForm,
    EquipmentRequestForm,
    HandbackForm,
    RejectForm,
)
from .models import (
    Equipment,
    EquipmentRequest,
    Handback,
    release_item,
    reserve_item,
    type_order,
)

MAX_SEARCH_LENGTH = 100


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allow only managers (staff users). Employees get a 403 page."""

    def test_func(self):
        """Managers are Django staff users."""
        return self.request.user.is_staff


def search_text(request):
    """Read the search box, trimmed and capped to keep queries small."""
    return request.GET.get("q", "").strip()[:MAX_SEARCH_LENGTH]


def home(request):
    """Public welcome page, or the right dashboard for the logged-in user."""
    if not request.user.is_authenticated:
        return render(request, "home.html")
    if request.user.is_staff:
        return render(request, "equipment/manager_dashboard.html",
                      manager_dashboard_context())
    requests = request.user.equipment_requests.select_related("equipment")
    return render(request, "equipment/employee_dashboard.html", {
        "pending_total": requests.filter(
            status=EquipmentRequest.Status.PENDING).count(),
        "held_total": request.user.equipment_held.count(),
        "available_total": Equipment.available().count(),
        "recent_requests": requests[:5],
    })


def manager_dashboard_context():
    """Counts and lists the manager needs to see first."""
    status_counts = dict(
        Equipment.objects.values("status")
        .annotate(total=Count("id"))
        .values_list("status", "total")
    )
    available = dict(
        Equipment.available()
        .values("equipment_type")
        .annotate(total=Count("id"))
        .values_list("equipment_type", "total")
    )
    pending = EquipmentRequest.objects.filter(
        status=EquipmentRequest.Status.PENDING
    ).select_related("employee", "equipment")
    soon = timezone.localdate() + timedelta(days=14)
    return {
        "pending_total": pending.count(),
        "in_stock_total": status_counts.get(Equipment.Status.IN_STOCK, 0),
        "assigned_total": status_counts.get(Equipment.Status.ASSIGNED, 0),
        "attention_total": Equipment.objects.filter(
            Q(status=Equipment.Status.IN_REPAIR)
            | Q(condition=Equipment.Condition.BAD)
        ).exclude(status=Equipment.Status.RETIRED).count(),
        "starting_soon": pending.filter(start_date__lte=soon)
        .order_by("start_date")[:6],
        "type_counts": [
            (value, label, available.get(value, 0))
            for value, label in Equipment.Type.choices
        ],
    }


# ---------------------------------------------------------------- employees


class CatalogueView(LoginRequiredMixin, ListView):
    """Equipment an employee can request, with a type filter and search."""

    template_name = "equipment/catalogue.html"
    context_object_name = "items"
    paginate_by = 12

    def get_queryset(self):
        """Only in-stock items in good or fair condition, laptops first."""
        items = Equipment.available().order_by(type_order(), "name")
        self.selected_type = self.request.GET.get("type", "")
        if self.selected_type in Equipment.Type.values:
            items = items.filter(equipment_type=self.selected_type)
        else:
            self.selected_type = ""
        self.query = search_text(self.request)
        if self.query:
            items = items.filter(
                Q(name__icontains=self.query)
                | Q(specification__icontains=self.query)
            )
        return items

    def get_context_data(self, **kwargs):
        """Pass the filters back so the page can keep them selected."""
        context = super().get_context_data(**kwargs)
        context.update({
            "types": Equipment.Type.choices,
            "selected_type": self.selected_type,
            "query": self.query,
        })
        return context


class OwnRequestMixin(LoginRequiredMixin):
    """Limit lookups to the logged-in employee's own requests."""

    def get_queryset(self):
        """Another user's request simply does not exist here (404)."""
        return EquipmentRequest.objects.filter(
            employee=self.request.user
        ).select_related("equipment")


class PendingOnlyMixin(OwnRequestMixin):
    """Block edit and cancel once a manager has decided."""

    def dispatch(self, request, *args, **kwargs):
        """Redirect with a message if the request is no longer pending."""
        if request.user.is_authenticated:
            equipment_request = get_object_or_404(
                self.get_queryset(), pk=kwargs["pk"]
            )
            if not equipment_request.is_pending:
                messages.error(
                    request,
                    "This request has already been "
                    f"{equipment_request.get_status_display().lower()} "
                    "and can no longer be changed.",
                )
                return redirect("request-list")
        return super().dispatch(request, *args, **kwargs)


class RequestListView(OwnRequestMixin, ListView):
    """The employee's own requests, newest first (Read)."""

    template_name = "equipment/request_list.html"
    context_object_name = "equipment_requests"
    paginate_by = 10


class RequestCreateView(LoginRequiredMixin, CreateView):
    """An employee requests an item (Create). The item becomes Reserved."""

    model = EquipmentRequest
    form_class = EquipmentRequestForm
    template_name = "equipment/request_form.html"
    success_url = reverse_lazy("request-list")

    def get_form_kwargs(self):
        """Give the form the employee, for the one-per-type rule."""
        kwargs = super().get_form_kwargs()
        kwargs["employee"] = self.request.user
        return kwargs

    def get_initial(self):
        """Pre-select the item chosen in the catalogue."""
        initial = super().get_initial()
        initial["equipment"] = self.request.GET.get("equipment")
        initial["start_date"] = timezone.localdate()
        last = self.request.user.equipment_requests.first()
        if last:
            initial["job_title"] = last.job_title
        return initial

    def form_valid(self, form):
        """Reserve the item and save the request in one transaction."""
        form.instance.employee = self.request.user
        try:
            with transaction.atomic():
                reserve_item(form.cleaned_data["equipment"].pk)
                response = super().form_valid(form)
        except ValidationError as error:
            form.add_error("equipment", error)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Request sent for {self.object.equipment.name}. "
            "A manager will review it.",
        )
        return response

    def form_invalid(self, form):
        """Explain why the request was not sent."""
        messages.error(self.request, "Please correct the highlighted fields.")
        return super().form_invalid(form)


class RequestUpdateView(PendingOnlyMixin, UpdateView):
    """An employee changes a pending request (Update)."""

    form_class = EquipmentRequestForm
    template_name = "equipment/request_form.html"
    success_url = reverse_lazy("request-list")

    def get_form_kwargs(self):
        """Give the form the employee, for the one-per-type rule."""
        kwargs = super().get_form_kwargs()
        kwargs["employee"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """If the item changed, free the old one and reserve the new one."""
        old_item_id = form.initial["equipment"]
        new_item = form.cleaned_data["equipment"]
        try:
            with transaction.atomic():
                if new_item.pk != old_item_id:
                    release_item(old_item_id)
                    reserve_item(new_item.pk)
                response = super().form_valid(form)
        except ValidationError as error:
            form.add_error("equipment", error)
            return self.form_invalid(form)
        messages.success(self.request, "Your request has been updated.")
        return response

    def form_invalid(self, form):
        """Explain why the change was not saved."""
        messages.error(self.request, "Please correct the highlighted fields.")
        return super().form_invalid(form)


class RequestDeleteView(PendingOnlyMixin, DeleteView):
    """An employee cancels a pending request (Delete). The item is freed."""

    template_name = "equipment/request_confirm_delete.html"
    success_url = reverse_lazy("request-list")
    context_object_name = "equipment_request"

    def form_valid(self, form):
        """Delete the request and put the item back in stock."""
        with transaction.atomic():
            release_item(self.object.equipment_id)
            response = super().form_valid(form)
        messages.success(
            self.request,
            f"Your request for {self.object.equipment.name} was cancelled.",
        )
        return response


class MyEquipmentView(LoginRequiredMixin, ListView):
    """Items currently assigned to the logged-in employee."""

    template_name = "equipment/my_equipment.html"
    context_object_name = "items"

    def get_queryset(self):
        """Only items where assigned_to is this user."""
        return self.request.user.equipment_held.all()


# ----------------------------------------------------------------- managers


class StockListView(ManagerRequiredMixin, ListView):
    """All equipment, with search and filters (manager Read)."""

    template_name = "manage/equipment_list.html"
    context_object_name = "items"
    paginate_by = 20

    FILTERS = {
        "type": ("equipment_type", Equipment.Type),
        "status": ("status", Equipment.Status),
        "condition": ("condition", Equipment.Condition),
    }

    def get_queryset(self):
        """Apply search, the three filters and an optional holder."""
        items = Equipment.objects.select_related("assigned_to").order_by(
            type_order(), "name"
        )
        self.active = {}
        for param, (field, choices) in self.FILTERS.items():
            value = self.request.GET.get(param, "")
            if value in choices.values:
                items = items.filter(**{field: value})
                self.active[param] = value
        holder = self.request.GET.get("holder", "")
        self.holder = None
        if holder.isdigit():
            self.holder = User.objects.filter(pk=holder).first()
            items = items.filter(assigned_to_id=holder)
        self.query = search_text(self.request)
        if self.query:
            items = items.filter(
                Q(name__icontains=self.query)
                | Q(serial_number__icontains=self.query)
                | Q(location__icontains=self.query)
            )
        return items

    def get_context_data(self, **kwargs):
        """Pass the filter choices and current values to the template."""
        context = super().get_context_data(**kwargs)
        context.update({
            "query": self.query,
            "active": self.active,
            "holder": self.holder,
            "filters": [
                ("type", "Type", Equipment.Type.choices),
                ("status", "Status", Equipment.Status.choices),
                ("condition", "Condition", Equipment.Condition.choices),
            ],
        })
        return context


class StockDetailView(ManagerRequiredMixin, DetailView):
    """One item with its full request and handback history."""

    model = Equipment
    template_name = "manage/equipment_detail.html"
    context_object_name = "item"

    def get_context_data(self, **kwargs):
        """Add the item's history."""
        context = super().get_context_data(**kwargs)
        context["history"] = self.object.requests.select_related(
            "employee", "reviewed_by"
        )
        context["handbacks"] = self.object.handbacks.select_related(
            "employee", "checked_by"
        )
        return context


class StockCreateView(ManagerRequiredMixin, CreateView):
    """A manager adds an item to stock (Create)."""

    model = Equipment
    form_class = EquipmentForm
    template_name = "manage/equipment_form.html"

    def form_valid(self, form):
        """Save and confirm."""
        messages.success(self.request, "Equipment added to stock.")
        return super().form_valid(form)

    def form_invalid(self, form):
        """Explain why nothing was saved."""
        messages.error(self.request, "Please correct the highlighted fields.")
        return super().form_invalid(form)


class StockUpdateView(ManagerRequiredMixin, UpdateView):
    """A manager edits an item, including its condition (Update)."""

    model = Equipment
    form_class = EquipmentForm
    template_name = "manage/equipment_form.html"
    context_object_name = "item"

    def form_valid(self, form):
        """Save and confirm."""
        messages.success(self.request, "Equipment updated.")
        return super().form_valid(form)

    def form_invalid(self, form):
        """Explain why nothing was saved."""
        messages.error(self.request, "Please correct the highlighted fields.")
        return super().form_invalid(form)


class StockDeleteView(ManagerRequiredMixin, DeleteView):
    """A manager removes an item with no history (Delete)."""

    model = Equipment
    template_name = "manage/equipment_confirm_delete.html"
    success_url = reverse_lazy("manage-equipment-list")
    context_object_name = "item"

    def form_valid(self, form):
        """Refuse to delete items that are out or have history."""
        if not self.object.can_be_deleted:
            messages.error(
                self.request,
                "This item has request or handback history, or is out with "
                "someone, so it cannot be deleted. Set its status to Retired "
                "instead.",
            )
            return redirect(self.object)
        messages.success(self.request, f"{self.object} was deleted.")
        return super().form_valid(form)


class ManagerRequestListView(ManagerRequiredMixin, ListView):
    """Requests waiting for a decision, soonest start date first."""

    template_name = "manage/request_list.html"
    context_object_name = "equipment_requests"
    paginate_by = 20

    def get_queryset(self):
        """Pending by default; ?show=decided lists past decisions."""
        self.show = self.request.GET.get("show", "pending")
        requests = EquipmentRequest.objects.select_related(
            "employee", "equipment", "reviewed_by"
        )
        if self.show == "decided":
            return requests.exclude(
                status=EquipmentRequest.Status.PENDING
            ).order_by("-reviewed_at")
        self.show = "pending"
        return requests.filter(
            status=EquipmentRequest.Status.PENDING
        ).order_by("start_date", "created_at")

    def get_context_data(self, **kwargs):
        """Tell the template which tab is open."""
        context = super().get_context_data(**kwargs)
        context["show"] = self.show
        return context


class RequestReviewView(ManagerRequiredMixin, View):
    """Show one request with Approve and Reject forms, and handle each."""

    template_name = "manage/request_review.html"

    def get_request(self, pk):
        """Load the request with everything the page shows."""
        return get_object_or_404(
            EquipmentRequest.objects.select_related(
                "employee", "equipment", "reviewed_by"
            ),
            pk=pk,
        )

    def render_page(self, equipment_request, approve_form=None,
                    reject_form=None):
        """Render the review page with fresh or bound forms."""
        employee = equipment_request.employee
        return render(self.request, self.template_name, {
            "equipment_request": equipment_request,
            "approve_form": approve_form or ApproveForm(),
            "reject_form": reject_form or RejectForm(),
            "already_held": employee.equipment_held.all(),
        })

    def get(self, request, pk):
        """Show the request."""
        return self.render_page(self.get_request(pk))

    def post(self, request, pk):
        """Approve or reject, depending on which button was pressed."""
        equipment_request = self.get_request(pk)
        if "approve" in request.POST:
            form = ApproveForm(request.POST)
            if form.is_valid():
                return self.decide(
                    equipment_request.approve,
                    form.cleaned_data["note"],
                    f"Approved. {equipment_request.equipment.name} is now "
                    f"assigned to {equipment_request.employee.username}.",
                )
            return self.render_page(equipment_request, approve_form=form)
        form = RejectForm(request.POST)
        if form.is_valid():
            return self.decide(
                equipment_request.reject,
                form.cleaned_data["reason"],
                "Request rejected. The item is back in stock.",
            )
        messages.error(request, "Give a reason for rejecting this request.")
        return self.render_page(equipment_request, reject_form=form)

    def decide(self, action, text, success_message):
        """Run approve or reject, then return to the queue."""
        try:
            action(self.request.user, text)
        except ValidationError as error:
            messages.error(self.request, error.messages[0])
        else:
            messages.success(self.request, success_message)
        return redirect("manage-request-list")


class HandbackCreateView(ManagerRequiredMixin, CreateView):
    """A manager records an assigned item coming back."""

    model = Handback
    form_class = HandbackForm
    template_name = "manage/handback_form.html"

    def dispatch(self, request, *args, **kwargs):
        """Only assigned items can be handed back."""
        if request.user.is_authenticated and request.user.is_staff:
            self.item = get_object_or_404(Equipment, pk=kwargs["pk"])
            if self.item.status != Equipment.Status.ASSIGNED:
                messages.error(
                    request, "Only assigned items can be handed back."
                )
                return redirect(self.item)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Start with today's date and the item's current condition."""
        return {
            "returned_on": timezone.localdate(),
            "condition_on_return": self.item.condition,
        }

    def get_context_data(self, **kwargs):
        """Show which item and which employee."""
        context = super().get_context_data(**kwargs)
        context["item"] = self.item
        return context

    def form_valid(self, form):
        """Save the handback and update the item in one transaction."""
        form.instance.equipment = self.item
        form.instance.employee = self.item.assigned_to
        form.instance.checked_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            self.object.apply_to_equipment()
        messages.success(
            self.request,
            f"Handback recorded. {self.item.name} is now "
            f"{self.item.get_status_display().lower()}.",
        )
        return response

    def get_success_url(self):
        """Back to the item, which now shows the handback."""
        return reverse("manage-equipment-detail", kwargs={"pk": self.item.pk})


class PeopleView(ManagerRequiredMixin, TemplateView):
    """Employees, what they hold and what they are waiting for."""

    template_name = "manage/people.html"

    def get_context_data(self, **kwargs):
        """One row per employee with their totals."""
        context = super().get_context_data(**kwargs)
        pending = EquipmentRequest.Status.PENDING
        context["people"] = (
            User.objects.filter(is_staff=False)
            .annotate(
                held=Count("equipment_held", distinct=True),
                pending=Count(
                    "equipment_requests",
                    filter=Q(equipment_requests__status=pending),
                    distinct=True,
                ),
            )
            .order_by("-pending", "-held", "username")
        )
        return context
