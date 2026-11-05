from django.urls import path

from . import views

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
    path("packs/<int:pk>/library/", views.PackLibrarySearchView.as_view(), name="library_search"),
    path("packs/<int:pk>/items/", views.PackAddItemView.as_view(), name="add_item"),
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
    path(
        "packs/<int:pk>/items/<int:item_pk>/remove/",
        views.PackItemRemoveView.as_view(),
        name="item_remove",
    ),
]
