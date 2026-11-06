"""Packs: a member's kits of saved assets for one project.

A Pack belongs to one member and holds PackItems, each pointing at one of
that member's own SavedAssets. The variant and import path live on the
PackItem, so the same asset can differ from pack to pack, and nothing
private on the SavedAsset (notes, rating, status) is part of a pack.
"""

import re
from collections.abc import Iterable, Mapping
from typing import Any

from django.conf import settings
from django.db import models, transaction
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils.text import slugify

from catalog.models import SavedAsset, Tag

TITLE_MAX_LENGTH = 120
DESCRIPTION_MAX_LENGTH = 2000
IMPORT_PATH_MAX_LENGTH = 300
SLUG_MAX_LENGTH = 140

# The variant a new item starts on, by kind, when the asset has one; otherwise
# the first listed. Labels are compared by squeeze_label(), so ambientCG's
# "2K-JPG" and Poly Haven's "2K JPG" both count.
PREFERRED_VARIANTS = {"sound": "mp3"}
PREFERRED_VARIANT_DEFAULT = "2k jpg"


def squeeze_label(label: str) -> str:
    """A variant label in a form that ignores case, hyphens and extra spaces."""
    return " ".join(label.replace("-", " ").lower().split())


def default_variant(kind: str, variants: Iterable[Mapping[str, Any]]) -> str:
    """The label of the variant a new pack item starts on.

    A 2K JPG (an MP3 for sounds) when the asset has one, otherwise the first
    listed variant, or "" for an asset with no variants.
    """
    labels = [str(variant.get("label", "")) for variant in variants]
    wanted = PREFERRED_VARIANTS.get(kind, PREFERRED_VARIANT_DEFAULT)
    for label in labels:
        if squeeze_label(label) == wanted:
            return label
    return labels[0] if labels else ""


def tags_from_text(text: str) -> list[Tag]:
    """The Tags typed as comma-separated text, through normalize_tag(), once each."""
    return Tag.objects.from_names(text.split(","))


class PackQuerySet(models.QuerySet):
    def owned_by(self, user) -> "PackQuerySet":
        """Only `user`'s packs; none at all for a signed-out visitor."""
        return self.filter(owner=user) if user.is_authenticated else self.none()

    def with_item_count(self) -> "PackQuerySet":
        return self.annotate(item_count=models.Count("items", distinct=True))

    def public_featuring(self, asset, *, exclude_owner=None) -> "PackQuerySet":
        """Public packs holding `asset` (through anyone's entry), A–Z, with their
        owners and item counts. Private packs are never included."""
        holding = PackItem.objects.filter(saved_asset__asset=asset).values("pack")
        packs = self.filter(is_public=True, pk__in=holding)
        if exclude_owner is not None and exclude_owner.is_authenticated:
            packs = packs.exclude(owner=exclude_owner)
        return packs.select_related("owner").with_item_count().order_by(Lower("title"), "id")


class PackManager(models.Manager.from_queryset(PackQuerySet)):
    def create_pack(self, owner, title: str, description: str = "", tags: str = "") -> "Pack":
        """Create a private pack with a site-wide unique slug and its tidied tags.

        The slug, the pack and its tags are written in one transaction, so a
        failure leaves no half-made pack behind.
        """
        with transaction.atomic():
            pack = self.create(
                owner=owner,
                title=title,
                description=description,
                slug=self.free_slug(title),
            )
            pack.tags.set(tags_from_text(tags))
        return pack

    def free_slug(self, title: str) -> str:
        """A slug for `title` that no pack uses yet: the slugified title, then -2, -3…"""
        base = slugify(title)[: SLUG_MAX_LENGTH - 8].strip("-") or "pack"
        taken = set(
            self.filter(slug__regex=rf"^{re.escape(base)}(-[0-9]+)?$").values_list(
                "slug", flat=True
            )
        )
        slug, number = base, 1
        while slug in taken:
            number += 1
            slug = f"{base}-{number}"
        return slug


class Pack(models.Model):
    """One member's kit of saved assets for a project. Private until made public."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="packs"
    )
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    # Set once when the pack is made, so its links never change on a rename.
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH, unique=True)
    description = models.TextField("intended use", max_length=DESCRIPTION_MAX_LENGTH, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="packs")
    is_public = models.BooleanField(default=False)
    copied_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="copies"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PackManager()

    class Meta:
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("packs:builder", args=[self.pk])

    @property
    def tags_text(self) -> str:
        """The pack's tags as the comma-separated text the owner edits."""
        return ", ".join(tag.name for tag in self.tags.all())

    def ordered_items(self) -> models.QuerySet["PackItem"]:
        """The pack's items in position order, with their entries and Assets."""
        return self.items.select_related("saved_asset__asset").order_by("position", "id")


class PackItem(models.Model):
    """One of the owner's SavedAssets in a pack, with this pack's variant and import path.

    Deleting the SavedAsset (or the pack) deletes the item; the Asset stays.
    """

    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="items")
    saved_asset = models.ForeignKey(SavedAsset, on_delete=models.CASCADE, related_name="pack_items")
    preferred_variant = models.CharField(max_length=100, blank=True)
    import_path = models.CharField(max_length=IMPORT_PATH_MAX_LENGTH, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["pack", "saved_asset"], name="unique_item_per_pack")
        ]

    def __str__(self):
        return f"{self.pack} · {self.saved_asset.asset.title}"

    @property
    def asset(self):
        return self.saved_asset.asset

    @property
    def default_import_path(self) -> str:
        """Where the engine puts the files when the owner leaves the path blank."""
        return f"{self.asset.kind}s/{self.asset.external_id}/"

    @property
    def variant_labels(self) -> list[str]:
        return [str(variant.get("label", "")) for variant in self.asset.variants]
