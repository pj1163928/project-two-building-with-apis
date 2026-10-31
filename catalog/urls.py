from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("discover/", views.DiscoverView.as_view(), name="discover"),
    path("library/", views.LibraryView.as_view(), name="library"),
]
