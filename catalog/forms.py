"""Forms for the library's own pages."""

from collections.abc import Mapping

from django import forms

from .models import SavedAsset

# Notes are free text; this keeps one entry's notes to a sensible size.
NOTES_MAX_LENGTH = 10_000
# The parts of an entry its owner reviews: everything else comes from the Asset.
REVIEW_FIELDS = ("status", "rating", "notes")
# Short enough for the drawer's status line, whatever the bad value was.
RATING_ERROR = "Choose a rating from 1 to 5."


class ReviewForm(forms.ModelForm):
    """A change to one entry's status, rating or notes, from the library drawer.

    Only the fields that were posted change: the others are checked at their
    stored values and saved untouched (save() writes `changed_fields` only),
    so a notes autosave and a status click never overwrite each other.
    """

    notes = forms.CharField(
        required=False,
        max_length=NOTES_MAX_LENGTH,
        strip=False,
        error_messages={"max_length": f"Notes can be up to {NOTES_MAX_LENGTH:,} characters."},
    )

    class Meta:
        model = SavedAsset
        fields = REVIEW_FIELDS
        error_messages = {
            "rating": {
                "invalid": RATING_ERROR,
                "min_value": RATING_ERROR,
                "max_value": RATING_ERROR,
            },
            "status": {"invalid_choice": "Choose one of the four statuses."},
        }

    def __init__(self, data: Mapping[str, str], *, instance: SavedAsset):
        self.changed_fields = [name for name in REVIEW_FIELDS if name in data]
        stored = {
            "status": instance.status,
            "rating": "" if instance.rating is None else str(instance.rating),
            "notes": instance.notes,
        }
        bound = {name: data[name] if name in data else stored[name] for name in REVIEW_FIELDS}
        # Browsers send a textarea's line breaks as CRLF; store them as typed (LF), so
        # the box's maxlength and NOTES_MAX_LENGTH count the same characters.
        bound["notes"] = bound["notes"].replace("\r\n", "\n")
        super().__init__(bound, instance=instance)

    @property
    def first_error(self) -> str:
        """The first problem with the posted values, as one sentence for the status line."""
        return next(iter(self.errors.values()))[0] if self.errors else ""

    def save(self, commit: bool = True) -> SavedAsset:
        entry = super().save(commit=False)
        if commit:
            entry.save(update_fields=self.changed_fields)
        return entry
