from django.urls import path

from . import api, attribution, views

app_name = "packs"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("packs/", views.PackListView.as_view(), name="list"),
    path("packs/new/", views.PackCreateView.as_view(), name="create"),
    # The Add to pack picker: GET the member's packs for one asset, POST to add it to one.
    path("packs/picker/", views.PickerView.as_view(), name="picker"),
    path("packs/<int:pk>/add/", views.PickerAddView.as_view(), name="picker_add"),
    # The owner's builder and its writes (POST only, each saving one change).
    path("packs/<int:pk>/edit/", views.PackBuilderView.as_view(), name="builder"),
    path("packs/<int:pk>/details/", views.PackDetailsView.as_view(), name="details"),
    path("packs/<int:pk>/visibility/", views.PackVisibilityView.as_view(), name="visibility"),
    path("packs/<int:pk>/delete/", views.PackDeleteView.as_view(), name="delete"),
    path("packs/<int:pk>/link/", views.PackRotateLinkView.as_view(), name="rotate_link"),
    path("packs/<int:pk>/library/", views.PackLibrarySearchView.as_view(), name="library_search"),
    path("packs/<int:pk>/items/", views.PackAddItemView.as_view(), name="add_item"),
    # Suggested for this pack: the list (GET, a fragment) and Add (POST `asset`).
    path("packs/<int:pk>/suggestions/", views.PackSuggestionsView.as_view(), name="suggestions"),
    path(
        "packs/<int:pk>/suggestions/add/",
        views.PackSuggestionAddView.as_view(),
        name="suggestion_add",
    ),
    path(
        "packs/<int:pk>/items/<int:item_pk>/",
        views.PackItemUpdateView.as_view(),
        name="item_update",
    ),
    path(
        "packs/<int:pk>/items/<int:item_pk>/move/",
        views.PackItemMoveView.as_view(),
        name="item_move",
    ),
    path("packs/<int:pk>/items/order/", views.PackItemsReorderView.as_view(), name="items_reorder"),
    path("packs/<int:pk>/items/sort/", views.PackItemsSortView.as_view(), name="items_sort"),
    path(
        "packs/<int:pk>/items/<int:item_pk>/remove/",
        views.PackItemRemoveView.as_view(),
        name="item_remove",
    ),
    # An unlisted pack's page and download, for anyone holding its share link.
    path("packs/link/<slug:token>/", views.PackSharedView.as_view(), name="shared"),
    path(
        "packs/link/<slug:token>/export/",
        views.PackSharedExportView.as_view(),
        name="shared_export",
    ),
    path(
        "packs/link/<slug:token>/files/", views.PackSharedFilesView.as_view(), name="shared_files"
    ),
    path(
        "packs/link/<slug:token>/attribution/",
        attribution.SharedPackAttributionView.as_view(),
        name="shared_attribution",
    ),
    # The pack's own page and its manifest download: anyone for a public pack,
    # the owner only for a private or unlisted one. Slugs are unique site-wide;
    # "new", "picker" and "link" are never given out (packs.models.RESERVED_SLUGS).
    path("packs/<slug:slug>/", views.PackPageView.as_view(), name="public"),
    path("packs/<slug:slug>/export/", views.PackExportView.as_view(), name="export"),
    # Download files: the providers' URLs for the browser's zip (?item=<id> for one item).
    path("packs/<slug:slug>/files/", views.PackFilesView.as_view(), name="files"),
    # The Attribution center: the license guide for everyone; each pack's attribution
    # (the pack page's reader rule); a member's own packs and assets.
    path("attribution/", attribution.AttributionGuideView.as_view(), name="attribution"),
    path(
        "attribution/packs/", attribution.AttributionPacksView.as_view(), name="attribution_packs"
    ),
    path(
        "attribution/packs/<slug:slug>/",
        attribution.PackAttributionView.as_view(),
        name="attribution_pack",
    ),
    path(
        "attribution/assets/",
        attribution.AttributionAssetsView.as_view(),
        name="attribution_assets",
    ),
    path(
        "attribution/assets/<int:pk>/",
        attribution.AssetAttributionView.as_view(),
        name="attribution_asset",
    ),
    # The pack API (DRF, read-only): public packs plus the caller's own.
    path("api/packs/", api.PackListAPI.as_view(), name="api_packs"),
    path("api/packs/<int:pk>/", api.PackDetailAPI.as_view(), name="api_pack"),
    path("api/packs/<int:pk>/export/", api.PackExportAPI.as_view(), name="api_pack_export"),
]
