import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone

from locations.models import LocationNode


def item_photo_path(instance, filename):
    """Store uploads under an unguessable name.

    Nginx serves /media/ without authentication, so a path derived from the
    original filename (items/passport.png) lets anyone who guesses it read
    another user's photo.
    """
    return f"items/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Category(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_category_name_per_owner",
            ),
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags",
    )
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_tag_name_per_owner",
            ),
        ]

    def __str__(self):
        return self.name


class Item(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        MISSING = "MISSING", "Missing"
        ARCHIVED = "ARCHIVED", "Archived"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="items",
    )
    name = models.CharField(max_length=160)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="items",
        blank=True,
        null=True,
    )
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    current_location_node = models.ForeignKey(
        LocationNode,
        on_delete=models.SET_NULL,
        related_name="items",
        blank=True,
        null=True,
    )
    photo = models.ImageField(upload_to=item_photo_path, blank=True, null=True)
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
    )
    purchase_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    last_checked_at = models.DateTimeField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, through="ItemTag", related_name="items", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["owner", "name"]),
            models.Index(fields=["owner", "status"]),
        ]

    def __str__(self):
        return self.name


class ItemTag(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "tag"],
                name="unique_item_tag",
            ),
        ]

    def __str__(self):
        return f"{self.item} #{self.tag}"


class ItemLocationHistory(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="location_histories",
    )
    from_location_node = models.ForeignKey(
        LocationNode,
        on_delete=models.SET_NULL,
        related_name="item_moves_from",
        blank=True,
        null=True,
    )
    to_location_node = models.ForeignKey(
        LocationNode,
        on_delete=models.SET_NULL,
        related_name="item_moves_to",
        blank=True,
        null=True,
    )
    memo = models.CharField(max_length=255, blank=True)
    moved_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="item_location_histories",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-moved_at", "-id"]

    def __str__(self):
        return f"{self.item} moved at {self.moved_at:%Y-%m-%d %H:%M}"
