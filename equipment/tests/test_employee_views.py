"""Tests for the employee pages: catalogue and request CRUD (EST-06 to 10)."""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from equipment.models import Equipment, EquipmentRequest

from .helpers import TrackroomTestCase, make_request


class LoginRequiredTests(TrackroomTestCase):
    """Logged-out visitors are sent to the login page."""

    def test_employee_pages_need_login(self):
        request = make_request(self.employee, self.laptop)
        urls = [
            reverse("catalogue"),
            reverse("request-list"),
            reverse("request-create"),
            reverse("request-update", args=[request.pk]),
            reverse("request-delete", args=[request.pk]),
            reverse("my-equipment"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response, f"{reverse('login')}?next={url}"
                )

    def test_logged_out_user_cannot_cancel_a_request(self):
        request = make_request(self.employee, self.laptop)
        self.client.post(reverse("request-delete", args=[request.pk]))
        self.assertTrue(
            EquipmentRequest.objects.filter(pk=request.pk).exists()
        )

    def test_home_page_is_public(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Create an account")


class CatalogueTests(TrackroomTestCase):
    """Employees see only what they can request (EST-06)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.employee)

    def test_only_available_items_are_listed(self):
        make_request(self.other, self.laptop2)
        response = self.client.get(reverse("catalogue"))
        self.assertContains(response, "MacBook Air")
        self.assertContains(response, "Dell 27 monitor")
        self.assertNotContains(response, "Dell XPS 13")
        self.assertNotContains(response, "Broken HP")

    def test_laptops_are_listed_first(self):
        make_item = Equipment.objects.create
        make_item(
            name="A dock", serial_number="INF-1",
            equipment_type=Equipment.Type.INFRASTRUCTURE,
        )
        response = self.client.get(reverse("catalogue"))
        first = response.context["items"][0]
        self.assertEqual(first.equipment_type, Equipment.Type.LAPTOP)

    def test_filter_by_type(self):
        response = self.client.get(reverse("catalogue"), {"type": "monitor"})
        self.assertContains(response, "Dell 27 monitor")
        self.assertNotContains(response, "MacBook Air")

    def test_unknown_type_shows_everything(self):
        response = self.client.get(reverse("catalogue"), {"type": "nope"})
        self.assertContains(response, "MacBook Air")
        self.assertContains(response, "Dell 27 monitor")

    def test_search(self):
        response = self.client.get(reverse("catalogue"), {"q": "macbook"})
        self.assertContains(response, "MacBook Air")
        self.assertNotContains(response, "Dell XPS 13")

    def test_empty_catalogue_message(self):
        Equipment.objects.update(status=Equipment.Status.ASSIGNED)
        response = self.client.get(reverse("catalogue"))
        self.assertContains(response, "Nothing available")


class CreateRequestTests(TrackroomTestCase):
    """Employees can request equipment (EST-07)."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.employee)

    def post(self, item, **overrides):
        """Send the request form."""
        data = {
            "equipment": item.pk,
            "job_title": "Junior developer",
            "start_date": self.future(),
            "note": "Left-handed",
        }
        data.update(overrides)
        return self.client.post(reverse("request-create"), data)

    def test_catalogue_choice_is_preselected(self):
        response = self.client.get(
            reverse("request-create"), {"equipment": self.laptop.pk}
        )
        self.assertEqual(
            str(response.context["form"]["equipment"].value()),
            str(self.laptop.pk),
        )

    def test_request_is_created_and_item_reserved(self):
        response = self.post(self.laptop)
        self.assertRedirects(response, reverse("request-list"))
        request = EquipmentRequest.objects.get()
        self.assertEqual(request.employee, self.employee)
        self.assertEqual(request.status, EquipmentRequest.Status.PENDING)
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.RESERVED)
        self.assertIn(
            "Request sent for MacBook Air. A manager will review it.",
            self.messages(response),
        )

    def test_employee_cannot_be_faked_in_the_form(self):
        self.post(self.laptop, employee=self.other.pk)
        self.assertEqual(
            EquipmentRequest.objects.get().employee, self.employee
        )

    def test_unavailable_item_cannot_be_requested(self):
        for item in (self.broken, self.laptop2):
            if item == self.laptop2:
                make_request(self.other, item)
            with self.subTest(item=item.name):
                response = self.post(item)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(
                    EquipmentRequest.objects.filter(
                        employee=self.employee
                    ).exists()
                )

    def test_one_pending_request_per_type(self):
        self.post(self.laptop)
        response = self.post(self.laptop2)
        self.assertContains(response, "already have a pending request")
        self.assertEqual(EquipmentRequest.objects.count(), 1)

    def test_different_types_can_be_requested(self):
        self.post(self.laptop)
        self.post(self.monitor)
        self.assertEqual(EquipmentRequest.objects.count(), 2)

    def test_start_date_cannot_be_in_the_past(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        response = self.post(self.laptop, start_date=yesterday.isoformat())
        self.assertContains(response, "cannot be in the past")
        self.assertIn(
            "Please correct the highlighted fields.", self.messages(response)
        )
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.IN_STOCK)

    def test_job_title_is_required(self):
        response = self.post(self.laptop, job_title="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EquipmentRequest.objects.exists())


class ReadRequestTests(TrackroomTestCase):
    """Employees see their own requests only (EST-08, EST-14)."""

    def test_list_shows_only_own_requests(self):
        make_request(self.employee, self.laptop)
        make_request(self.other, self.monitor)
        self.client.force_login(self.employee)
        response = self.client.get(reverse("request-list"))
        self.assertContains(response, "MacBook Air")
        self.assertNotContains(response, "Dell 27 monitor")

    def test_rejection_reason_is_shown(self):
        make_request(self.employee, self.laptop).reject(
            self.manager, "Please choose the Dell"
        )
        self.client.force_login(self.employee)
        response = self.client.get(reverse("request-list"))
        self.assertContains(response, "Please choose the Dell")
        self.assertContains(response, "Rejected")

    def test_my_equipment_lists_assigned_items(self):
        make_request(self.employee, self.laptop).approve(self.manager)
        make_request(self.other, self.monitor).approve(self.manager)
        self.client.force_login(self.employee)
        response = self.client.get(reverse("my-equipment"))
        self.assertContains(response, "MacBook Air")
        self.assertContains(response, "LAP-1")
        self.assertNotContains(response, "Dell 27 monitor")

    def test_dashboard_counts(self):
        make_request(self.employee, self.laptop)
        make_request(self.employee, self.monitor).approve(self.manager)
        self.client.force_login(self.employee)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["pending_total"], 1)
        self.assertEqual(response.context["held_total"], 1)
        self.assertEqual(response.context["available_total"], 1)


class UpdateRequestTests(TrackroomTestCase):
    """Employees can change a pending request (EST-09)."""

    def setUp(self):
        super().setUp()
        self.request = make_request(self.employee, self.laptop)
        self.url = reverse("request-update", args=[self.request.pk])

    def post(self, item):
        """Send the edit form."""
        return self.client.post(self.url, {
            "equipment": item.pk,
            "job_title": "Developer",
            "start_date": self.future(10),
        })

    def test_swap_item_frees_old_and_reserves_new(self):
        self.client.force_login(self.employee)
        response = self.post(self.laptop2)
        self.assertRedirects(response, reverse("request-list"))
        self.refresh(self.request, self.laptop, self.laptop2)
        self.assertEqual(self.request.equipment, self.laptop2)
        self.assertEqual(self.laptop.status, Equipment.Status.IN_STOCK)
        self.assertEqual(self.laptop2.status, Equipment.Status.RESERVED)
        self.assertIn(
            "Your request has been updated.", self.messages(response)
        )

    def test_edit_form_shows_saved_start_date(self):
        # Date pickers only read YYYY-MM-DD; a UK date left the box empty.
        self.client.force_login(self.employee)
        response = self.client.get(self.url)
        self.assertContains(
            response, f'value="{self.request.start_date.isoformat()}"'
        )

    def test_current_item_stays_selectable(self):
        self.client.force_login(self.employee)
        response = self.post(self.laptop)
        self.assertRedirects(response, reverse("request-list"))
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.RESERVED)

    def test_cannot_edit_someone_elses_request(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.post(self.laptop2).status_code, 404)

    def test_cannot_edit_after_approval(self):
        self.request.approve(self.manager)
        self.client.force_login(self.employee)
        response = self.post(self.laptop2)
        self.assertRedirects(response, reverse("request-list"))
        self.refresh(self.request)
        self.assertEqual(self.request.equipment, self.laptop)
        self.assertIn(
            "This request has already been approved and can no longer be "
            "changed.",
            self.messages(response),
        )


class DeleteRequestTests(TrackroomTestCase):
    """Employees can cancel a pending request (EST-10)."""

    def setUp(self):
        super().setUp()
        self.request = make_request(self.employee, self.laptop)
        self.url = reverse("request-delete", args=[self.request.pk])

    def test_get_shows_confirmation_without_deleting(self):
        self.client.force_login(self.employee)
        response = self.client.get(self.url)
        self.assertContains(response, "Cancel this request?")
        self.assertTrue(
            EquipmentRequest.objects.filter(pk=self.request.pk).exists()
        )

    def test_cancel_deletes_request_and_frees_item(self):
        self.client.force_login(self.employee)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("request-list"))
        self.assertFalse(EquipmentRequest.objects.exists())
        self.refresh(self.laptop)
        self.assertEqual(self.laptop.status, Equipment.Status.IN_STOCK)
        self.assertIn(
            "Your request for MacBook Air was cancelled.",
            self.messages(response),
        )

    def test_cannot_cancel_someone_elses_request(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(EquipmentRequest.objects.exists())

    def test_cannot_cancel_after_decision(self):
        self.request.reject(self.manager, "No stock budget")
        self.client.force_login(self.employee)
        self.client.post(self.url)
        self.assertTrue(EquipmentRequest.objects.exists())
