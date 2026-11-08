"""Top-level URL routes: admin, Django's login/logout, and the two apps."""

from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.utils.functional import lazy
from django.views.generic import RedirectView

# Look up the hashed file name only when the icon is requested, so starting
# the site never depends on collectstatic having run.
static_lazy = lazy(static, str)

admin.site.site_header = "Trackroom administration"
admin.site.site_title = "Trackroom admin"
admin.site.index_title = "Equipment, requests and handbacks"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Browsers ask for /favicon.ico even when the page links an SVG icon.
    path("favicon.ico", RedirectView.as_view(
        url=static_lazy("images/favicon.svg"), permanent=True)),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("equipment.urls")),
]
