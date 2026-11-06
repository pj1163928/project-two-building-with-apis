from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import QueryDict

from catalog.files import MAP_CHOICES, MAP_KEYS

from .models import DownloadPreferences

# The download defaults a member can change, in the Settings page's order.
PREFERENCE_FIELDS = (
    "resolution",
    "texture_format",
    "hdri_format",
    "model_format",
    "sound_format",
    "maps",
)


class StyledFieldsMixin:
    """Give every widget the DaisyUI input class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input w-full")


class SignInForm(StyledFieldsMixin, AuthenticationForm):
    pass


class SignUpForm(StyledFieldsMixin, UserCreationForm):
    pass


class DownloadPreferencesForm(forms.ModelForm):
    """A member's download defaults, from the Settings page.

    Like the drawer's forms, only the fields that were posted change (the
    rest are checked at their stored values), so each group of chips saves
    on its own. At least one map type must stay chosen.
    """

    maps = forms.MultipleChoiceField(
        choices=MAP_CHOICES,
        error_messages={
            "required": "Choose at least one map type.",
            "invalid_choice": "Choose map types from the list.",
        },
    )

    class Meta:
        model = DownloadPreferences
        fields = PREFERENCE_FIELDS
        error_messages = {
            name: {"invalid_choice": "Choose one of the options shown."}
            for name in PREFERENCE_FIELDS
            if name != "maps"
        }

    def __init__(self, data, *, instance: DownloadPreferences):
        # A form posts its map chips with a marker, so "none ticked" still counts as posted.
        posted_maps = "maps" in data or "maps_posted" in data
        self.changed_fields = [
            name for name in PREFERENCE_FIELDS if name in data or (name == "maps" and posted_maps)
        ]
        bound = QueryDict(mutable=True)
        for name in PREFERENCE_FIELDS:
            if name == "maps":
                bound.setlist("maps", data.getlist("maps") if posted_maps else instance.maps)
            else:
                bound[name] = data[name] if name in data else getattr(instance, name)
        super().__init__(bound, instance=instance)

    @property
    def first_error(self) -> str:
        """The first problem, as one sentence for the status line."""
        return next(iter(self.errors.values()))[0] if self.errors else ""

    def clean_maps(self) -> list[str]:
        chosen = set(self.cleaned_data["maps"])
        return [key for key in MAP_KEYS if key in chosen]

    def save(self, commit: bool = True) -> DownloadPreferences:
        preferences = super().save(commit=False)
        if commit:
            if preferences.pk:
                preferences.save(update_fields=self.changed_fields)
            else:
                preferences.save()
        return preferences
