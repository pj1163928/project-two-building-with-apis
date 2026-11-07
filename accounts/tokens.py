"""Members' API tokens: the one place a token is replaced.

DRF's Token uses its key as the primary key, so a new key means a new row:
the old row is deleted and a new one made, in one transaction.
"""

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from rest_framework.authtoken.models import Token


def rotate_token(user: AbstractBaseUser) -> Token:
    """Replace the member's API token with a new one and return it.

    The old key stops signing requests at once. A member with no token yet
    simply gets their first one.
    """
    with transaction.atomic():
        Token.objects.filter(user=user).delete()
        return Token.objects.create(user=user)
