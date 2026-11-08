"""Routes for the dashboard, employee pages and the manager area."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    # Employees
    path("catalogue/", views.CatalogueView.as_view(), name="catalogue"),
    path("requests/", views.RequestListView.as_view(), name="request-list"),
    path("requests/new/", views.RequestCreateView.as_view(),
         name="request-create"),
    path("requests/<int:pk>/edit/", views.RequestUpdateView.as_view(),
         name="request-update"),
    path("requests/<int:pk>/cancel/", views.RequestDeleteView.as_view(),
         name="request-delete"),
    path("my-equipment/", views.MyEquipmentView.as_view(),
         name="my-equipment"),
    # Managers
    path("manage/equipment/", views.StockListView.as_view(),
         name="manage-equipment-list"),
    path("manage/equipment/add/", views.StockCreateView.as_view(),
         name="manage-equipment-create"),
    path("manage/equipment/<int:pk>/", views.StockDetailView.as_view(),
         name="manage-equipment-detail"),
    path("manage/equipment/<int:pk>/edit/", views.StockUpdateView.as_view(),
         name="manage-equipment-update"),
    path("manage/equipment/<int:pk>/delete/",
         views.StockDeleteView.as_view(), name="manage-equipment-delete"),
    path("manage/equipment/<int:pk>/handback/",
         views.HandbackCreateView.as_view(), name="manage-handback"),
    path("manage/requests/", views.ManagerRequestListView.as_view(),
         name="manage-request-list"),
    path("manage/requests/<int:pk>/", views.RequestReviewView.as_view(),
         name="manage-request-review"),
    path("manage/people/", views.PeopleView.as_view(), name="manage-people"),
]
