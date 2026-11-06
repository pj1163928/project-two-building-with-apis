from django.contrib import admin

from .models import DownloadPreferences


@admin.register(DownloadPreferences)
class DownloadPreferencesAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "resolution",
        "texture_format",
        "hdri_format",
        "model_format",
        "sound_format",
    ]
    list_select_related = ["user"]
