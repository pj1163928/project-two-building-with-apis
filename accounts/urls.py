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
    # POST only: saves whichever download defaults are posted.
    path(
        "settings/downloads/",
        views.DownloadPreferencesView.as_view(),
        name="download_preferences",
    ),
    path("token/", views.TokenView.as_view(), name="token"),
    # POST only: replaces the token, so the old key stops working.
    path("token/rotate/", views.RotateTokenView.as_view(), name="rotate_token"),
    # POST only, for everyone: sets the colour scheme (system, light or dark).
    path("theme/", views.ThemeView.as_view(), name="theme"),
]
