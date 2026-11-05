"""An optional cache for provider lookups, installed by the Toolbox.

The providers package is plain Python: the console script uses it with no
Django and no cache, so nothing here imports Django. The Toolbox installs
Django's cache at startup (catalog.apps), and from then on remember()
reuses successful answers. A lookup that raises is never stored.
"""

from collections.abc import Callable
from typing import Any, Protocol


class CacheBackend(Protocol):
    """The part of Django's cache API that remember() needs."""

    def get(self, key: str, default: Any = None) -> Any: ...

    def set(self, key: str, value: Any, timeout: float | None = None) -> None: ...


_backend: CacheBackend | None = None
_MISSING = object()


def use_cache(backend: CacheBackend | None) -> None:
    """Install the cache remember() uses, or None to turn caching off."""
    global _backend
    _backend = backend


def remember[T](key: str, seconds: int, fetch: Callable[[], T]) -> T:
    """Return the cached value for `key`, or call `fetch()` and cache its answer.

    With no cache installed, this just calls `fetch()`. If `fetch()` raises,
    nothing is stored and the exception propagates.
    """
    if _backend is None:
        return fetch()
    value = _backend.get(key, _MISSING)
    if value is _MISSING:
        value = fetch()
        _backend.set(key, value, seconds)
    return value
