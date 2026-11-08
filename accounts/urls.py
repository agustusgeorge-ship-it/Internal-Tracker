"""Account routes. Login and logout come from django.contrib.auth.urls."""

from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
]
