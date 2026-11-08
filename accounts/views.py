"""Account views: registration (login and logout use Django's own views)."""

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import RegistrationForm


class RegisterView(FormView):
    """Create an employee account, log it in and open the catalogue."""

    template_name = "accounts/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("catalogue")

    def dispatch(self, request, *args, **kwargs):
        """Send users who are already logged in to their dashboard."""
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Save the user, log them in and confirm the new account."""
        user = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            "Your account has been created. Choose the equipment you need.",
        )
        return super().form_valid(form)
