from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import SignInForm

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=SignInForm,
            redirect_authenticated_user=True,
            extra_context={"active_nav": "account"},
        ),
        name="login",
    ),
    # LogoutView only accepts POST, so sign-out always carries a CSRF token.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("settings/", views.SettingsView.as_view(), name="settings"),
]
