from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("discover/", views.DiscoverView.as_view(), name="discover"),
    # One provider's shelf for one kind, e.g. /discover/texture/polyhaven/?q=brick
    path(
        "discover/<slug:kind>/<slug:provider>/",
        views.DiscoverShelfView.as_view(),
        name="discover_shelf",
    ),
    path("library/", views.LibraryView.as_view(), name="library"),
]
