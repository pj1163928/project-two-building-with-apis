from django.contrib import admin

from .models import Pack, PackItem


class PackItemInline(admin.TabularInline):
    model = PackItem
    extra = 0
    raw_id_fields = ["saved_asset"]
    fields = ["position", "saved_asset", "preferred_variant", "import_path"]


@admin.register(Pack)
class PackAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "visibility", "updated_at"]
    list_filter = ["visibility"]
    search_fields = ["title", "slug", "owner__username"]
    readonly_fields = ["slug", "created_at", "updated_at"]
    filter_horizontal = ["tags"]
    raw_id_fields = ["copied_from"]
    inlines = [PackItemInline]
