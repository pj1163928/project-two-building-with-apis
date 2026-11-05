"""The library API's serializers.

LibraryEntrySerializer is the owner serializer: it shows one member's entry,
their notes, rating and status included, and is only ever used on the
caller's own entries. The asset inside it is read-only. AssetSerializer
holds Asset fields only, so a public serializer (packs, Phase 8) can reuse
it without any member's private fields.
"""

from rest_framework import serializers

from .forms import NOTES_MAX_LENGTH
from .models import PROVIDER_CHOICES, Asset, SavedAsset


class AssetSerializer(serializers.ModelSerializer):
    """One shared Asset, read-only: the provider's data as the Toolbox stored it."""

    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = Asset
        fields = [
            "provider",
            "external_id",
            "kind",
            "title",
            "author",
            "thumbnail_url",
            "license",
            "license_url",
            "attribution",
            "source_url",
            "tags",
            "variants",
            "fetched_at",
        ]
        read_only_fields = fields


class LibraryEntrySerializer(serializers.ModelSerializer):
    """One of the caller's library entries: their review plus the read-only asset.

    Only notes, rating and status can change; any asset field in a request
    is ignored. The rules match the drawer's ReviewForm: notes up to
    NOTES_MAX_LENGTH characters, kept as typed (line breaks stored as LF),
    rating 1 to 5 or null, status one of the four. `community` is the
    average of every member's rating for the asset and how many rated it
    (never who), or null.
    """

    asset = AssetSerializer(read_only=True)
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=NOTES_MAX_LENGTH, trim_whitespace=False
    )
    community = serializers.SerializerMethodField()

    class Meta:
        model = SavedAsset
        fields = ["id", "asset", "notes", "rating", "status", "saved_at", "community"]
        read_only_fields = ["id", "saved_at"]

    def validate_notes(self, value: str) -> str:
        return value.replace("\r\n", "\n")

    def get_community(self, entry: SavedAsset) -> dict | None:
        community = entry.community
        return {"average": community.average, "count": community.count} if community else None

    def update(self, entry: SavedAsset, validated_data: dict) -> SavedAsset:
        # Write only the fields sent, so an API call and the drawer's notes
        # autosave never overwrite each other.
        for name, value in validated_data.items():
            setattr(entry, name, value)
        entry.save(update_fields=list(validated_data))
        return entry


class NewLibraryEntrySerializer(LibraryEntrySerializer):
    """A save through the API: the provider and its asset ID, plus an optional review.

    Everything is checked here, before any provider is called. The save
    itself (and its errors) is the view's, through save_to_library().
    """

    provider = serializers.ChoiceField(choices=PROVIDER_CHOICES, write_only=True)
    external_id = serializers.CharField(max_length=200, write_only=True)

    class Meta(LibraryEntrySerializer.Meta):
        fields = ["provider", "external_id", *LibraryEntrySerializer.Meta.fields]
