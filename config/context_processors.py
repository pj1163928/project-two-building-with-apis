"""Template context shared by every page of the shell."""

from catalog.discover import provider_statuses


def shell(request):
    """Each provider's last known status, for the status bar."""
    return {"status_providers": provider_statuses()}
