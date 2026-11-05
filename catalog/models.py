"""The catalog's records: shared Assets and Tags, and each member's SavedAssets.

An Asset is the Toolbox's own copy of one provider asset, shared by every
member, so the library still works when the provider is down. A SavedAsset
is one member's entry for an Asset, holding their private notes, rating and
status.
"""

from collections.abc import Iterable

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone

from providers import KINDS, PROVIDERS, AssetRecord

from .discover import TILES_BY_KIND, KindTile
from .tags import MAX_TAG_LENGTH, normalize_tag

PROVIDER_CHOICES = [(provider.KEY, provider.NAME) for provider in PROVIDERS]
# One asset's type, so singular (the Discover tiles' labels are plural).
KIND_LABELS = {"texture": "Texture", "hdri": "HDRI", "model": "Model", "sound": "Sound"}
KIND_CHOICES = [(kind, KIND_LABELS[kind]) for kind in KINDS]


class TagManager(models.Manager):
    def from_names(self, names: Iterable[str]) -> list["Tag"]:
        """The Tags for `names`, normalized and de-duplicated, created as needed.

        Names that normalize to nothing are dropped. The rest keep the order
        they were first seen in.
        """
        normalized = dict.fromkeys(
            tag for tag in (normalize_tag(name) for name in names if isinstance(name, str)) if tag
        )
        return [self.get_or_create(name=name)[0] for name in normalized]


class Tag(models.Model):
    """A normalized tag name (see catalog.tags.normalize_tag), unique site-wide."""

    name = models.CharField(max_length=MAX_TAG_LENGTH, unique=True)

    objects = TagManager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AssetManager(models.Manager):
    def from_record(self, record: AssetRecord) -> "Asset":
        """Store a fetched record as the shared Asset, or return the one already stored.

        A stored Asset is never overwritten: the first save by anyone sets it.
        Its tags go through normalize_tag().
        """
        with transaction.atomic():
            asset, created = self.get_or_create(
                provider=record.provider,
                external_id=record.external_id,
                defaults={
                    "kind": record.kind,
                    "title": record.title[:300],
                    "author": record.author[:300],
                    "thumbnail_url": record.thumbnail_url,
                    "license": record.license[:100],
                    "license_url": record.license_url,
                    "attribution": record.attribution,
                    "source_url": record.source_url,
                    "variants": [variant.as_dict() for variant in record.variants],
                },
            )
            if created:
                asset.tags.set(Tag.objects.from_names(record.tags))
        return asset


class Asset(models.Model):
    """One provider asset as the Toolbox stored it when it was first saved.

    Shared by every member and never deleted by them. Thumbnails and files
    are the provider's URLs: the Toolbox links to them, never copies them.
    `variants` is a list of {"label", "files": [{"url", "filename", "size"}],
    "total_size"}, as providers.records.Variant.as_dict() writes it.
    """

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    external_id = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    title = models.CharField(max_length=300)
    author = models.CharField(max_length=300, blank=True)
    thumbnail_url = models.URLField(max_length=1000, blank=True)
    license = models.CharField(max_length=100)
    license_url = models.URLField(max_length=500, blank=True)
    attribution = models.TextField(blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    variants = models.JSONField(default=list, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="assets")
    fetched_at = models.DateTimeField(default=timezone.now)

    objects = AssetManager()

    class Meta:
        ordering = ["title", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"], name="unique_asset_per_provider_id"
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.get_provider_display()})"

    @property
    def tile(self) -> KindTile:
        """The asset's type tile: its label, icon and type colour."""
        return TILES_BY_KIND[self.kind]


# The library's sorts, by their URL value; "newest" is the default. Each ends
# on a unique column, so the order never shifts between pages.
LIBRARY_SORTS = {
    "newest": ("-saved_at", "-id"),
    "oldest": ("saved_at", "id"),
    "title": (Lower("asset__title"), "-saved_at", "-id"),
    "rating": (F("rating").desc(nulls_last=True), "-saved_at", "-id"),
}


class SavedAssetQuerySet(models.QuerySet):
    def for_user(self, user) -> "SavedAssetQuerySet":
        """Only `user`'s entries; none at all for a signed-out visitor."""
        return self.filter(user=user) if user.is_authenticated else self.none()

    def saved_external_ids(self, user, provider_key: str, external_ids: Iterable[str]) -> set[str]:
        """Which of `external_ids` from one provider `user` already has in their library."""
        return set(
            self.for_user(user)
            .filter(asset__provider=provider_key, asset__external_id__in=list(external_ids))
            .values_list("asset__external_id", flat=True)
        )

    def search(self, text: str) -> "SavedAssetQuerySet":
        """Entries matching every word of `text` in the title, a tag or the notes.

        Case is ignored. Each word is tidied like a tag before matching tags,
        so "bricks" finds the tag "brick".
        """
        entries = self
        for word in text.split():
            tagged = Asset.objects.filter(tags__name__icontains=normalize_tag(word) or word)
            entries = entries.filter(
                Q(asset__title__icontains=word) | Q(notes__icontains=word) | Q(asset__in=tagged)
            )
        return entries

    def sorted_by(self, sort: str) -> "SavedAssetQuerySet":
        """Entries in one of LIBRARY_SORTS' orders. Unrated entries sort last by rating."""
        return self.order_by(*LIBRARY_SORTS[sort])


class SavedAsset(models.Model):
    """One member's library entry for a shared Asset, with their private notes,
    rating and status. Deleting it never deletes the Asset."""

    class Status(models.TextChoices):
        TO_REVIEW = "to_review", "To review"
        TESTING = "testing", "Testing"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_assets"
    )
    # PROTECT: a shared Asset can't be deleted out from under anyone's library.
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="saves")
    notes = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.TO_REVIEW)
    saved_at = models.DateTimeField(default=timezone.now)

    objects = SavedAssetQuerySet.as_manager()

    class Meta:
        ordering = ["-saved_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "asset"], name="unique_saved_asset_per_user"),
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True) | models.Q(rating__gte=1, rating__lte=5),
                name="saved_asset_rating_1_to_5",
            ),
        ]

    def __str__(self):
        return f"{self.user} · {self.asset.title}"

    @property
    def stars(self) -> list[bool]:
        """Five flags, one per star, True for each the rating fills (all False if unrated)."""
        return [star <= (self.rating or 0) for star in range(1, 6)]
