"""Tests for registration, login and logout (user story EST-01)."""

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

PASSWORD = "Long-test-password-2026!"


def message_texts(response):
    """Return the flash messages attached to a response."""
    return [str(message) for message in get_messages(response.wsgi_request)]


class RegistrationTests(TestCase):
    """A visitor can create an employee account."""

    def form_data(self, **overrides):
        """Valid sign-up data, with optional changes."""
        data = {
            "username": "new-starter",
            "first_name": "Sam",
            "last_name": "Jones",
            "email": "sam@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_registration_creates_employee_and_logs_in(self):
        response = self.client.post(reverse("register"), self.form_data())
        user = User.objects.get(username="new-starter")
        self.assertRedirects(response, reverse("catalogue"))
        self.assertFalse(user.is_staff)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertIn(
            "Your account has been created. Choose the equipment you need.",
            message_texts(response),
        )

    def test_registration_cannot_create_a_manager(self):
        self.client.post(
            reverse("register"),
            self.form_data(is_staff="on", is_superuser="on"),
        )
        user = User.objects.get(username="new-starter")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("first", "sam@example.com", PASSWORD)
        response = self.client.post(
            reverse("register"), self.form_data(email="SAM@example.com")
        )
        self.assertContains(response, "already exists")
        self.assertFalse(User.objects.filter(username="new-starter").exists())

    def test_mismatched_passwords_create_no_account(self):
        response = self.client.post(
            reverse("register"), self.form_data(password2="different-123!")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="new-starter").exists())

    def test_logged_in_user_is_sent_to_dashboard(self):
        user = User.objects.create_user("someone", password=PASSWORD)
        self.client.force_login(user)
        response = self.client.get(reverse("register"))
        self.assertRedirects(response, reverse("home"))


class LoginLogoutTests(TestCase):
    """Users are told when they log in and out."""

    def setUp(self):
        self.user = User.objects.create_user("worker", password=PASSWORD)

    def test_login_shows_confirmation(self):
        response = self.client.post(
            reverse("login"), {"username": "worker", "password": PASSWORD}
        )
        self.assertRedirects(response, reverse("home"))
        self.assertIn("You are logged in as worker.", message_texts(response))

    def test_wrong_password_does_not_log_in(self):
        response = self.client.post(
            reverse("login"), {"username": "worker", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_shows_confirmation(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"), follow=True)
        self.assertContains(response, "You have been logged out.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_needs_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
