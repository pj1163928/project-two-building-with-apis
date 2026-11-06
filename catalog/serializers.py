"""The library API's serializers.

LibraryEntrySerializer is the owner serializer: it shows one member's entry,
their notes, rating and status included, and is only ever used on the
caller's own entries. The asset inside it is read-only. AssetSerializer
holds Asset fields only, so a public serializer (packs, Phase 8) can reuse
it without any member's private fields.
"""

from rest_framework import serializers

from .forms import NOTES_MAX_LENGTH
from .models import (
    PROVIDER_CHOICES,
    STATUS_REASON_MAX_LENGTH,
    Asset,
    SavedAsset,
    StatusChange,
)


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
    (never who), or null. `status_change` says who set the current status,
    when, through what and why (`status_reason`, write-only, sets the why).
    """

    asset = AssetSerializer(read_only=True)
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=NOTES_MAX_LENGTH, trim_whitespace=False
    )
    community = serializers.SerializerMethodField()
    # Why the status is what it is: with a status change it goes on that change,
    # alone it explains the current status. Recorded with who sent it, via the API.
    status_reason = serializers.CharField(
        required=False, allow_blank=True, max_length=STATUS_REASON_MAX_LENGTH, write_only=True
    )
    status_change = serializers.SerializerMethodField()

    class Meta:
        model = SavedAsset
        fields = [
            "id",
            "asset",
            "notes",
            "rating",
            "status",
            "status_reason",
            "status_change",
            "saved_at",
            "community",
        ]
        read_only_fields = ["id", "saved_at"]

    def validate_notes(self, value: str) -> str:
        return value.replace("\r\n", "\n")

    def validate_status_reason(self, value: str) -> str:
        return " ".join(value.split())

    def get_community(self, entry: SavedAsset) -> dict | None:
        community = entry.community
        return {"average": community.average, "count": community.count} if community else None

    def get_status_change(self, entry: SavedAsset) -> dict | None:
        """Who set the current status, when, where and why; null when it has no record."""
        change = entry.latest_status_change
        if change is None:
            return None
        return {
            "status": change.status,
            "by": change.changed_by.get_username() if change.changed_by else None,
            "via": change.via,
            "reason": change.reason,
            "changed_at": serializers.DateTimeField().to_representation(change.changed_at),
        }

    def update(self, entry: SavedAsset, validated_data: dict) -> SavedAsset:
        # Write only the fields sent, so an API call and the drawer's notes
        # autosave never overwrite each other. A status change is recorded
        # with who made it (SavedAsset.save_review).
        by = self.context["request"].user
        reason = validated_data.pop("status_reason", None)
        for name, value in validated_data.items():
            setattr(entry, name, value)
        change = None
        if validated_data:
            change = entry.save_review(
                validated_data, by=by, via=StatusChange.Via.API, reason=reason or ""
            )
        if reason is not None and change is None:
            entry.explain_status(reason, by=by, via=StatusChange.Via.API)
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
