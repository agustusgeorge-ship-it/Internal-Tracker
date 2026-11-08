"""Tell users when they have logged in or out (Code Institute checklist)."""

from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver


@receiver(user_logged_in)
def announce_login(sender, request, user, **kwargs):
    """Show a confirmation message after every successful login.

    fail_silently covers logins with no message system, such as the
    test client's force_login.
    """
    if request is not None:
        messages.success(
            request,
            f"You are logged in as {user.username}.",
            fail_silently=True,
        )


@receiver(user_logged_out)
def announce_logout(sender, request, user, **kwargs):
    """Show a confirmation message after logging out."""
    if request is not None:
        messages.info(
            request, "You have been logged out.", fail_silently=True
        )
