from django.urls import path

from . import views

app_name = "packs"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("packs/", views.PackListView.as_view(), name="list"),
]
