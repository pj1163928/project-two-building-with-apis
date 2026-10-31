"""The real URLs plus a stand-in accounts:password_reset.

Password recovery is out of scope (PRD), so it doesn't exist yet. The sign-in
page shows "Forgot password?" only once that URL exists; tests switch to this
URLconf with @pytest.mark.urls to prove the link appears when it does.
"""

from django.http import HttpResponse
from django.urls import include, path

from accounts import urls as accounts_urls
from config.urls import urlpatterns as real_urlpatterns

accounts_patterns = [
    *accounts_urls.urlpatterns,
    path("password-reset/", lambda request: HttpResponse("reset"), name="password_reset"),
]

urlpatterns = [
    path("accounts/", include((accounts_patterns, "accounts"))),
    *[p for p in real_urlpatterns if getattr(p, "namespace", None) != "accounts"],
]
