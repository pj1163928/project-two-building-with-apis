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
    # POST only: saves one provider asset (provider, external_id) to the member's library.
    path("library/save/", views.SaveAssetView.as_view(), name="save"),
    # POST only: removes one of the member's own entries (the shared Asset stays).
    path("library/<int:pk>/remove/", views.RemoveFromLibraryView.as_view(), name="remove"),
]
