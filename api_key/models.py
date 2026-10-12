from typing import Iterable, Optional, Tuple

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from api_key.crypto import concatenate, KeyGenerator, split


class APIKeyScope(models.TextChoices):
    """Scopes understood by the API-key boundary.

    ``legacy`` is the compatibility scope for keys created before scoped keys
    existed. New integrations must opt into a narrower scope explicitly.
    """

    LEGACY = "legacy", "Legacy integrations"
    NIGHTSHIFT_BENCH_CONSULTANTS_READ = (
        "nightshift.bench-consultants.read",
        "NightShift bench consultants (read-only)",
    )


KNOWN_API_KEY_SCOPES = frozenset(scope.value for scope in APIKeyScope)


class BaseAPIKeyManager(models.Manager):
    key_generator = KeyGenerator()

    def assign_key(self, obj: "AbstractAPIKey") -> str:
        try:
            key, prefix, hashed_key = self.key_generator.generate()
        except ValueError:  # Compatibility with < 1.4
            key, hashed_key = self.key_generator.generate()  # type: ignore
            pk = hashed_key
            prefix, hashed_key = split(hashed_key)
        else:
            pk = concatenate(prefix, hashed_key)

        obj.id = pk
        obj.prefix = prefix
        obj.hashed_key = hashed_key
        obj.api_key = key

        return key

    def create_key(self, **kwargs) -> Tuple["AbstractAPIKey", str]:
        # Prevent from manually setting the primary key.
        kwargs.pop("id", None)
        obj = self.model(**kwargs)  # type: AbstractAPIKey
        key = self.assign_key(obj)
        obj.save()
        return obj, key

    def get_usable_keys(self) -> models.QuerySet:
        return self.filter(revoked=False)

    def delete_key_by_string(self, key: str) -> bool:
        prefix, _, _ = key.partition(".")
        queryset = self.get_usable_keys()

        try:
            api_key = queryset.get(prefix=prefix)  # type: AbstractAPIKey
            api_key.delete()
            return True
        except self.model.DoesNotExist:
            return False

    def get_valid_key(self, key: Optional[str]) -> Optional["AbstractAPIKey"]:
        if not key:
            return None

        prefix, _, _ = key.partition(".")
        queryset = self.get_usable_keys()
        try:
            api_key = queryset.get(prefix=prefix)  # type: AbstractAPIKey
        except self.model.DoesNotExist:
            return None

        if not api_key.is_valid(key):
            return None

        if api_key.has_expired or api_key.scope not in KNOWN_API_KEY_SCOPES:
            return None

        return api_key

    def is_valid(
        self,
        key: Optional[str],
        allowed_scopes: Optional[Iterable[str]] = None,
    ) -> bool:
        """Validate a key and its scope for an existing integration boundary.

        Existing callers remain limited to legacy keys by default. A scoped
        integration must pass its explicitly allowed scopes, so adding a new
        scope cannot silently grant access to old endpoints.
        """

        api_key = self.get_valid_key(key)
        if api_key is None:
            return False

        if allowed_scopes is None:
            allowed_scopes = (APIKeyScope.LEGACY,)
        return api_key.scope in set(allowed_scopes)


class APIKeyManager(BaseAPIKeyManager):
    pass


class AbstractAPIKey(models.Model):
    objects = APIKeyManager()

    hashed_key = models.CharField(_('Hashed Key'), max_length=100, editable=False)
    created = models.DateTimeField(_('Created'), auto_now_add=True, db_index=True)
    api_key = models.CharField(_('Api-Key'), max_length=100, blank=True, null=True)
    prefix = models.CharField(_('Prefix'), max_length=8, unique=True, editable=False)
    id = models.CharField(_('ID'), max_length=100, unique=True, primary_key=True, editable=False)
    name = models.CharField(
        max_length=50,
        blank=False,
        default=None,
        help_text=(
            "A free-form name for the API key. "
            "Need not be unique. "
            "50 characters max."
        ),
    )
    scope = models.CharField(
        _('Scope'),
        max_length=64,
        choices=APIKeyScope.choices,
        default=APIKeyScope.LEGACY,
        help_text=(
            "Permission scope for this key. Legacy keys preserve existing "
            "integration behavior; scoped keys are limited to their endpoint."
        ),
    )
    revoked = models.BooleanField(
        blank=True,
        default=False,
        help_text=(
            "If the API key is revoked, clients cannot use it anymore. "
            "(This cannot be undone.)"
        ),
    )
    expiry_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Expires",
        help_text="Once API key expires, clients cannot use it anymore.",
    )

    class Meta:  # noqa
        abstract = True
        ordering = ("-created",)
        verbose_name = "API key"
        verbose_name_plural = "API keys"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store the initial value of `revoked` to detect changes.
        self._initial_revoked = self.revoked

    def _has_expired(self) -> bool:
        if self.expiry_date is None:
            return False
        return self.expiry_date < timezone.now()

    _has_expired.short_description = "Has expired"  # type: ignore
    _has_expired.boolean = True  # type: ignore
    has_expired = property(_has_expired)

    def is_valid(self, key: str) -> bool:
        return type(self).objects.key_generator.verify(key, self.hashed_key)

    def clean(self):
        super().clean()
        self._validate_scope()
        self._validate_revoked()

    def save(self, *args, **kwargs):
        self._validate_scope()
        self._validate_revoked()
        super().save(*args, **kwargs)

    def _validate_scope(self):
        if self.scope not in KNOWN_API_KEY_SCOPES:
            raise ValidationError({"scope": "Unknown API key scope."})

    def _validate_revoked(self):
        if self._initial_revoked and not self.revoked:
            raise ValidationError(
                "The API key has been revoked, which cannot be undone."
            )

    def delete_key(self):
        self.delete()

    def __str__(self) -> str:
        return str(self.name)


class APIKey(AbstractAPIKey):
    pass
