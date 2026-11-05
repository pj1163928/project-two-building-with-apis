"""Forms for the pack pages: creating a pack, and the builder's autosaving fields."""

from collections.abc import Mapping

from django import forms
from django.db import transaction

from accounts.forms import StyledFieldsMixin

from .models import (
    DESCRIPTION_MAX_LENGTH,
    IMPORT_PATH_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    Pack,
    PackItem,
    tags_from_text,
)

TAGS_MAX_LENGTH = 500
TAGS_HELP = "Separate tags with commas. They're tidied: “Mossy Stones” is stored as “mossy stone”."
DETAIL_FIELDS = ("title", "description", "tags")
ITEM_FIELDS = ("preferred_variant", "import_path")


class PackFieldsMixin(forms.Form):
    title = forms.CharField(
        max_length=TITLE_MAX_LENGTH,
        error_messages={
            "required": "Give the pack a title.",
            "max_length": f"A title can be up to {TITLE_MAX_LENGTH} characters.",
        },
    )
    description = forms.CharField(
        label="Intended use",
        required=False,
        max_length=DESCRIPTION_MAX_LENGTH,
        widget=forms.Textarea(attrs={"rows": 3}),
        error_messages={
            "max_length": f"The intended use can be up to {DESCRIPTION_MAX_LENGTH:,} characters."
        },
    )
    tags = forms.CharField(
        required=False,
        max_length=TAGS_MAX_LENGTH,
        help_text=TAGS_HELP,
        error_messages={"max_length": f"Tags can be up to {TAGS_MAX_LENGTH} characters in all."},
    )


class NewPackForm(StyledFieldsMixin, PackFieldsMixin):
    """The New pack page: a title, the intended use and comma-separated tags."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].widget.attrs["class"] = "textarea w-full"
        self.fields["title"].widget.attrs["placeholder"] = "Medieval Village"
        self.fields["tags"].widget.attrs["placeholder"] = "stone, wood, medieval"

    def create(self, owner) -> Pack:
        """Create the private pack (Pack.objects.create_pack, one transaction)."""
        data = self.cleaned_data
        return Pack.objects.create_pack(owner, data["title"], data["description"], data["tags"])


class PackDetailsForm(PackFieldsMixin):
    """A change to a pack's title, intended use or tags, from the builder.

    Each field autosaves on its own, so only the fields that were posted are
    checked and saved; the others keep their stored values.
    """

    def __init__(self, data: Mapping[str, str], *, pack: Pack):
        self.pack = pack
        self.changed_fields = [name for name in DETAIL_FIELDS if name in data]
        stored = {"title": pack.title, "description": pack.description, "tags": pack.tags_text}
        super().__init__({name: data.get(name, stored[name]) for name in DETAIL_FIELDS})

    @property
    def first_error(self) -> str:
        return next(iter(self.errors.values()))[0] if self.errors else ""

    def save(self) -> Pack:
        """Write the posted fields (and the tags, through normalize_tag) in one transaction."""
        pack, data = self.pack, self.cleaned_data
        with transaction.atomic():
            for name in {"title", "description"} & set(self.changed_fields):
                setattr(pack, name, data[name])
            # updated_at moves on every change, tags included.
            pack.save(
                update_fields=[*({"title", "description"} & set(self.changed_fields)), "updated_at"]
            )
            if "tags" in self.changed_fields:
                pack.tags.set(tags_from_text(data["tags"]))
        return pack


class PackItemForm(forms.Form):
    """A change to one item's variant or import path, from the builder.

    The variant must be one of the asset's own variants. The import path is
    optional (blank means the default, <kind>s/<external_id>/), and must be
    a relative path that never climbs out with "..".
    """

    preferred_variant = forms.CharField(required=False, max_length=100)
    import_path = forms.CharField(
        required=False,
        max_length=IMPORT_PATH_MAX_LENGTH,
        error_messages={
            "max_length": f"An import path can be up to {IMPORT_PATH_MAX_LENGTH} characters."
        },
    )

    def __init__(self, data: Mapping[str, str], *, item: PackItem):
        self.item = item
        self.changed_fields = [name for name in ITEM_FIELDS if name in data]
        stored = {"preferred_variant": item.preferred_variant, "import_path": item.import_path}
        super().__init__({name: data.get(name, stored[name]) for name in ITEM_FIELDS})

    @property
    def first_error(self) -> str:
        return next(iter(self.errors.values()))[0] if self.errors else ""

    def clean_preferred_variant(self) -> str:
        value = self.cleaned_data["preferred_variant"]
        labels = self.item.variant_labels
        if (value or labels) and value not in labels:
            raise forms.ValidationError("Choose one of this asset's variants.")
        return value

    def clean_import_path(self) -> str:
        value = self.cleaned_data["import_path"].strip().replace("\\", "/")
        if value.startswith("/") or ":" in value.split("/")[0]:
            raise forms.ValidationError("Use a path inside your project, like textures/brick/.")
        if ".." in value.split("/"):
            raise forms.ValidationError("An import path can't climb out of the project with “..”.")
        return value

    def save(self) -> PackItem:
        for name in self.changed_fields:
            setattr(self.item, name, self.cleaned_data[name])
        self.item.save(update_fields=self.changed_fields)
        return self.item
