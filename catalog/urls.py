from django.urls import path

from . import api, views

app_name = "catalog"

urlpatterns = [
    path("discover/", views.DiscoverView.as_view(), name="discover"),
    # One provider's shelf for one kind, e.g. /discover/texture/polyhaven/?q=brick
    path(
        "discover/<slug:kind>/<slug:provider>/",
        views.DiscoverShelfView.as_view(),
        name="discover_shelf",
    ),
    # One result in full: Discover's drawer for HTMX, a page otherwise. Nothing is saved.
    path(
        "discover/asset/<slug:provider>/<path:external_id>/",
        views.DiscoverAssetView.as_view(),
        name="discover_asset",
    ),
    path("library/", views.LibraryView.as_view(), name="library"),
    # POST only: saves one provider asset (provider, external_id) to the member's library.
    path("library/save/", views.SaveAssetView.as_view(), name="save"),
    # One of the member's entries: the drawer for HTMX, a full page otherwise.
    path("library/<int:pk>/", views.EntryView.as_view(), name="entry"),
    # POST only: saves whichever of status, rating and notes is posted.
    path("library/<int:pk>/update/", views.UpdateEntryView.as_view(), name="update"),
    # POST only: removes one of the member's own entries (the shared Asset stays).
    path("library/<int:pk>/remove/", views.RemoveFromLibraryView.as_view(), name="remove"),
    # The library API (DRF): list and create, then read, update and delete one entry.
    path("api/library/", api.LibraryAPI.as_view(), name="api_library"),
    path("api/library/<int:pk>/", api.LibraryEntryAPI.as_view(), name="api_entry"),
]
