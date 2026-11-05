from django.contrib import admin

from .models import Asset, SavedAsset, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "provider", "external_id", "license", "fetched_at"]
    list_filter = ["kind", "provider"]
    search_fields = ["title", "external_id", "author"]
    filter_horizontal = ["tags"]


@admin.register(SavedAsset)
class SavedAssetAdmin(admin.ModelAdmin):
    list_display = ["asset", "user", "status", "rating", "saved_at"]
    list_filter = ["status", "asset__kind"]
    search_fields = ["asset__title", "user__username"]
    list_select_related = ["asset", "user"]
