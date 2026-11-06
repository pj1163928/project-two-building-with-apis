"""Template context shared by every page of the shell."""

from accounts.theme import THEME_LABELS, next_theme, theme_choice
from catalog.discover import provider_statuses
from catalog.models import SavedAsset


def shell(request):
    """Each provider's last known status, and a member's own saved count, for the status bar,
    and the chosen colour scheme, for <html> and the title bar's switch.

    The count is the signed-in member's entries only; a visitor gets none.
    """
    choice = theme_choice(request)
    context = {
        "status_providers": provider_statuses(),
        "theme_choice": choice,
        "theme_label": THEME_LABELS[choice],
        "theme_next": next_theme(choice),
        "theme_next_label": THEME_LABELS[next_theme(choice)],
    }
    if request.user.is_authenticated:
        context["saved_count"] = SavedAsset.objects.for_user(request.user).count()
    return context
