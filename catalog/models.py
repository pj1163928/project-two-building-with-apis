"""The catalog's records: shared Assets and Tags, and each member's SavedAssets.

An Asset is the Toolbox's own copy of one provider asset, shared by every
member, so the library still works when the provider is down. A SavedAsset
is one member's entry for an Asset, holding their private notes, rating and
status.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Avg, Case, Count, F, IntegerField, OuterRef, Q, Subquery, When
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone
from django.utils.functional import cached_property

from providers import KINDS, PROVIDERS, AssetRecord

from .discover import TILES_BY_KIND, KindTile
from .files import FileFilters, VariantInfo, describe_variants, file_filters
from .licenses import LicenseInfo, license_info
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

    def in_library(self, user) -> models.QuerySet["Tag"]:
        """The tags on `user`'s saved assets, from every provider, most used first.

        Each Tag carries `uses`: how many of the member's entries have it.
        Ties go A–Z. A signed-out visitor has none.
        """
        if not user.is_authenticated:
            return self.none()
        return (
            self.filter(assets__saves__user=user)
            .annotate(uses=Count("assets__saves", distinct=True))
            .order_by("-uses", "name")
        )


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

    @cached_property
    def file_variants(self) -> list[VariantInfo]:
        """The stored variants told apart by resolution, format, package and map type."""
        return describe_variants(self.variants or [], self.external_id)

    @property
    def file_filters(self) -> FileFilters:
        """The resolutions and formats its files come in, for the drawer's filters."""
        return file_filters(self.file_variants)

    @property
    def license_info(self) -> LicenseInfo:
        """What its license lets you do and asks in return (catalog.licenses)."""
        return license_info(self.license)


# The library's sorts, by their URL value; "newest" is the default. Each ends
# on a unique column, so the order never shifts between pages. "community"
# needs SavedAssetQuerySet.with_community_rating().
LIBRARY_SORTS = {
    "newest": ("-saved_at", "-id"),
    "oldest": ("saved_at", "id"),
    "title": (Lower("asset__title"), "-saved_at", "-id"),
    "rating": (F("rating").desc(nulls_last=True), "-saved_at", "-id"),
    "community": (
        F("community_rating").desc(nulls_last=True),
        F("community_count").desc(),
        "-saved_at",
        "-id",
    ),
}


@dataclass(frozen=True)
class CommunityRating:
    """The average of every member's rating for one asset, and how many rated it.

    Only the average and the count: never who rated, or anyone's own rating,
    notes or status.
    """

    average: float
    count: int


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

    def with_community_rating(self) -> "SavedAssetQuerySet":
        """Entries annotated with their asset's community rating.

        `community_rating` is the average of every member's rating for the
        entry's asset (None when no one has rated it) and `community_count`
        how many members rated it. Unrated entries don't count. Each is a
        subquery over all members' entries, so the entries themselves stay
        one row each.
        """
        rated = SavedAsset.objects.filter(asset=OuterRef("asset"), rating__isnull=False)
        per_asset = rated.order_by().values("asset")
        return self.annotate(
            community_rating=Subquery(per_asset.annotate(average=Avg("rating")).values("average")),
            community_count=Coalesce(
                Subquery(per_asset.annotate(count=Count("id")).values("count")),
                0,
                output_field=IntegerField(),
            ),
        )

    def community_ratings(
        self, provider_key: str, external_ids: Iterable[str]
    ) -> dict[str, CommunityRating]:
        """The community rating of each of one provider's assets that anyone has rated.

        Keyed by external ID. Assets no member has rated are left out.
        """
        rows = (
            self.filter(
                asset__provider=provider_key,
                asset__external_id__in=list(external_ids),
                rating__isnull=False,
            )
            .order_by()
            .values("asset__external_id")
            .annotate(average=Avg("rating"), count=Count("id"))
        )
        return {
            row["asset__external_id"]: CommunityRating(row["average"], row["count"]) for row in rows
        }

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

    def tagged(self, names: Iterable[str]) -> "SavedAssetQuerySet":
        """Entries whose asset has every tag in `names` (exact, normalized names).

        Each tag matches through a subquery, so an entry is never listed twice.
        """
        entries = self
        for name in names:
            entries = entries.filter(asset__in=Asset.objects.filter(tags__name=name))
        return entries

    def similar_to(self, entry: "SavedAsset", limit: int = 6) -> list["SavedAsset"]:
        """Up to `limit` other entries most like `entry`: most shared tags first,
        then the same kind, then newest saved. Entries sharing neither are left out.

        Each carries `shared_tags`. Call it on one member's entries
        (for_user()), so it never reaches anyone else's library.
        """
        asset = entry.asset
        tag_ids = list(asset.tags.values_list("id", flat=True))
        same_kind = Case(When(asset__kind=asset.kind, then=1), default=0)
        similar = (
            self.exclude(pk=entry.pk)
            .annotate(
                shared_tags=Count("asset__tags", filter=Q(asset__tags__in=tag_ids), distinct=True),
                same_kind=same_kind,
            )
            .filter(Q(shared_tags__gt=0) | Q(same_kind=1))
            .select_related("asset")
            .order_by("-shared_tags", "-same_kind", "-saved_at", "-id")
        )
        return list(similar[:limit])

    def sorted_by(self, sort: str) -> "SavedAssetQuerySet":
        """Entries in one of LIBRARY_SORTS' orders. Unrated entries sort last by
        rating, and assets no one has rated sort last by community rating (which
        needs with_community_rating())."""
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
    def community(self) -> CommunityRating | None:
        """This entry's community rating, when with_community_rating() annotated it
        and at least one member has rated the asset."""
        count = getattr(self, "community_count", 0)
        return CommunityRating(self.community_rating, count) if count else None

    @property
    def stars(self) -> list[bool]:
        """Five flags, one per star, True for each the rating fills (all False if unrated)."""
        return [star <= (self.rating or 0) for star in range(1, 6)]

    def save_review(
        self, fields: Iterable[str], *, by, via: str = "site", reason: str = ""
    ) -> "StatusChange | None":
        """Save `fields` of this entry's review (status, rating, notes) and nothing else.

        When the status really changes, the change is recorded with who made
        it, where (the website or the API) and the optional `reason`, in the
        same transaction. Returns that record, or None.
        """
        fields = list(fields)
        with transaction.atomic():
            stored = type(self).objects.filter(pk=self.pk).values_list("status", flat=True).first()
            self.save(update_fields=fields)
            if "status" in fields and self.status != stored:
                return self.status_changes.create(
                    status=self.status, changed_by=by, via=via, reason=reason
                )
        return None

    def explain_status(self, reason: str, *, by, via: str = "site") -> "StatusChange":
        """Give the current status a reason (or clear it, with "").

        The reason goes on the latest change when that set the current
        status, and the explainer becomes its author. Otherwise (an entry
        whose status has no record yet) a record of the current status is
        made.
        """
        with transaction.atomic():
            latest = self.status_changes.select_for_update().first()
            if latest and latest.status == self.status:
                latest.reason, latest.changed_by, latest.via = reason, by, via
                latest.save(update_fields=["reason", "changed_by", "via"])
                return latest
            return self.status_changes.create(
                status=self.status, changed_by=by, via=via, reason=reason
            )

    @property
    def latest_status_change(self) -> "StatusChange | None":
        """The record behind the current status, when it has one."""
        latest = next(iter(self.status_changes.all()), None)
        return latest if latest and latest.status == self.status else None


# A status reason is one short line for the drawer.
STATUS_REASON_MAX_LENGTH = 300


class StatusChange(models.Model):
    """Who set one entry's review status, when, where and why.

    Entries are private, so today it's always the entry's owner (or their
    API token); recording the person keeps the history right once members
    work in teams.
    """

    class Via(models.TextChoices):
        SITE = "site", "the website"
        API = "api", "the API"

    entry = models.ForeignKey(SavedAsset, on_delete=models.CASCADE, related_name="status_changes")
    status = models.CharField(max_length=10, choices=SavedAsset.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.CharField(max_length=STATUS_REASON_MAX_LENGTH, blank=True)
    via = models.CharField(max_length=4, choices=Via.choices, default=Via.SITE)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-changed_at", "-id"]

    def __str__(self):
        return f"{self.entry} → {self.get_status_display()}"
