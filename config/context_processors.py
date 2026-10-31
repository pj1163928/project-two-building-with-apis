"""Template context shared by every page of the shell."""

from providers import PROVIDERS


def shell(request):
    """Provider names for the status bar."""
    return {"status_providers": [provider.NAME for provider in PROVIDERS]}
