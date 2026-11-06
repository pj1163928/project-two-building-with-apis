"""Packs: a member's kits of saved assets for one project.

A Pack belongs to one member and holds PackItems, each pointing at one of
that member's own SavedAssets. The variant and import path live on the
PackItem, so the same asset can differ from pack to pack, and nothing
private on the SavedAsset (notes, rating, status) is part of a pack.

A pack is private (its owner only), unlisted (anyone holding its share
link, /packs/link/<token>/) or public (anyone, at /packs/<slug>/).
"""

import re
import secrets
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
# Words under /packs/ that are pages, not packs: a pack titled "New" gets "new-2".
RESERVED_SLUGS = frozenset({"new", "picker", "link"})
# Bytes of randomness in an unlisted pack's share link (secrets.token_urlsafe):
# 16 bytes is 128 bits, 22 URL-safe characters, never guessable.
SHARE_TOKEN_BYTES = 16
SHARE_TOKEN_MAX_LENGTH = 64

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


def new_share_token() -> str:
    """A fresh, unguessable share-link token (128 bits, URL-safe)."""
    return secrets.token_urlsafe(SHARE_TOKEN_BYTES)


class PackQuerySet(models.QuerySet):
    def owned_by(self, user) -> "PackQuerySet":
        """Only `user`'s packs; none at all for a signed-out visitor."""
        return self.filter(owner=user) if user.is_authenticated else self.none()

    def public(self) -> "PackQuerySet":
        """Public packs only: never a private or unlisted one."""
        return self.filter(visibility=Pack.Visibility.PUBLIC)

    def visible_to(self, user) -> "PackQuerySet":
        """Packs `user` may read by slug or id: every public pack plus their own,
        private and unlisted ones included. A signed-out visitor gets public
        packs only. The pack page, the pack API and both exports read packs
        through this, so anything else is a 404. Anyone else reads an unlisted
        pack only through its share link (shared_by_link())."""
        public = models.Q(visibility=Pack.Visibility.PUBLIC)
        if user.is_authenticated:
            return self.filter(public | models.Q(owner=user))
        return self.filter(public)

    def shared_by_link(self, token: str) -> "PackQuerySet":
        """The pack whose share link carries `token`, while it's unlisted or public.

        A private pack's link never opens it, and an old token (one the owner
        replaced) matches nothing.
        """
        if not token:
            return self.none()
        return self.filter(share_token=token).exclude(visibility=Pack.Visibility.PRIVATE)

    def with_item_count(self) -> "PackQuerySet":
        return self.annotate(item_count=models.Count("items", distinct=True))

    def public_featuring(self, asset, *, exclude_owner=None) -> "PackQuerySet":
        """Public packs holding `asset` (through anyone's entry), A–Z, with their
        owners and item counts. Private and unlisted packs are never included."""
        holding = PackItem.objects.filter(saved_asset__asset=asset).values("pack")
        packs = self.public().filter(pk__in=holding)
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
        taken |= RESERVED_SLUGS
        slug, number = base, 1
        while slug in taken:
            number += 1
            slug = f"{base}-{number}"
        return slug


class Pack(models.Model):
    """One member's kit of saved assets for a project. Private until the owner
    makes it unlisted (shared by link) or public."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        UNLISTED = "unlisted", "Unlisted"
        PUBLIC = "public", "Public"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="packs"
    )
    title = models.CharField(max_length=TITLE_MAX_LENGTH)
    # Set once when the pack is made, so its links never change on a rename.
    slug = models.SlugField(max_length=SLUG_MAX_LENGTH, unique=True)
    description = models.TextField("intended use", max_length=DESCRIPTION_MAX_LENGTH, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="packs")
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE, db_index=True
    )
    # The secret in an unlisted pack's share link. Made the first time the pack
    # is unlisted, kept through later visibility changes, and replaced only by
    # rotate_share_token(), which makes every older link a 404.
    share_token = models.CharField(
        max_length=SHARE_TOKEN_MAX_LENGTH, unique=True, null=True, blank=True, editable=False
    )
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

    def get_public_url(self) -> str:
        """The pack's page, /packs/<slug>/: for anyone when public, the owner otherwise."""
        return reverse("packs:public", args=[self.slug])

    def get_share_url(self) -> str:
        """The share link, /packs/link/<token>/, or "" when the pack has none yet."""
        return reverse("packs:shared", args=[self.share_token]) if self.share_token else ""

    @property
    def reader_url(self) -> str:
        """The address readers use: the share link while unlisted, else the slug page.

        The manifest's source_url and the API's page_url use it.
        """
        if self.is_unlisted and self.share_token:
            return self.get_share_url()
        return self.get_public_url()

    @property
    def is_public(self) -> bool:
        return self.visibility == self.Visibility.PUBLIC

    @property
    def is_unlisted(self) -> bool:
        return self.visibility == self.Visibility.UNLISTED

    def set_visibility(self, visibility: str) -> None:
        """Save the pack as private, unlisted or public.

        Unlisting it the first time makes its share link. The link is kept
        when the pack goes private or public, so unlisting it again brings
        the same link back; rotate_share_token() is how an owner retires it.
        """
        if visibility not in self.Visibility.values:
            raise ValueError(f"Unknown visibility: {visibility!r}")
        self.visibility = visibility
        fields = ["visibility", "updated_at"]
        if visibility == self.Visibility.UNLISTED and not self.share_token:
            self.share_token = new_share_token()
            fields.append("share_token")
        self.save(update_fields=fields)

    def rotate_share_token(self) -> str:
        """Replace the share link with a new one and return its token.

        Every older link stops working at once (a 404). The pack's visibility
        doesn't change.
        """
        self.share_token = new_share_token()
        self.save(update_fields=["share_token", "updated_at"])
        return self.share_token

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

    @property
    def variant_options(self) -> list[dict[str, Any]]:
        """The variant dropdown's choices: each label with its file count and total size."""
        return [
            {
                "label": str(variant.get("label", "")),
                "count": len(variant.get("files") or []),
                "size": variant.get("total_size"),
            }
            for variant in self.asset.variants
        ]
