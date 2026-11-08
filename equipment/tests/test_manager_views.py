"""Tests for the manager area: stock CRUD, approvals, handbacks (EST-02 to
05, EST-11 to 13)."""

from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.urls import reverse

from equipment.admin import EquipmentRequestAdmin
from equipment.models import Equipment, EquipmentRequest, Handback

from .helpers import TrackroomTestCase, make_request


class ManagerAccessTests(TrackroomTestCase):
    """Manager pages are closed to employees and visitors (EST-02)."""

    def manager_urls(self):
        """Every manager page, with real ids."""
        request = make_request(self.employee, self.laptop)
        return [
            reverse("manage-equipment-list"),
            reverse("manage-equipment-create"),
            reverse("manage-equipment-detail", args=[self.laptop.pk]),
            reverse("manage-equipment-update", args=[self.laptop.pk]),
            reverse("manage-equipment-delete", args=[self.monitor.pk]),
            reverse("manage-handback", args=[self.laptop.pk]),
            reverse("manage-request-list"),
            reverse("manage-request-review", args=[request.pk]),
            reverse("manage-people"),
        ]

    def test_employee_gets_403_on_every_manager_page(self):
        self.client.force_login(self.employee)
        for url in self.manager_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)
                self.assertContains(
                    response, "Managers only", status_code=403
                )

    def test_visitor_is_sent_to_login(self):
        for url in self.manager_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response, f"{reverse('login')}?next={url}"
                )

    def test_employee_cannot_approve_by_posting(self):
        request = make_request(self.employee, self.laptop)
        self.client.force_login(self.employee)
        response = self.client.post(
            reverse("manage-request-review", args=[request.pk]),
            {"approve": "1"},
        )
        self.assertEqual(response.status_code, 403)
        self.refresh(request)
        self.assertTrue(request.is_pending)

    def test_employee_cannot_delete_stock(self):
        self.client.force_login(self.employee)
        self.client.post(
            reverse("manage-equipment-delete", args=[self.monitor.pk])
        )
        self.assertTrue(Equipment.objects.filter(pk=self.monitor.pk).exists())

    def test_manager_sees_manager_navigation(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Today at a glance")
        self.assertContains(response, reverse("manage-request-list"))


class StockCrudTests(TrackroomTestCase):
    """Managers add, view, edit and delete equipment (EST-03 to 05)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.manager)

    def item_data(self, **overrides):
        """Valid data for the equipment form."""
        data = {
            "name": "ThinkPad T14",
            "serial_number": "lap-tp-9",
            "equipment_type": Equipment.Type.LAPTOP,
            "specification": "16 GB RAM",
            "condition": Equipment.Condition.GOOD,
            "status": Equipment.Status.IN_STOCK,
            "location": "Store room",
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_create_item(self):
        response = self.client.post(
            reverse("manage-equipment-create"), self.item_data()
        )
        item = Equipment.objects.get(serial_number="LAP-TP-9")
        self.assertRedirects(response, item.get_absolute_url())
        self.assertEqual(item.status, Equipment.Status.IN_STOCK)
        self.assertIn("Equipment added to stock.", self.messages(response))

    def test_duplicate_serial_is_rejected(self):
        response = self.client.post(
            reverse("manage-equipment-create"),
            self.item_data(serial_number="lap-1"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_required_fields(self):
        response = self.client.post(
            reverse("manage-equipment-create"),
            self.item_data(name="", serial_number=""),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Equipment.objects.count(), 4)

    def test_update_condition(self):
        url = reverse("manage-equipment-update", args=[self.laptop.pk])
        response = self.client.post(url, self.item_data(
            name="MacBook Air", serial_number="LAP-1",
            condition=Equipment.Condition.BAD,
        ))
        self.assertRedirects(response, self.laptop.get_absolute_url())
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.condition, Equipment.Condition.BAD)
        self.assertNotIn(self.laptop, Equipment.available())

    def test_status_is_locked_while_assigned(self):
        make_request(self.employee, self.laptop).approve(self.manager)
        url = reverse("manage-equipment-update", args=[self.laptop.pk])
        self.client.post(url, self.item_data(
            name="MacBook Air", serial_number="LAP-1",
            status=Equipment.Status.IN_STOCK,
        ))
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.ASSIGNED)

    def test_manual_status_choices_exclude_workflow_statuses(self):
        response = self.client.get(reverse("manage-equipment-create"))
        field = response.context["form"]["status"].field
        choices = [value for value, label in field.choices]
        self.assertNotIn(Equipment.Status.ASSIGNED, choices)
        self.assertIn(Equipment.Status.RETIRED, choices)

    def test_delete_item_without_history(self):
        url = reverse("manage-equipment-delete", args=[self.monitor.pk])
        self.assertContains(self.client.get(url), "Delete this item?")
        response = self.client.post(url)
        self.assertRedirects(response, reverse("manage-equipment-list"))
        self.assertFalse(Equipment.objects.filter(pk=self.monitor.pk).exists())

    def test_delete_refused_when_item_has_history(self):
        make_request(self.employee, self.laptop)
        url = reverse("manage-equipment-delete", args=[self.laptop.pk])
        self.assertContains(self.client.get(url), "Retired")
        response = self.client.post(url)
        self.assertRedirects(response, self.laptop.get_absolute_url())
        self.assertTrue(Equipment.objects.filter(pk=self.laptop.pk).exists())

    def test_stock_list_filters_and_search(self):
        url = reverse("manage-equipment-list")
        response = self.client.get(url, {"condition": "bad"})
        self.assertEqual(list(response.context["items"]), [self.broken])
        response = self.client.get(url, {"type": "monitor"})
        self.assertEqual(list(response.context["items"]), [self.monitor])
        response = self.client.get(url, {"q": "LAP-2"})
        self.assertEqual(list(response.context["items"]), [self.laptop2])

    def test_stock_list_by_holder(self):
        make_request(self.employee, self.laptop).approve(self.manager)
        response = self.client.get(
            reverse("manage-equipment-list"), {"holder": self.employee.pk}
        )
        self.assertEqual(list(response.context["items"]), [self.laptop])
        self.assertContains(response, "Equipment held by Alex Smith")

    def test_detail_shows_history(self):
        make_request(self.employee, self.laptop).reject(self.manager, "No")
        response = self.client.get(self.laptop.get_absolute_url())
        self.assertContains(response, "Requested by <strong>alex</strong>")


class ApprovalTests(TrackroomTestCase):
    """Managers approve or reject requests (EST-11)."""

    def setUp(self):
        super().setUp()
        self.request = make_request(self.employee, self.laptop)
        self.url = reverse("manage-request-review", args=[self.request.pk])
        self.client.force_login(self.manager)

    def test_queue_lists_pending_requests(self):
        response = self.client.get(reverse("manage-request-list"))
        self.assertContains(response, "Alex Smith")
        self.assertContains(response, "MacBook Air")

    def test_approve(self):
        response = self.client.post(self.url, {"approve": "1", "note": ""})
        self.assertRedirects(response, reverse("manage-request-list"))
        self.refresh(self.request, self.laptop)
        self.assertEqual(self.request.status, EquipmentRequest.Status.APPROVED)
        self.assertEqual(self.request.reviewed_by, self.manager)
        self.assertEqual(self.laptop.assigned_to, self.employee)
        self.assertIn(
            "Approved. MacBook Air is now assigned to alex.",
            self.messages(response),
        )

    def test_reject_needs_reason(self):
        response = self.client.post(self.url, {"reject": "1", "reason": ""})
        self.assertEqual(response.status_code, 200)
        self.refresh(self.request)
        self.assertTrue(self.request.is_pending)

    def test_reject_with_reason(self):
        response = self.client.post(
            self.url, {"reject": "1", "reason": "Choose a Windows laptop"}
        )
        self.assertRedirects(response, reverse("manage-request-list"))
        self.refresh(self.request, self.laptop)
        self.assertEqual(self.request.status, EquipmentRequest.Status.REJECTED)
        self.assertEqual(self.request.manager_note, "Choose a Windows laptop")
        self.assertEqual(self.laptop.status, Equipment.Status.IN_STOCK)

    def test_deciding_twice_shows_an_error(self):
        self.request.approve(self.manager)
        response = self.client.post(
            self.url, {"reject": "1", "reason": "Too late"}
        )
        self.assertIn(
            "This request has already been decided.", self.messages(response)
        )
        self.refresh(self.request)
        self.assertEqual(self.request.status, EquipmentRequest.Status.APPROVED)

    def test_decided_tab(self):
        self.request.approve(self.manager)
        response = self.client.get(
            reverse("manage-request-list"), {"show": "decided"}
        )
        self.assertContains(response, "Approved")

    def test_admin_bulk_approve(self):
        request = RequestFactory().post("/admin/")
        request.user = self.manager
        model_admin = EquipmentRequestAdmin(EquipmentRequest, site)
        model_admin.message_user = lambda *args, **kwargs: None
        model_admin.approve_selected(request, EquipmentRequest.objects.all())
        self.refresh(self.request)
        self.assertEqual(self.request.status, EquipmentRequest.Status.APPROVED)


class HandbackViewTests(TrackroomTestCase):
    """Managers record items coming back from leavers (EST-12)."""

    def setUp(self):
        super().setUp()
        make_request(self.employee, self.laptop).approve(self.manager)
        self.url = reverse("manage-handback", args=[self.laptop.pk])
        self.client.force_login(self.manager)

    def test_record_handback(self):
        response = self.client.post(self.url, {
            "returned_on": self.future(0),
            "condition_on_return": Equipment.Condition.BAD,
            "notes": "Cracked screen",
        })
        self.assertRedirects(response, self.laptop.get_absolute_url())
        handback = Handback.objects.get()
        self.assertEqual(handback.employee, self.employee)
        self.assertEqual(handback.checked_by, self.manager)
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.IN_REPAIR)
        self.assertIsNone(self.laptop.assigned_to)

    def test_return_date_cannot_be_future(self):
        response = self.client.post(self.url, {
            "returned_on": self.future(3),
            "condition_on_return": Equipment.Condition.GOOD,
        })
        self.assertContains(response, "cannot be in the future")
        self.assertFalse(Handback.objects.exists())

    def test_only_assigned_items_can_be_handed_back(self):
        url = reverse("manage-handback", args=[self.monitor.pk])
        response = self.client.get(url)
        self.assertRedirects(response, self.monitor.get_absolute_url())

    def test_people_page_counts(self):
        make_request(self.employee, self.monitor)
        response = self.client.get(reverse("manage-people"))
        people = response.context["people"]
        alex = next(p for p in people if p.username == "alex")
        self.assertEqual(alex.held, 1)
        self.assertEqual(alex.pending, 1)
        self.assertNotIn(
            "manager", [p.username for p in response.context["people"]]
        )


class DashboardAndErrorPageTests(TrackroomTestCase):
    """Manager dashboard totals (EST-13) and custom error pages."""

    def test_manager_dashboard_totals(self):
        make_request(self.employee, self.laptop)
        make_request(self.other, self.monitor).approve(self.manager)
        self.client.force_login(self.manager)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["pending_total"], 1)
        self.assertEqual(response.context["assigned_total"], 1)
        self.assertEqual(response.context["in_stock_total"], 2)
        self.assertEqual(response.context["attention_total"], 1)
        self.assertEqual(len(response.context["starting_soon"]), 1)

    def test_custom_404_page(self):
        response = self.client.get("/no-such-page/")
        self.assertContains(response, "Page not found", status_code=404)
