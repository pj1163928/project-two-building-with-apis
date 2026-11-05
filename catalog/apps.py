from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = "catalog"

    def ready(self):
        # The providers package is plain Python; give it Django's cache so
        # lookups such as Poly Haven's /info are reused (see providers.cache).
        from django.core.cache import cache

        from providers.cache import use_cache

        use_cache(cache)
