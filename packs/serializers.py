"""The pack API's public serializers.

They carry only Pack, PackItem and Asset fields (the Asset through
catalog.serializers.AssetSerializer), never a member's library entry, so a
pack can't leak its owner's notes, ratings or statuses, nor anyone's
community rating.
"""

from django.urls import reverse
from rest_framework import serializers

from catalog.serializers import AssetSerializer

from .models import Pack, PackItem


class PackItemSerializer(serializers.ModelSerializer):
    """One item: this pack's variant and import path, and the stored Asset."""

    asset = AssetSerializer(source="saved_asset.asset", read_only=True)
    default_import_path = serializers.CharField(read_only=True)

    class Meta:
        model = PackItem
        fields = [
            "id",
            "position",
            "preferred_variant",
            "import_path",
            "default_import_path",
            "asset",
        ]
        read_only_fields = fields


class PackSerializer(serializers.ModelSerializer):
    """A pack in the list: its details and where to read, see and export it."""

    author = serializers.CharField(source="owner.get_username", read_only=True)
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    item_count = serializers.IntegerField(read_only=True)
    url = serializers.SerializerMethodField()
    export_url = serializers.SerializerMethodField()
    page_url = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = [
            "id",
            "slug",
            "title",
            "author",
            "description",
            "tags",
            "visibility",
            "item_count",
            "created_at",
            "updated_at",
            "url",
            "export_url",
            "page_url",
        ]
        read_only_fields = fields

    def _absolute(self, path: str) -> str:
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path

    def get_url(self, pack: Pack) -> str:
        return self._absolute(reverse("packs:api_pack", args=[pack.pk]))

    def get_export_url(self, pack: Pack) -> str:
        return self._absolute(reverse("packs:api_pack_export", args=[pack.pk]))

    def get_page_url(self, pack: Pack) -> str:
        # The share link for an unlisted pack, which only its owner can list.
        return self._absolute(pack.reader_url)


class PackDetailSerializer(PackSerializer):
    """One pack read in full: the list's fields plus its items in position order."""

    items = PackItemSerializer(source="ordered_items", many=True, read_only=True)

    class Meta(PackSerializer.Meta):
        fields = [*PackSerializer.Meta.fields, "items"]
        read_only_fields = fields
