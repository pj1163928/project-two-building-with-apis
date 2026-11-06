from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render, resolve_url
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import CreateView, TemplateView
from django_htmx.http import HttpResponseClientRedirect
from rest_framework.authtoken.models import Token

from .forms import DownloadPreferencesForm, SignUpForm
from .models import DownloadPreferences, preference_groups
from .theme import COOKIE_MAX_AGE, COOKIE_NAME, THEME_CHOICES, THEME_LABELS, theme_choice


class SignUpView(CreateView):
    """Create an account, sign the new member in, and honour `next`."""

    form_class = SignUpForm
    template_name = "accounts/signup.html"
    extra_context = {"active_nav": "account"}

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(self.get_success_url())

    def get_success_url(self):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url
        return resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next"] = self.request.GET.get("next", "")
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    extra_context = {"active_nav": "account"}


class SettingsView(LoginRequiredMixin, TemplateView):
    """The member's settings: the theme, and their download defaults."""

    template_name = "accounts/settings.html"
    extra_context = {"active_nav": "settings"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["theme_choices"] = THEME_CHOICES
        context["theme_choice"] = theme_choice(self.request)
        context["preferences"] = DownloadPreferences.objects.for_user(self.request.user)
        context["preference_groups"] = preference_groups(context["preferences"])
        return context


class DownloadPreferencesView(LoginRequiredMixin, View):
    """Save whichever download defaults were posted (DownloadPreferencesForm).

    Members only, with CSRF. The Settings page's HTMX request gets the status
    line: "Saved", or a 400 with the first problem and nothing saved. A plain
    POST is sent back to the Settings page.
    """

    http_method_names = ["post"]
    template_name = "accounts/partials/settings_save_status.html"

    def handle_no_permission(self):
        login = redirect_to_login(reverse("accounts:settings"))
        return HttpResponseClientRedirect(login.url) if self.request.htmx else login

    def post(self, request):
        preferences = DownloadPreferences.objects.for_user(request.user)
        form = DownloadPreferencesForm(request.POST, instance=preferences)
        if not form.changed_fields:
            return self.reply(400, "There was nothing to save.")
        if not form.is_valid():
            return self.reply(400, form.first_error)
        form.save()
        if not request.htmx or request.htmx.boosted:
            return redirect("accounts:settings")
        return self.reply(200)

    def reply(self, status: int, message: str = ""):
        context = {"state": "error" if message else "saved", "message": message}
        return render(self.request, self.template_name, context, status=status)


@method_decorator(never_cache, name="dispatch")
class TokenView(LoginRequiredMixin, TemplateView):
    """The member's API token, created on their first visit.

    The token signs API requests (`Authorization: Token <key>`) without a
    CSRF token. The page is never cached, so the key isn't kept by the browser.
    """

    template_name = "accounts/token.html"
    extra_context = {"active_nav": "account"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["token"], _created = Token.objects.get_or_create(user=self.request.user)
        context["api_url"] = self.request.build_absolute_uri(reverse("catalog:api_library"))
        return context


class ThemeView(View):
    """Set the colour scheme: POST `choice` ("system", "light" or "dark"), with CSRF.

    Open to everyone, signed in or not. It stores the choice in the ax-theme
    cookie for a year. An HTMX request gets a 204 (the page has already
    switched itself); any other is sent back to the page it came from (`next`,
    else the Referer) when that's on this site, otherwise to the home page.
    An unknown choice is a 400.
    """

    http_method_names = ["post"]

    def post(self, request):
        choice = request.POST.get("choice", "")
        if choice not in THEME_LABELS:
            return HttpResponseBadRequest("Choose system, light or dark.")
        if request.htmx and not request.htmx.boosted:
            response = HttpResponse(status=204)
        else:
            next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
            safe = url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            )
            response = redirect(next_url if safe else "packs:home")
        response.set_cookie(COOKIE_NAME, choice, max_age=COOKIE_MAX_AGE, samesite="Lax")
        return response
