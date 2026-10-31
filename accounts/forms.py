from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


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
