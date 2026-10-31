from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "packs/home.html"
    extra_context = {"active_nav": "home"}


class PackListView(LoginRequiredMixin, TemplateView):
    template_name = "packs/pack_list.html"
    extra_context = {"active_nav": "packs"}
