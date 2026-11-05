"""Template context shared by every page of the shell."""

from catalog.discover import provider_statuses
from catalog.models import SavedAsset


def shell(request):
    """Each provider's last known status, and a member's own saved count, for the status bar.

    The count is the signed-in member's entries only; a visitor gets none.
    """
    context = {"status_providers": provider_statuses()}
    if request.user.is_authenticated:
        context["saved_count"] = SavedAsset.objects.for_user(request.user).count()
    return context
