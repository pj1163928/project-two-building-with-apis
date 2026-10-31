from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DiscoverView(TemplateView):
    """Discover is open to signed-out visitors."""

    template_name = "catalog/discover.html"
    extra_context = {"active_nav": "discover"}


class LibraryView(LoginRequiredMixin, TemplateView):
    template_name = "catalog/library.html"
    extra_context = {"active_nav": "library"}
