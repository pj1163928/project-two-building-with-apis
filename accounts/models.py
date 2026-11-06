"""A member's own settings."""

from dataclasses import dataclass

from django.conf import settings
from django.db import models

from catalog.files import (
    HDRI_FORMATS,
    MAP_CHOICES,
    MAP_KEYS,
    MODEL_FORMATS,
    RESOLUTION_CHOICES,
    SOUND_FORMATS,
    TEXTURE_FORMATS,
)


def every_map() -> list[str]:
    """The default map list: every map type."""
    return list(MAP_KEYS)


class DownloadPreferencesManager(models.Manager):
    def for_user(self, user) -> "DownloadPreferences":
        """`user`'s download defaults: their saved row, or the defaults, unsaved.

        Reading never writes, so a member has a row only once they change a
        setting.
        """
        if user.is_authenticated:
            saved = self.filter(user=user).first()
            if saved:
                return saved
            return self.model(user=user)
        return self.model()


class DownloadPreferences(models.Model):
    """Which files a member wants by default: the resolution, a format per
    kind, and the texture maps. "Download bundle" in the library drawer
    follows them (catalog.files.pick_bundle)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="download_preferences"
    )
    resolution = models.CharField(max_length=4, choices=RESOLUTION_CHOICES, default="2K")
    texture_format = models.CharField(max_length=8, choices=TEXTURE_FORMATS, default="jpg")
    hdri_format = models.CharField("HDRI format", max_length=8, choices=HDRI_FORMATS, default="hdr")
    model_format = models.CharField(max_length=8, choices=MODEL_FORMATS, default="gltf")
    sound_format = models.CharField(max_length=8, choices=SOUND_FORMATS, default="mp3")
    # Map type keys (catalog.files.MAP_KEYS) to take from loose texture maps.
    maps = models.JSONField(default=every_map)

    objects = DownloadPreferencesManager()

    class Meta:
        verbose_name_plural = "download preferences"

    def __str__(self):
        return f"{self.user} · download defaults"

    def format_for(self, kind: str) -> str:
        """The member's format key for one kind of asset."""
        return {
            "texture": self.texture_format,
            "hdri": self.hdri_format,
            "model": self.model_format,
            "sound": self.sound_format,
        }.get(kind, "")

    @property
    def summary(self) -> str:
        """The defaults in a few words, e.g. "2K · JPG · every map"."""
        maps = (
            "every map"
            if set(self.maps) >= set(MAP_KEYS)
            else f"{len(self.maps)} map{'s' if len(self.maps) != 1 else ''}"
        )
        return f"{self.resolution} · {self.get_texture_format_display()} · {maps}"


@dataclass(frozen=True)
class PreferenceGroup:
    """One group of the Settings page's download chips: radios, or checkboxes
    for the maps."""

    name: str
    title: str
    hint: str
    multiple: bool
    chips: list[tuple[str, str, bool]]  # (value, label, checked)


def preference_groups(preferences: DownloadPreferences) -> list[PreferenceGroup]:
    """The Settings page's download chips, each checked to match `preferences`."""

    def radios(name, title, hint):
        field = DownloadPreferences._meta.get_field(name)
        current = getattr(preferences, name)
        chips = [(value, label, value == current) for value, label in field.choices]
        return PreferenceGroup(name, title, hint, False, chips)

    chosen_maps = set(preferences.maps)
    return [
        radios("resolution", "Resolution", "Or the nearest below it, when there's no exact match."),
        radios("texture_format", "Texture format", "For loose texture maps."),
        radios("hdri_format", "HDRI format", "For HDRI environment maps."),
        radios("model_format", "Model format", "Models come as a bundle with their textures."),
        radios("sound_format", "Sound format", "When a sound comes in more than one."),
        PreferenceGroup(
            "maps",
            "Texture maps",
            "Only these maps go into a bundle of loose texture maps.",
            True,
            [(key, label, key in chosen_maps) for key, label in MAP_CHOICES],
        ),
    ]
